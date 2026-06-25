from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from typing import Optional
from PIL import Image, ImageOps
import io, os, uuid

from ..database import get_db
from ..models.models import User, Store, Auction, Bid, Watched, Sale, Message
from ..schemas.schemas import StoreUpdate, SaleStatusUpdate, UserUpdate, FacebookLink, ShippingUpdate
from ..deps import get_current_user
from ..services.auction_service import fmt_price
from ..config import get_settings

router = APIRouter(prefix="/api/users", tags=["users"])
settings = get_settings()
UPLOAD_DIR = "app/uploads"

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

def _save_chat_image(file: UploadFile) -> str:
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Formato de imagen no permitido")
    data = file.file.read()
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((1200, 1200), Image.LANCZOS)
    fname = f"chat_{uuid.uuid4().hex}.jpg"
    img.save(os.path.join(UPLOAD_DIR, fname), "JPEG", quality=85, optimize=True)
    return f"/uploads/{fname}"


@router.get("/me")
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.refresh(current_user)
    return current_user


@router.get("/me/bids")
def my_bids(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bids = (
        db.query(Bid)
        .options(joinedload(Bid.auction).joinedload(Auction.seller))
        .filter(Bid.bidder_id == current_user.id)
        .order_by(Bid.created_at.desc())
        .all()
    )
    seen = set()
    result = []
    for b in bids:
        if b.auction_id not in seen:
            seen.add(b.auction_id)
            result.append(b)
    return result


@router.get("/me/watched")
def my_watched(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Watched)
        .options(joinedload(Watched.auction).joinedload(Auction.seller))
        .filter(Watched.user_id == current_user.id)
        .all()
    )


@router.get("/me/won")
def my_won(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Sale)
        .options(joinedload(Sale.auction))
        .filter(Sale.buyer_id == current_user.id)
        .order_by(Sale.created_at.desc())
        .all()
    )


@router.get("/me/sales")
def my_sales(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Sale)
        .options(joinedload(Sale.auction), joinedload(Sale.buyer))
        .filter(Sale.seller_id == current_user.id)
        .order_by(Sale.created_at.desc())
        .all()
    )


@router.patch("/me")
def update_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from passlib.hash import bcrypt as bcrypt_hash

    if data.display_name is not None:
        current_user.display_name = data.display_name.strip() or None

    if data.email is not None:
        email = data.email.strip().lower()
        taken = db.query(User).filter(User.email == email, User.id != current_user.id).first()
        if taken:
            raise HTTPException(status_code=400, detail="Este email ya está registrado")
        current_user.email = email

    if data.new_password:
        if not data.current_password:
            raise HTTPException(status_code=400, detail="Debes ingresar tu contraseña actual")
        if not bcrypt_hash.verify(data.current_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
        if len(data.new_password) < 6:
            raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 6 caracteres")
        current_user.password_hash = bcrypt_hash.hash(data.new_password)

    db.commit()
    return JSONResponse({"ok": True, "display_name": current_user.display_name, "email": current_user.email})


@router.patch("/me/shipping")
def update_shipping(
    data: ShippingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.shipping_street is not None:
        current_user.shipping_street = data.shipping_street.strip() or None
    if data.shipping_colony is not None:
        current_user.shipping_colony = data.shipping_colony.strip() or None
    if data.shipping_city is not None:
        current_user.shipping_city = data.shipping_city.strip() or None
    if data.shipping_state is not None:
        current_user.shipping_state = data.shipping_state.strip() or None
    if data.shipping_postal is not None:
        current_user.shipping_postal = data.shipping_postal.strip() or None
    db.commit()
    return JSONResponse({"ok": True})


@router.post("/me/facebook")
def link_facebook(
    data: FacebookLink,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import httpx, hmac, hashlib
    proof = hmac.new(
        settings.FACEBOOK_APP_SECRET.encode(),
        data.access_token.encode(),
        hashlib.sha256,
    ).hexdigest()
    r = httpx.get(
        "https://graph.facebook.com/me",
        params={"fields": "id,name", "access_token": data.access_token, "appsecret_proof": proof},
        timeout=8,
    )
    if r.status_code != 200:
        raise HTTPException(status_code=400, detail="Token de Facebook inválido")
    fb = r.json()
    if "id" not in fb:
        raise HTTPException(status_code=400, detail="No se pudo obtener información de Facebook")
    taken = db.query(User).filter(User.facebook_id == fb["id"], User.id != current_user.id).first()
    if taken:
        raise HTTPException(status_code=400, detail="Esta cuenta de Facebook ya está vinculada a otro usuario")
    current_user.facebook_id = fb["id"]
    current_user.facebook_name = fb.get("name")
    db.commit()
    return JSONResponse({"ok": True, "facebook_name": fb.get("name")})


@router.delete("/me/facebook")
def unlink_facebook(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.facebook_id = None
    current_user.facebook_name = None
    db.commit()
    return JSONResponse({"ok": True})


@router.put("/me/store")
def update_store(
    data: StoreUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    store = db.query(Store).filter(Store.user_id == current_user.id).first()
    if not store:
        store = Store(user_id=current_user.id)
        db.add(store)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(store, field, value)
    db.commit()
    return JSONResponse({"ok": True})


@router.post("/me/store/logo")
def upload_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "logo.jpg")[1] or ".jpg"
    fname = f"logo_{current_user.id}_{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, fname)
    with open(path, "wb") as f:
        f.write(file.file.read())
    store = db.query(Store).filter(Store.user_id == current_user.id).first()
    if store:
        store.logo_path = f"/uploads/{fname}"
        db.commit()
    return JSONResponse({"logo_path": f"/uploads/{fname}"})


@router.patch("/me/sales/{sale_id}")
def update_sale_status(
    sale_id: int,
    data: SaleStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.seller_id == current_user.id).first()
    if not sale:
        raise HTTPException(status_code=404)
    sale.status = data.status
    if data.status == "enviado" and sale.shipped_at is None:
        sale.shipped_at = datetime.now()
    if data.tracking:
        sale.tracking = data.tracking
    db.commit()
    return JSONResponse({
        "ok": True,
        "shipped_at": sale.shipped_at.strftime("%d/%m/%Y") if sale.shipped_at else None,
    })


def _get_sale_for_user(sale_id: int, user: User, db: Session) -> Sale:
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale or (sale.seller_id != user.id and sale.buyer_id != user.id):
        raise HTTPException(status_code=404)
    return sale


@router.get("/me/sales/{sale_id}/messages")
def get_messages(
    sale_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sale = _get_sale_for_user(sale_id, current_user, db)
    msgs = (
        db.query(Message)
        .options(joinedload(Message.sender))
        .filter(Message.sale_id == sale.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return [
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "sender_name": m.sender.display_name or m.sender.username,
            "body": m.body,
            "image_url": m.image_url,
            "mine": m.sender_id == current_user.id,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]


@router.post("/me/sales/{sale_id}/messages")
async def send_message(
    sale_id: int,
    body: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sale = _get_sale_for_user(sale_id, current_user, db)
    text_body = (body or "").strip()
    image_url = None
    if image and image.filename:
        image_url = _save_chat_image(image)
    if not text_body and not image_url:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")
    msg = Message(
        sale_id=sale.id,
        sender_id=current_user.id,
        body=text_body,
        image_url=image_url,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {
        "id": msg.id,
        "sender_id": msg.sender_id,
        "sender_name": current_user.display_name or current_user.username,
        "body": msg.body,
        "image_url": msg.image_url,
        "mine": True,
        "created_at": msg.created_at.isoformat(),
    }
