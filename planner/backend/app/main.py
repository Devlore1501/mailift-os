"""Mailift Planner — backend FastAPI.

Avvio dev:
    uvicorn app.main:app --port 8001 --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text

from .db import Base, engine
from .api import brands, catalog, integrations, plans, system, templates

Base.metadata.create_all(bind=engine)


def _migrate() -> None:
    """Micro-migrazioni per DB SQLite già esistenti (create_all non altera tabelle)."""
    with engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(brands)"))}
        if "country" not in cols:
            conn.execute(
                text("ALTER TABLE brands ADD COLUMN country VARCHAR(5) DEFAULT 'IT'")
            )
        tcols = {row[1] for row in conn.execute(text("PRAGMA table_info(templates)"))}
        if tcols and "preview_url" not in tcols:
            conn.execute(
                text("ALTER TABLE templates ADD COLUMN preview_url VARCHAR(600) DEFAULT ''")
            )
        ecols = {row[1] for row in conn.execute(text("PRAGMA table_info(plan_emails)"))}
        if ecols and "format" not in ecols:
            conn.execute(
                text("ALTER TABLE plan_emails ADD COLUMN format VARCHAR(20) DEFAULT 'grafica'")
            )
        if ecols and "blocks" not in ecols:
            conn.execute(text("ALTER TABLE plan_emails ADD COLUMN blocks JSON DEFAULT '[]'"))
        if ecols and "campaign" not in ecols:
            conn.execute(text("ALTER TABLE plan_emails ADD COLUMN campaign JSON"))
        pcols = {row[1] for row in conn.execute(text("PRAGMA table_info(plans)"))}
        if pcols and "campaigns" not in pcols:
            conn.execute(text("ALTER TABLE plans ADD COLUMN campaigns JSON"))


_migrate()

app = FastAPI(title="Mailift Planner", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(brands.router)
app.include_router(catalog.router)
app.include_router(integrations.router)
app.include_router(templates.router)
app.include_router(plans.router)
