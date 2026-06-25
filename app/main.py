from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from .routers import auth, auctions, users, pages
from .database import engine, Base
from .models import models  # ensure models are registered
from sqlalchemy import text

Base.metadata.create_all(bind=engine)

# Incremental schema migrations (no Alembic)
with engine.connect() as _conn:
    for _sql in [
        "ALTER TABLE messages ADD COLUMN image_url VARCHAR(500) NULL",
        "ALTER TABLE sales ADD COLUMN shipped_at DATETIME NULL",
    ]:
        try:
            _conn.execute(text(_sql))
            _conn.commit()
        except Exception:
            pass  # column already exists

app = FastAPI(title="Rareza — Subastas de cartas", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("app/uploads", exist_ok=True)
os.makedirs("app/static", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(auctions.router)
app.include_router(users.router)
app.include_router(pages.router)
