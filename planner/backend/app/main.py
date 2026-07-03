"""Mailift Planner — backend FastAPI.

Avvio dev:
    uvicorn app.main:app --port 8001 --reload
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy import inspect, text

from .db import Base, engine
from .api import brands, catalog, integrations, plans, system, templates

Base.metadata.create_all(bind=engine)


def _migrate() -> None:
    """Micro-migrazioni per DB già esistenti (create_all non altera tabelle).

    Dialect-agnostic (SQLite in locale, Postgres in produzione): usa
    sqlalchemy.inspect invece di PRAGMA table_info.
    """
    with engine.begin() as conn:
        insp = inspect(conn)

        def cols(table: str) -> set[str]:
            if table not in insp.get_table_names():
                return set()
            return {c["name"] for c in insp.get_columns(table)}

        if "country" not in cols("brands"):
            conn.execute(
                text("ALTER TABLE brands ADD COLUMN country VARCHAR(5) DEFAULT 'IT'")
            )
        if "preview_url" not in cols("templates"):
            conn.execute(
                text("ALTER TABLE templates ADD COLUMN preview_url VARCHAR(600) DEFAULT ''")
            )
        ecols = cols("plan_emails")
        if "format" not in ecols:
            conn.execute(
                text("ALTER TABLE plan_emails ADD COLUMN format VARCHAR(20) DEFAULT 'grafica'")
            )
        if "blocks" not in ecols:
            conn.execute(text("ALTER TABLE plan_emails ADD COLUMN blocks JSON"))
        if "campaign" not in ecols:
            conn.execute(text("ALTER TABLE plan_emails ADD COLUMN campaign JSON"))
        if "campaigns" not in cols("plans"):
            conn.execute(text("ALTER TABLE plans ADD COLUMN campaigns JSON"))


_migrate()

app = FastAPI(title="Mailift Planner", version="0.1.0")

_extra_origins = [
    o.strip() for o in os.environ.get("PLANNER_CORS_ORIGINS", "").split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174", *_extra_origins],
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

# Serve la build del frontend (React) se presente: un solo servizio in
# produzione (Docker build multi-stage, vedi planner/Dockerfile). In sviluppo
# locale la variabile non è impostata e il frontend gira separato via Vite.
_frontend_dist = os.environ.get("PLANNER_FRONTEND_DIST", "")
if _frontend_dist and Path(_frontend_dist).is_dir():
    _dist = Path(_frontend_dist)
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(404, "Not found")
        candidate = _dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")
