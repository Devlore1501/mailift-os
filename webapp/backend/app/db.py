"""SQLAlchemy engine + session management per la webapp.

DB sync su SQLite, file in `.tmp/webapp.db`. Niente migrazioni Alembic per ora.
`init_db()` viene chiamato nel lifespan di FastAPI e crea tutte le tabelle.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app import settings

DB_PATH = settings.TMP_DIR / "webapp.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    # timeout: i job in background scrivono mentre il frontend fa polling
    connect_args={"check_same_thread": False, "timeout": 15},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    """UTC naive, come le colonne DateTime gia' scritte su SQLite (datetime.utcnow e' deprecato)."""
    return datetime.now(UTC).replace(tzinfo=None)


def init_db() -> None:
    # Import tardivo per registrare i modelli su Base.metadata
    from app.models import db_models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def _add_missing_columns() -> None:
    """create_all non tocca le tabelle esistenti: aggiunge le colonne nuove.

    Basta per colonne nullable aggiunte ai modelli; per cambi piu' invasivi
    servira' Alembic.
    """
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            present = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name not in present and col.nullable:
                    ddl = col.type.compile(dialect=engine.dialect)
                    conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN "{col.name}" {ddl}'))


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
