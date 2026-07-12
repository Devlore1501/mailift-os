"""Configurazione backend: path, env, chiavi API (solo server-side, NFR-03)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent.parent  # root del repo mailift-os

# .env del repo root (stesso file usato da tools/)
load_dotenv(ROOT_DIR / ".env")

TMP_DIR = BACKEND_DIR / ".tmp"
TMP_DIR.mkdir(exist_ok=True)

DB_PATH = os.environ.get("CONTENT_DASHBOARD_DB", str(TMP_DIR / "content_dashboard.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("CONTENT_DASHBOARD_MODEL", "claude-sonnet-5")

CORS_ORIGINS = [
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

SESSION_TTL_DAYS = 30
