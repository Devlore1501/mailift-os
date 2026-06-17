"""SQLAlchemy engine + session management per la webapp.

DB sync su SQLite, file in `.tmp/webapp.db`. Niente migrazioni Alembic per ora.
`init_db()` viene chiamato nel lifespan di FastAPI e crea tutte le tabelle.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app import settings

DB_PATH = settings.TMP_DIR / "webapp.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    # Import tardivo per registrare i modelli su Base.metadata
    from app.models import db_models  # noqa: F401
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency. Esempio:

        @router.get(...)
        def endpoint(db: Session = Depends(get_db)): ...
    """
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
