"""FastAPI entrypoint."""
from __future__ import annotations

# IMPORTANTE: settings deve essere importato per primo (sys.path injection)
from app import settings  # noqa: F401

import logging
import logging.handlers
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import autofatture, history, jobs, statements, suppliers, system
from app.db import init_db


def _setup_logging() -> None:
    """Configura root logger: stdout + webapp/backend/.tmp/backend.log (rotating)."""
    # backend-local log dir, distinto da webapp/.tmp/ (DB + upload statements)
    from pathlib import Path as _P
    log_dir = _P(__file__).resolve().parent.parent / ".tmp"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "backend.log"

    fmt = logging.Formatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    # Evita doppia configurazione (uvicorn reload)
    if getattr(root, "_mailift_configured", False):
        return
    root.setLevel(logging.INFO)

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    root.addHandler(stream)

    file_h = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_h.setFormatter(fmt)
    root.addHandler(file_h)

    # Uvicorn logger: evita handler duplicati
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True

    root._mailift_configured = True  # type: ignore[attr-defined]
    logging.getLogger("app.main").info("logging configured → %s", log_path)


_setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logging.getLogger("app.main").info("backend lifespan start: db initialized")
    yield
    logging.getLogger("app.main").info("backend lifespan stop")


app = FastAPI(
    title="Autofatture Web App",
    version="0.2.0",
    description="Web UI per emettere autofatture passive (TD17/18/19) su Fatture in Cloud",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(statements.router)
app.include_router(autofatture.router)
app.include_router(jobs.router)
app.include_router(suppliers.router)
app.include_router(history.router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "autofatture-webapp-backend",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/api/health",
    }
