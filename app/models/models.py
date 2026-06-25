from sqlalchemy import (
    Column, Integer, String, Text, DECIMAL, Enum, Boolean,
    DateTime, Date, ForeignKey, func
)
from sqlalchemy.orm import relationship
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100))
    rating = Column(DECIMAL(2, 1), default=5.0)
    sales_count = Column(Integer, default=0)
    location = Column(String(100), default="Argentina")
    phone = Column(String(30))
    shipping_address = Column(String(255))
    facebook_id = Column(String(64), default=None)
    facebook_name = Column(String(255), default=None)
    created_at = Column(DateTime, server_default=func.now())

    store = relationship("Store", back_populates="user", uselist=False)
    auctions = relationship("Auction", back_populates="seller")
    bids = relationship("Bid", back_populates="bidder")
    max_bids = relationship("MaxBid", back_populates="bidder")
    watched = relationship("Watched", back_populates="user")
    sales_as_seller = relationship("Sale", foreign_keys="Sale.seller_id", back_populates="seller")
    sales_as_buyer = relationship("Sale", foreign_keys="Sale.buyer_id", back_populates="buyer")


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name = Column(String(100))
    bio = Column(Text)
    logo_path = Column(String(255))
    country = Column(String(100), default="Argentina")
    ship_nacional = Column(Boolean, default=True)
    cost_nacional = Column(DECIMAL(10, 2), default=5.00)
    ship_regional = Column(Boolean, default=False)
    cost_regional = Column(DECIMAL(10, 2), default=15.00)
    ship_intl = Column(Boolean, default=False)
    cost_intl = Column(DECIMAL(10, 2), default=0.00)
    free_over_on = Column(Boolean, default=False)
    free_over = Column(DECIMAL(10, 2), default=0.00)
    handling = Column(String(50), default="2 días hábiles")
    returns_policy = Column(String(50), default="No acepta devoluciones")
    tracked = Column(Boolean, default=False)
    win_message = Column(String(500))

    user = relationship("User", back_populates="store")


class Auction(Base):
    __tablename__ = "auctions"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String(255), nullable=False)
    game = Column(String(50))
    set_name = Column(String(100))
    rarity = Column(String(100))
    grade = Column(String(50))
    condition = Column(String(50))
    language = Column(String(50), default="Español")
    notes = Column(Text)
    sale_type = Column(Enum("subasta", "fijo"), default="subasta")
    start_price = Column(DECIMAL(10, 2), default=0.00)
    bid_increment = Column(DECIMAL(10, 2), default=50.00)
    buy_now_price = Column(DECIMAL(10, 2))
    current_bid = Column(DECIMAL(10, 2), default=0.00)
    bid_count = Column(Integer, default=0)
    watchers_count = Column(Integer, default=0)
    accepts_offers = Column(Boolean, default=False)
    is_lot = Column(Boolean, default=False)
    duration_days = Column(Integer, default=7)
    ends_at = Column(DateTime, nullable=False)
    status = Column(Enum("active", "ended", "sold"), default="active")
    hue = Column(Integer, default=40)
    image_path = Column(String(255))
    back_image_path = Column(String(255))
    detail_image_path = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())

    seller = relationship("User", back_populates="auctions")
    bids = relationship("Bid", back_populates="auction", order_by="Bid.created_at.desc()")
    max_bids = relationship("MaxBid", back_populates="auction")
    watched_by = relationship("Watched", back_populates="auction")
    sale = relationship("Sale", back_populates="auction", uselist=False)


class MaxBid(Base):
    __tablename__ = "max_bids"

    id = Column(Integer, primary_key=True)
    auction_id = Column(Integer, ForeignKey("auctions.id", ondelete="CASCADE"))
    bidder_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    max_amount = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    auction = relationship("Auction", back_populates="max_bids")
    bidder = relationship("User", back_populates="max_bids")


class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True)
    auction_id = Column(Integer, ForeignKey("auctions.id", ondelete="CASCADE"))
    bidder_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    amount = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    auction = relationship("Auction", back_populates="bids")
    bidder = relationship("User", back_populates="bids")


class Watched(Base):
    __tablename__ = "watched"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    auction_id = Column(Integer, ForeignKey("auctions.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="watched")
    auction = relationship("Auction", back_populates="watched_by")


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    auction_id = Column(Integer, ForeignKey("auctions.id"))
    seller_id = Column(Integer, ForeignKey("users.id"))
    buyer_id = Column(Integer, ForeignKey("users.id"))
    final_price = Column(DECIMAL(10, 2), nullable=False)
    status = Column(Enum("pago", "envio", "enviado"), default="pago")
    tracking = Column(String(100))
    sale_date = Column(Date, server_default=func.current_date())
    created_at = Column(DateTime, server_default=func.now())

    auction = relationship("Auction", back_populates="sale")
    seller = relationship("User", foreign_keys=[seller_id], back_populates="sales_as_seller")
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="sales_as_buyer")
    messages = relationship("Message", back_populates="sale", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey("sales.id", ondelete="CASCADE"), index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    body = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    sale = relationship("Sale", back_populates="messages")
    sender = relationship("User")
