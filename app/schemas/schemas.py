from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    display_name: Optional[str] = None
    location: str = "Argentina"


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    display_name: Optional[str]
    rating: Optional[float]
    sales_count: int
    location: Optional[str]

    class Config:
        from_attributes = True


class BidCreate(BaseModel):
    amount: Decimal


class BidOut(BaseModel):
    id: int
    auction_id: int
    bidder_id: int
    amount: Decimal
    created_at: datetime
    bidder_username: Optional[str] = None

    class Config:
        from_attributes = True


class AuctionCreate(BaseModel):
    title: str
    game: Optional[str] = None
    set_name: Optional[str] = None
    rarity: Optional[str] = None
    grade: Optional[str] = None
    condition: Optional[str] = None
    language: str = "Español"
    notes: Optional[str] = None
    sale_type: str = "subasta"
    start_price: Decimal = Decimal("0")
    buy_now_price: Optional[Decimal] = None
    accepts_offers: bool = False
    duration_days: int = 7


class AuctionOut(BaseModel):
    id: int
    title: str
    game: Optional[str]
    set_name: Optional[str]
    rarity: Optional[str]
    grade: Optional[str]
    condition: Optional[str]
    language: Optional[str]
    sale_type: str
    start_price: Decimal
    buy_now_price: Optional[Decimal]
    current_bid: Decimal
    bid_count: int
    watchers_count: int
    accepts_offers: bool
    ends_at: datetime
    status: str
    hue: int
    image_path: Optional[str]
    seller_id: int

    class Config:
        from_attributes = True


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    country: Optional[str] = None
    ship_nacional: Optional[bool] = None
    cost_nacional: Optional[Decimal] = None
    ship_regional: Optional[bool] = None
    cost_regional: Optional[Decimal] = None
    ship_intl: Optional[bool] = None
    cost_intl: Optional[Decimal] = None
    free_over_on: Optional[bool] = None
    free_over: Optional[Decimal] = None
    handling: Optional[str] = None
    returns_policy: Optional[str] = None
    tracked: Optional[bool] = None
    win_message: Optional[str] = None


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


class FacebookLink(BaseModel):
    access_token: str


class SaleStatusUpdate(BaseModel):
    status: str
    tracking: Optional[str] = None


class MessageCreate(BaseModel):
    body: str


class Token(BaseModel):
    access_token: str
    token_type: str
