from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import asc, desc
from datetime import datetime, timedelta
from typing import Optional

from ..database import get_db
from ..models.models import Auction, User, Bid, MaxBid, Watched, Sale, Store
from ..deps import get_current_user_optional, get_current_user
from ..services.auction_service import fmt_price, fmt_countdown, time_ago, auction_to_card
from ..config import get_settings

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["fmt_price"] = fmt_price
settings = get_settings()


def _watched_ids(user: Optional[User], db: Session) -> set:
    if not user:
        return set()
    rows = db.query(Watched.auction_id).filter(Watched.user_id == user.id).all()
    return {r[0] for r in rows}


def _common(request: Request, user: Optional[User]) -> dict:
    return {
        "request": request,
        "current_user": user,
        "currency": settings.CURRENCY,
    }


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
    game: str = "todas",
    sort: str = "termina",
):
    watched = _watched_ids(user, db)

    # Ending soon (next 6 hours)
    cutoff = datetime.utcnow() + timedelta(hours=6)
    ending_q = (
        db.query(Auction)
        .options(joinedload(Auction.seller))
        .filter(Auction.status == "active", Auction.ends_at <= cutoff, Auction.ends_at > datetime.utcnow())
        .order_by(asc(Auction.ends_at))
        .limit(8)
        .all()
    )

    # Main grid
    q = db.query(Auction).options(joinedload(Auction.seller)).filter(
        Auction.status == "active", Auction.ends_at > datetime.utcnow()
    )
    if game != "todas":
        q = q.filter(Auction.game == game)
    if sort == "precio_asc":
        q = q.order_by(asc(Auction.current_bid))
    elif sort == "precio_desc":
        q = q.order_by(desc(Auction.current_bid))
    elif sort == "pujas":
        q = q.order_by(desc(Auction.bid_count))
    elif sort == "recientes":
        q = q.order_by(desc(Auction.created_at))
    else:
        q = q.order_by(asc(Auction.ends_at))
    auctions = q.limit(20).all()

    # Featured = highest watcher count active
    featured = (
        db.query(Auction)
        .options(joinedload(Auction.seller))
        .filter(Auction.status == "active", Auction.ends_at > datetime.utcnow())
        .order_by(desc(Auction.watchers_count))
        .first()
    )

    ending_cards = [auction_to_card(a, watched, settings.CURRENCY) for a in ending_q]
    auction_cards = [auction_to_card(a, watched, settings.CURRENCY) for a in auctions]

    feat = None
    if featured:
        cd = fmt_countdown(featured.ends_at)
        feat = {
            "id": featured.id,
            "name": featured.title,
            "game": featured.game or "",
            "rarity": featured.rarity or "",
            "grade": featured.grade or "",
            "set": featured.set_name or "",
            "watchers": f"{featured.watchers_count} observando",
            "price": fmt_price(featured.current_bid, settings.CURRENCY),
            "bids": f"{featured.bid_count} {'puja' if featured.bid_count == 1 else 'pujas'}",
            "countdown": cd["text"],
            "timer_color": cd["color"],
            "has_buy_now": featured.buy_now_price is not None,
            "buy_now_text": fmt_price(featured.buy_now_price, settings.CURRENCY),
            "hue": featured.hue,
        }

    ctx = _common(request, user)
    ctx.update({
        "featured": feat,
        "ending_cards": ending_cards,
        "auction_cards": auction_cards,
        "selected_game": game,
        "selected_sort": sort,
        "auction_count": len(auction_cards),
        "fmt_price": fmt_price,
        "fmt_countdown": fmt_countdown,
    })
    return templates.TemplateResponse("marketplace.html", ctx)


