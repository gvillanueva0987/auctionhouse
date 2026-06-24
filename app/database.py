from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

print(f"[DB] DATABASE_URL set: {bool(os.environ.get('DATABASE_URL'))}", flush=True)
print(f"[DB] MYSQL_URL set: {bool(os.environ.get('MYSQL_URL'))}", flush=True)
print(f"[DB] Total env vars: {len(os.environ)}", flush=True)
print(f"[DB] .env file exists: {os.path.exists('.env')}", flush=True)

raw_url = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL") or ""

if raw_url:
    db_url = raw_url
    if db_url.startswith("mysql://"):
        db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)
    if "charset" not in db_url:
        db_url += ("&" if "?" in db_url else "?") + "charset=utf8mb4"
else:
    from .config import get_settings
    db_url = get_settings().database_url

safe_url = db_url.split("@")[-1] if "@" in db_url else db_url
print(f"[DB] Connecting to: ...@{safe_url}", flush=True)

engine = create_engine(
    db_url,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
