from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from PIL import Image, ImageOps
import io, os, uuid

from ..database import get_db
from ..models.models import Auction, Bid, MaxBid, Watched, User, Store, Sale, Message
from ..schemas.schemas import AuctionCreate
from ..deps import get_current_user, get_current_user_optional
from ..services.auction_service import manager, fmt_price, fmt_countdown, time_ago
from ..config import get_settings

router = APIRouter(prefix="/api/auctions", tags=["auctions"])
settings = get_settings()

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


MAX_SIZE = 1200
JPEG_QUALITY = 85

def _save_file(file: UploadFile) -> str:
    data = file.file.read()
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)  # respect EXIF rotation
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((MAX_SIZE, MAX_SIZE), Image.LANCZOS)
    fname = f"{uuid.uuid4().hex}.jpg"
    path = os.path.join(UPLOAD_DIR, fname)
    img.save(path, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return f"/uploads/{fname}"


@router.get("")
def list_auctions(
    game: Optional[str] = None,
    sort: str = "termina",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    grade_filter: Optional[str] = None,
    sale_type: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Auction)
        .options(joinedload(Auction.seller))
        .filter(Auction.status == "active", Auction.ends_at > datetime.utcnow())
    )
    if game:
        query = query.filter(Auction.game == game)
    if min_price is not None:
        query = query.filter(Auction.current_bid >= min_price)
    if max_price is not None:
        query = query.filter(Auction.current_bid <= max_price)
    if sale_type:
        query = query.filter(Auction.sale_type == sale_type)
    if q:
        query = query.filter(Auction.title.ilike(f"%{q}%"))

    if sort == "precio_asc":
        query = query.order_by(asc(Auction.current_bid))
    elif sort == "precio_desc":
        query = query.order_by(desc(Auction.current_bid))
    elif sort == "pujas":
        query = query.order_by(desc(Auction.bid_count))
    elif sort == "recientes":
        query = query.order_by(desc(Auction.created_at))
    else:
        query = query.order_by(asc(Auction.ends_at))

    return query.all()


