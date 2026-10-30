"""Database engine and session management with PostgreSQL and SQLite fallback."""

import logging
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.models.document import Base

logger = logging.getLogger(__name__)

# Ensure data directories exist
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
SQLITE_PATH = DATA_DIR / "enterprise_knowledge.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Build engine: PostgreSQL with SQLite local fallback
def create_app_engine():
    db_url = settings.DATABASE_URL

    # If Postgres URL is provided, test connection; fallback to SQLite if offline
    if "postgresql" in db_url:
        try:
            pg_engine = create_engine(
                db_url,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 3},
            )
            with pg_engine.connect():
                pass
            logger.info("Connected successfully to PostgreSQL database.")
            return pg_engine
        except Exception as e:
            logger.warning(
                f"PostgreSQL at {db_url} unreachable ({e}). Falling back to local SQLite at {SQLITE_PATH}."
            )

    sqlite_url = f"sqlite:///{SQLITE_PATH}"
    logger.info(f"Using SQLite database engine at {sqlite_url}")
    return create_engine(sqlite_url, connect_args={"check_same_thread": False})


engine = create_app_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all registered database tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency to yield a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