@router.get("/auction/{auction_id}", response_class=HTMLResponse)
def auction_detail(
    auction_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
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

    watched = _watched_ids(user, db)
    cd = fmt_countdown(auction.ends_at)

    # Related: same game, exclude current
    related_q = (
        db.query(Auction)
        .options(joinedload(Auction.seller))
        .filter(
            Auction.game == auction.game,
            Auction.id != auction.id,
            Auction.status == "active",
            Auction.ends_at > datetime.utcnow(),
        )
        .limit(5)
        .all()
    )
    related = [auction_to_card(a, watched, settings.CURRENCY) for a in related_q]

    bid_history = auction.bids[:8]
    spec_rows = [
        ("Juego", auction.game or "—"),
        ("Set / Edición", auction.set_name or "—"),
        ("Rareza", auction.rarity or "—"),
        ("Graduación", auction.grade or "Sin graduar"),
        ("Condición", auction.condition or "—"),
        ("Idioma", auction.language or "—"),
    ]

    increment = float(auction.bid_increment) if auction.bid_increment else 50
    floor = float(auction.current_bid) + increment if auction.bid_count > 0 else float(auction.start_price)

    user_max_bid = None
    user_min_bid = floor
    if user:
        mb = db.query(MaxBid).filter(
            MaxBid.auction_id == auction_id,
            MaxBid.bidder_id == user.id,
        ).first()
        if mb:
            user_max_bid = float(mb.max_amount)
            user_min_bid = user_max_bid + 1  # can only increase their max

    ctx = _common(request, user)
    ctx.update({
        "auction": auction,
        "cd": cd,
        "is_watched": auction_id in watched,
        "related": related,
        "bid_history": bid_history,
        "spec_rows": spec_rows,
        "price_text": fmt_price(auction.current_bid, settings.CURRENCY),
        "buy_now_text": fmt_price(auction.buy_now_price, settings.CURRENCY) if auction.buy_now_price else None,
        "min_bid": user_min_bid,
        "min_bid_text": fmt_price(floor, settings.CURRENCY),
        "user_max_bid": user_max_bid,
        "user_max_bid_text": fmt_price(user_max_bid, settings.CURRENCY) if user_max_bid else None,
        "time_ago": time_ago,
        "seller_store": auction.seller.store,
    })
    return templates.TemplateResponse("auction_detail.html", ctx)


@router.get("/seller/{seller_id}", response_class=HTMLResponse)
def seller_profile(
    seller_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    seller = (
        db.query(User)
        .options(joinedload(User.store))
        .filter(User.id == seller_id)
        .first()
    )
    if not seller:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")

    watched = _watched_ids(user, db)

    all_auctions = (
        db.query(Auction)
        .filter(Auction.seller_id == seller_id, Auction.ends_at > datetime.utcnow())
        .order_by(asc(Auction.ends_at))
        .all()
    )

    active_auctions = [a for a in all_auctions if a.sale_type == "subasta" and a.status == "active"]
    fixed_offers = [a for a in all_auctions if a.sale_type == "fijo" and a.status == "active"]

    auction_cards = [auction_to_card(a, watched, settings.CURRENCY) for a in active_auctions]
    offer_cards = [auction_to_card(a, watched, settings.CURRENCY) for a in fixed_offers]

    ctx = _common(request, user)
    ctx.update({
        "seller": seller,
        "store": seller.store,
        "auction_cards": auction_cards,
        "offer_cards": offer_cards,
        "fmt_price": fmt_price,
    })
    return templates.TemplateResponse("seller_profile.html", ctx)


@router.get("/search", response_class=HTMLResponse)
def search(
    request: Request,
    q: str = "",
    game: Optional[str] = None,
    sale_type: Optional[str] = None,
    grade_filter: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort: str = "termina",
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    watched = _watched_ids(user, db)
    base = db.query(Auction).options(joinedload(Auction.seller)).filter(
        Auction.status == "active", Auction.ends_at > datetime.utcnow()
    )
    if q:
        base = base.filter(Auction.title.ilike(f"%{q}%"))
    if game:
        games = game.split(",") if "," in game else [game]
        base = base.filter(Auction.game.in_(games))
    if sale_type:
        base = base.filter(Auction.sale_type == sale_type)
    if min_price is not None:
        base = base.filter(Auction.current_bid >= min_price)
    if max_price is not None:
        base = base.filter(Auction.current_bid <= max_price)

    if sort == "precio_asc":
        base = base.order_by(asc(Auction.current_bid))
    elif sort == "precio_desc":
        base = base.order_by(desc(Auction.current_bid))
    elif sort == "pujas":
        base = base.order_by(desc(Auction.bid_count))
    elif sort == "recientes":
        base = base.order_by(desc(Auction.created_at))
    else:
        base = base.order_by(asc(Auction.ends_at))

    results = base.limit(50).all()
    cards = [auction_to_card(a, watched, settings.CURRENCY) for a in results]

    ctx = _common(request, user)
    ctx.update({
        "query": q,
        "results": cards,
        "result_count": len(cards),
        "selected_game": game or "",
        "selected_sort": sort,
        "selected_sale_type": sale_type or "",
        "min_price": min_price or "",
        "max_price": max_price or "",
    })
    return templates.TemplateResponse("search.html", ctx)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    tab: str = "curso",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    watched = _watched_ids(user, db)

    # Tab 1: active auctions the user bid on OR is watching, deduplicated
    active_map: dict = {}
    for b in (
        db.query(Bid)
        .options(joinedload(Bid.auction).joinedload(Auction.seller))
        .filter(Bid.bidder_id == user.id)
        .order_by(Bid.created_at.desc())
        .all()
    ):
        if b.auction and b.auction.status == "active" and b.auction_id not in active_map:
            active_map[b.auction_id] = b.auction

    for w in (
        db.query(Watched)
        .options(joinedload(Watched.auction).joinedload(Auction.seller))
        .filter(Watched.user_id == user.id)
        .all()
    ):
        if w.auction and w.auction.status == "active" and w.auction_id not in active_map:
            active_map[w.auction_id] = w.auction

    active_cards = [auction_to_card(a, watched, settings.CURRENCY) for a in active_map.values()]

    # Tab 2: won, not yet received
    won = (
        db.query(Sale)
        .options(joinedload(Sale.auction), joinedload(Sale.seller))
        .filter(Sale.buyer_id == user.id, Sale.received_at == None)
        .order_by(Sale.created_at.desc())
        .all()
    )

    # Tab 3: received (purchase history)
    history = (
        db.query(Sale)
        .options(joinedload(Sale.auction), joinedload(Sale.seller))
        .filter(Sale.buyer_id == user.id, Sale.received_at != None)
        .order_by(Sale.received_at.desc())
        .all()
    )

    ctx = _common(request, user)
    ctx.update({
        "tab": tab,
        "active_cards": active_cards,
        "won": won,
        "history": history,
        "active_count": len(active_cards),
        "won_count": len(won),
        "history_count": len(history),
        "fmt_price": fmt_price,
        "time_ago": time_ago,
        "facebook_app_id": settings.FACEBOOK_APP_ID,
    })
    return templates.TemplateResponse("dashboard.html", ctx)


@router.get("/sell", response_class=HTMLResponse)
def sell_page(
    request: Request,
    tab: str = "crear",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    store = db.query(Store).filter(Store.user_id == user.id).first()

    sales = (
        db.query(Sale)
        .options(joinedload(Sale.auction), joinedload(Sale.buyer))
        .filter(Sale.seller_id == user.id)
        .order_by(Sale.created_at.desc())
        .all()
    )
    enviado_sales = [s for s in sales if s.status == "enviado"]
    enviado_count = len(enviado_sales)
    revenue = sum(float(s.final_price) for s in enviado_sales)

    ctx = _common(request, user)
    ctx.update({
        "tab": tab,
        "store": store,
        "sales": sales,
        "enviado_count": enviado_count,
        "revenue": fmt_price(revenue, settings.CURRENCY),
        "fmt_price": fmt_price,
    })
    return templates.TemplateResponse("sell.html", ctx)


@router.get("/privacy", response_class=HTMLResponse)
def privacy_policy(request: Request, user: Optional[User] = Depends(get_current_user_optional)):
    ctx = _common(request, user)
    return templates.TemplateResponse("privacy.html", ctx)


@router.get("/auth/login", response_class=HTMLResponse)
def login_page(request: Request, user: Optional[User] = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse("/")
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/auth/register", response_class=HTMLResponse)
def register_page(request: Request, user: Optional[User] = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse("/")
    return templates.TemplateResponse("auth/register.html", {"request": request})
