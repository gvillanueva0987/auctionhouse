from datetime import datetime
from decimal import Decimal
from typing import Any
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, auction_id: int):
        await websocket.accept()
        self.connections.setdefault(auction_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, auction_id: int):
        conns = self.connections.get(auction_id, [])
        if websocket in conns:
            conns.remove(websocket)

    async def broadcast(self, auction_id: int, data: dict):
        for ws in list(self.connections.get(auction_id, [])):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(ws, auction_id)


manager = ConnectionManager()


def fmt_price(amount, currency: str = "$") -> str:
    if amount is None:
        return ""
    n = int(amount)
    formatted = f"{n:,}"
    return f"{currency} {formatted}"


def fmt_countdown(ends_at: datetime) -> dict:
    now = datetime.utcnow()
    rem = (ends_at - now).total_seconds()
    if rem <= 0:
        return {"text": "Finalizada", "urgent": False, "finished": True, "color": "#6c727b"}
    d = int(rem // 86400)
    h = int((rem % 86400) // 3600)
    m = int((rem % 3600) // 60)
    s = int(rem % 60)
    if d > 0:
        text = f"{d}d {h}h"
    elif h > 0:
        text = f"{h}h {m:02d}m"
    else:
        text = f"{m}m {s:02d}s"
    urgent = rem < 3600
    color = "#6c727b" if rem <= 0 else "#e0573f" if rem < 600 else "#e8a13f" if rem < 3600 else "#9aa0a8"
    return {"text": text, "urgent": urgent, "finished": False, "color": color}


def time_ago(dt: datetime) -> str:
    diff = (datetime.utcnow() - dt).total_seconds()
    if diff < 60:
        return f"hace {int(diff)}s"
    elif diff < 3600:
        return f"hace {int(diff // 60)} min"
    elif diff < 86400:
        return f"hace {int(diff // 3600)} h"
    else:
        return f"hace {int(diff // 86400)} d"


def auction_to_card(auction: Any, watched_ids: set, currency: str = "$") -> dict:
    cd = fmt_countdown(auction.ends_at)
    return {
        "id": auction.id,
        "name": auction.title,
        "game": auction.game or "",
        "rarity": auction.rarity or "",
        "grade": auction.grade or "",
        "has_grade": bool(auction.grade),
        "price_text": fmt_price(auction.current_bid, currency),
        "bid_count": auction.bid_count,
        "bid_count_text": f"{auction.bid_count} {'puja' if auction.bid_count == 1 else 'pujas'}",
        "watchers": auction.watchers_count,
        "ends_text": cd["text"],
        "urgent": cd["urgent"],
        "finished": cd["finished"],
        "timer_color": cd["color"],
        "hue": auction.hue,
        "is_watched": auction.id in watched_ids,
        "image_path": auction.image_path,
        "seller": auction.seller,
        "ends_at_ms": int(auction.ends_at.timestamp() * 1000),
    }
