"""FastAPI entrypoint."""
from __future__ import annotations

# IMPORTANTE: settings deve essere importato per primo (sys.path injection)
from app import settings  # noqa: F401

import logging
import logging.handlers
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app import auth
from app.api import auth as auth_api
from app.api import archive as archive_api
from app.api import autofatture, history, jobs, sdi, statements, suppliers, system
from app.db import init_db


def _setup_logging() -> None:
    """Configura root logger: stdout + webapp/backend/.tmp/backend.log (rotating)."""
    log_path = settings.TMP_DIR / "backend.log"

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
    nightly = None
    from app.services import scheduler
    if scheduler.enabled():
        import asyncio
        nightly = asyncio.create_task(scheduler.nightly_loop())
    yield
    if nightly:
        nightly.cancel()
    logging.getLogger("app.main").info("backend lifespan stop")


app = FastAPI(
    title="Autofatture Web App",
    version="0.3.0",
    description="Web UI per emettere autofatture passive (TD17/18/19) su Fatture in Cloud",
    lifespan=lifespan,
    # Online la documentazione interattiva esporrebbe tutta l'API: solo in dev.
    docs_url="/docs" if settings.DEV_MODE else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.DEV_MODE else None,
)

if settings.DEV_MODE:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

_PUBLIC_API = {"/api/auth/login", "/api/auth/me", "/api/auth/logout", "/api/healthz"}


@app.middleware("http")
async def require_session(request: Request, call_next):
    path = request.url.path
    if (
        auth.enabled()
        and path.startswith("/api/")
        and path not in _PUBLIC_API
        and not auth.token_valid(request.cookies.get(auth.COOKIE_NAME))
    ):
        return JSONResponse({"detail": "Sessione scaduta, accedi di nuovo"}, status_code=401)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    if path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


app.include_router(auth_api.router)
app.include_router(system.router)
app.include_router(statements.router)
app.include_router(autofatture.router)
app.include_router(sdi.router)
app.include_router(jobs.router)
app.include_router(suppliers.router)
app.include_router(history.router)
app.include_router(archive_api.router)


@app.get("/api/healthz")
def healthz() -> dict[str, str]:
    """Liveness per il load balancer: non tocca FiC ne' Gmail."""
    return {"status": "ok"}


# Frontend buildato (npm run build) servito dallo stesso processo: una sola
# origine, quindi niente CORS e cookie SameSite=Strict funzionanti.
if settings.FRONTEND_DIST.is_dir():
    _dist = settings.FRONTEND_DIST.resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        target = (_dist / full_path).resolve()
        if full_path and target.is_file() and target.is_relative_to(_dist):
            return FileResponse(target)
        return FileResponse(_dist / "index.html", headers={"Cache-Control": "no-cache"})
