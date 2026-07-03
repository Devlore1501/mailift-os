from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .settings import DB_PATH


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    """SQLite in locale/mock; Postgres in produzione via DATABASE_URL (es. Railway).

    Railway/Heroku forniscono lo schema "postgres://", SQLAlchemy + psycopg 3
    vogliono "postgresql+psycopg://".
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return f"sqlite:///{DB_PATH}"
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


DATABASE_URL = _database_url()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
