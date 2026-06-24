from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import get_settings
import logging
import os

logger = logging.getLogger(__name__)

# Debug: show all DB-related env vars Railway provides
for key in sorted(os.environ):
    if any(k in key.upper() for k in ["MYSQL", "DATABASE", "DB_"]):
        val = os.environ[key]
        if "@" in val:
            val = "..." + val.split("@")[-1]
        logger.warning(f"ENV {key} = {val}")

settings = get_settings()

db_url = settings.database_url
safe_url = db_url.split("@")[-1] if "@" in db_url else db_url
logger.warning(f"Connecting to database: ...@{safe_url}")

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
