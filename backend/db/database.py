"""
SHIELD Database Layer
─────────────────────
Single source of truth for DB connection, session factory, and FastAPI DI.

Usage in routers:
    from backend.db.database import get_db
    @router.post("/example")
    def example(db: DBSession = Depends(get_db)):
        ...

Usage in seed scripts:
    from backend.db.database import SessionLocal, ENGINE
    db = SessionLocal()
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────
# Connection
# ─────────────────────────────────────────────────────────────

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("DB_PATH", os.path.join(DB_DIR, "shield.db"))

ENGINE = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(bind=ENGINE, autocommit=False, autoflush=False)


# ─────────────────────────────────────────────────────────────
# Declarative Base
# ─────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────────────────────
# Table Initialization
# ─────────────────────────────────────────────────────────────

def init_db():
    """Create all tables. Import models first to register them with Base."""
    from backend.db.models import (  # noqa: F401
        User, Session, Score, SimSwapEvent, AlertLog, DeviceRegistry
    )
    Base.metadata.create_all(bind=ENGINE)


# ─────────────────────────────────────────────────────────────
# FastAPI Dependency Injection
# ─────────────────────────────────────────────────────────────

def get_db():
    """
    Yields a SQLAlchemy session for the duration of a single request.
    Auto-closes on completion. Use with FastAPI Depends().
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
