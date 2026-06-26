"""
Seed dummy data for cartasdelsur@rareza.com so the buyer dashboard has
something to show across all three tabs.

Run from the project root:
    python seed_buyer.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import User, Auction, Bid, Watched, Sale

db: Session = SessionLocal()

try:
    buyer = db.query(User).filter(User.email == "cartasdelsur@rareza.com").first()
    if not buyer:
        print("ERROR: user cartasdelsur@rareza.com not found")
        sys.exit(1)

    print(f"Seeding data for user: {buyer.username} (id={buyer.id})")

    # ── Subastas en Curso: bids on auctions owned by other sellers ──────────
    # Auction 2 – Hechicera del Vacío (seller=holomaniamc)
    # Auction 5 – Ángel del Ocaso (seller=gradedperu)
    for auction_id, amount in [(2, 340.00), (5, 165.00)]:
        exists = db.query(Bid).filter(
            Bid.auction_id == auction_id, Bid.bidder_id == buyer.id
        ).first()
        if not exists:
            db.add(Bid(auction_id=auction_id, bidder_id=buyer.id, amount=amount))
            print(f"  + Bid on auction {auction_id} for {amount}")

    # ── Subastas en Curso: watched auctions ─────────────────────────────────
    # Auction 4 – Zorro Solar (seller=elcoleccionista)
    # Auction 7 – Maga Astral (seller=holomaniamc)
    for auction_id in [4, 7]:
        exists = db.query(Watched).filter(
            Watched.auction_id == auction_id, Watched.user_id == buyer.id
        ).first()
        if not exists:
            db.add(Watched(auction_id=auction_id, user_id=buyer.id))
            a = db.query(Auction).get(auction_id)
            if a:
                a.watchers_count = (a.watchers_count or 0) + 1
            print(f"  + Watching auction {auction_id}")

    db.flush()

    # ── Ganadas: won sales not yet received ─────────────────────────────────
    # We need sellers that are NOT the buyer
    sales_ganadas = [
        # auction_id, seller_id, final_price, status, tracking, shipped_at
        (8,  3, 510.00, "pago",    None,             None),
        (10, 5, 410.00, "envio",   None,             None),
        (13, 3,  95.00, "enviado", "MX9876543210",   datetime.now() - timedelta(days=2)),
    ]

    for auction_id, seller_id, price, status, tracking, shipped_at in sales_ganadas:
        exists = db.query(Sale).filter(
            Sale.auction_id == auction_id, Sale.buyer_id == buyer.id
        ).first()
        if not exists:
            sale = Sale(
                auction_id=auction_id,
                seller_id=seller_id,
                buyer_id=buyer.id,
                final_price=price,
                status=status,
                tracking=tracking,
                shipped_at=shipped_at,
                sale_date=datetime.now().date() - timedelta(days=3),
            )
            db.add(sale)
            print(f"  + Sale (ganada) auction {auction_id} status={status}")

    # ── Historial de Compra: received sales ─────────────────────────────────
    sales_historial = [
        # auction_id, seller_id, final_price, received days ago
        (9,  4, 780.00, 5),
        (12, 2, 310.00, 22),
    ]

    for auction_id, seller_id, price, days_ago in sales_historial:
        exists = db.query(Sale).filter(
            Sale.auction_id == auction_id, Sale.buyer_id == buyer.id
        ).first()
        if not exists:
            received = datetime.now() - timedelta(days=days_ago)
            sale = Sale(
                auction_id=auction_id,
                seller_id=seller_id,
                buyer_id=buyer.id,
                final_price=price,
                status="enviado",
                tracking=f"MX00{auction_id}TEST",
                shipped_at=received - timedelta(days=3),
                received_at=received,
                sale_date=(received - timedelta(days=5)).date(),
            )
            db.add(sale)
            print(f"  + Sale (historial) auction {auction_id} received {days_ago}d ago")

    db.commit()
    print("\nDone. Log in as cartasdelsur@rareza.com (password: rareza123) and visit /dashboard")

except Exception as e:
    db.rollback()
    print(f"ERROR: {e}")
    raise
finally:
    db.close()