@router.get("/ending-soon")
def ending_soon(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() + timedelta(hours=6)
    return (
        db.query(Auction)
        .options(joinedload(Auction.seller))
        .filter(
            Auction.status == "active",
            Auction.ends_at <= cutoff,
            Auction.ends_at > datetime.utcnow(),
        )
        .order_by(asc(Auction.ends_at))
        .limit(10)
        .all()
    )


@router.get("/{auction_id}")
def get_auction(auction_id: int, db: Session = Depends(get_db)):
    auction = (
        db.query(Auction)
        .options(
            joinedload(Auction.seller).joinedload(User.store),
            joinedload(Auction.bids).joinedload(Bid.bidder),
        )
        .filter(Auction.id == auction_id)
        .first()
    )
    if not auction:
        raise HTTPException(status_code=404, detail="Subasta no encontrada")
    return auction


BID_INCREMENT = Decimal("50")  # fallback only


@router.post("/{auction_id}/bid")
async def place_bid(
    auction_id: int,
    max_amount: Decimal = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    auction = db.query(Auction).filter(Auction.id == auction_id).first()
    if not auction:
        raise HTTPException(status_code=404, detail="Subasta no encontrada")
    if auction.status != "active" or auction.ends_at <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="La subasta ya finalizó")
    if auction.seller_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes pujar en tu propia subasta")

    # Minimum required to enter
    increment = auction.bid_increment or BID_INCREMENT
    floor = auction.current_bid + increment if auction.bid_count > 0 else auction.start_price
    if max_amount < floor:
        raise HTTPException(
            status_code=400,
            detail=f"La puja mínima es {fmt_price(floor, settings.CURRENCY)}",
        )

    # Upsert the user's max bid (can only increase)
    user_max = db.query(MaxBid).filter(
        MaxBid.auction_id == auction_id,
        MaxBid.bidder_id == current_user.id,
    ).first()
    if user_max:
        if max_amount <= user_max.max_amount:
            raise HTTPException(
                status_code=400,
                detail=f"Tu nueva puja máxima debe superar la actual ({fmt_price(user_max.max_amount, settings.CURRENCY)})",
            )
        user_max.max_amount = max_amount
    else:
        db.add(MaxBid(auction_id=auction_id, bidder_id=current_user.id, max_amount=max_amount))
    db.flush()

    # Resolve proxy: top 2 max bids ordered by amount desc, then by entry time asc (tie → first bidder wins)
    top = (
        db.query(MaxBid)
        .filter(MaxBid.auction_id == auction_id)
        .order_by(MaxBid.max_amount.desc(), MaxBid.created_at.asc())
        .limit(2)
        .all()
    )

    if len(top) == 1:
        winner_id = top[0].bidder_id
        new_current = max(floor, auction.start_price)
    else:
        leader, runner_up = top[0], top[1]
        new_current = min(runner_up.max_amount + increment, leader.max_amount)
        winner_id = leader.bidder_id

    winner = db.query(User).filter(User.id == winner_id).first()
    bid = Bid(auction_id=auction_id, bidder_id=winner_id, amount=new_current)
    auction.current_bid = new_current
    auction.bid_count += 1
    db.add(bid)
    db.commit()
    db.refresh(auction)

    payload = {
        "event": "new_bid",
        "current_bid": float(auction.current_bid),
        "bid_count": auction.bid_count,
        "price_text": fmt_price(auction.current_bid, settings.CURRENCY),
        "bidder": winner.username,
    }
    await manager.broadcast(auction_id, payload)

    you_lead = winner_id == current_user.id
    return JSONResponse({
        "ok": True,
        "current_bid": float(auction.current_bid),
        "bid_count": auction.bid_count,
        "you_lead": you_lead,
        "message": "¡Eres el mejor postor!" if you_lead else "Otro postor supera tu máximo",
    })


@router.post("/{auction_id}/buy-now")
async def buy_now(
    auction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    auction = (
        db.query(Auction)
        .options(joinedload(Auction.seller).joinedload(User.store))
        .filter(Auction.id == auction_id)
        .first()
    )
    if not auction or not auction.buy_now_price:
        raise HTTPException(status_code=400, detail="Compra inmediata no disponible")
    if auction.status != "active":
        raise HTTPException(status_code=400, detail="La subasta ya finalizó")
    if auction.seller_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes comprar tu propia subasta")

    auction.status = "sold"
    auction.current_bid = auction.buy_now_price

    sale = Sale(
        auction_id=auction.id,
        seller_id=auction.seller_id,
        buyer_id=current_user.id,
        final_price=auction.buy_now_price,
    )
    db.add(sale)
    db.flush()

    store = auction.seller.store
    if store and store.win_message:
        db.add(Message(sale_id=sale.id, sender_id=auction.seller_id, body=store.win_message))

    db.commit()
    return JSONResponse({"ok": True, "redirect": f"/auction/{auction_id}"})


@router.post("/{auction_id}/watch")
def toggle_watch(
    auction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = (
        db.query(Watched)
        .filter(Watched.user_id == current_user.id, Watched.auction_id == auction_id)
        .first()
    )
    auction = db.query(Auction).filter(Auction.id == auction_id).first()
    if not auction:
        raise HTTPException(status_code=404)

    if existing:
        db.delete(existing)
        auction.watchers_count = max(0, auction.watchers_count - 1)
        watching = False
    else:
        db.add(Watched(user_id=current_user.id, auction_id=auction_id))
        auction.watchers_count += 1
        watching = True

    db.commit()
    return JSONResponse({"watching": watching, "watchers_count": auction.watchers_count})


@router.post("")
async def create_listing(
    title: str = Form(...),
    game: str = Form(""),
    set_name: str = Form(""),
    rarity: str = Form(""),
    grade: str = Form(""),
    condition: str = Form(""),
    language: str = Form("Español"),
    notes: str = Form(""),
    sale_type: str = Form("subasta"),
    start_price: Decimal = Form(Decimal("0")),
    bid_increment: Decimal = Form(Decimal("50")),
    buy_now_price: Optional[str] = Form(None),
    accepts_offers: bool = Form(False),
    is_lot: bool = Form(False),
    duration_days: int = Form(7),
    ends_at_iso: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    back_image: Optional[UploadFile] = File(None),
    detail_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image_path = _save_file(image) if image and image.filename else None
    back_path = _save_file(back_image) if back_image and back_image.filename else None
    detail_path = _save_file(detail_image) if detail_image and detail_image.filename else None

    import random
    hues = [28, 268, 8, 42, 222, 196, 300, 32, 50, 150, 322, 18, 188, 210]
    buy_now = Decimal(buy_now_price) if buy_now_price and buy_now_price.strip() else None

    if ends_at_iso:
        dt = datetime.fromisoformat(ends_at_iso)
        if dt.tzinfo is not None:
            ends_at = dt.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            ends_at = dt
        duration_days = max(1, (ends_at - datetime.utcnow()).days)
    else:
        ends_at = datetime.utcnow() + timedelta(days=duration_days)

    auction = Auction(
        seller_id=current_user.id,
        title=title,
        game=game or None,
        set_name=set_name or None,
        rarity=rarity or None,
        grade=grade or None,
        condition=condition or None,
        language=language,
        notes=notes or None,
        sale_type=sale_type,
        start_price=start_price,
        bid_increment=bid_increment,
        buy_now_price=buy_now,
        current_bid=start_price,
        accepts_offers=accepts_offers,
        is_lot=is_lot,
        duration_days=duration_days,
        ends_at=ends_at,
        hue=random.choice(hues),
        image_path=image_path,
        back_image_path=back_path,
        detail_image_path=detail_path,
    )
    db.add(auction)
    db.commit()
    return JSONResponse({"ok": True, "auction_id": auction.id})


@router.websocket("/{auction_id}/ws")
async def auction_websocket(websocket: WebSocket, auction_id: int):
    await manager.connect(websocket, auction_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, auction_id)
