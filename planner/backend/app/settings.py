"""Configurazione Mailift Planner backend.

Le chiavi API globali (Claude, Notion) arrivano da env / .env.
Le chiavi Klaviyo sono per-brand e vivono nel DB.
Le impostazioni Notion (token, database template, pagina calendario) sono
modificabili anche a runtime via API e persistite nel DB (tabella settings);
l'env fa da valore iniziale.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent.parent  # repo root (mailift-os)

# Stessa convenzione dei tools: ~/.secrets/mailift/.env se esiste, altrimenti .env di repo
_SECRETS_ENV = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(_SECRETS_ENV if _SECRETS_ENV.exists() else PROJECT_ROOT / ".env")

DATA_DIR = Path(os.environ.get("PLANNER_DATA_DIR", BACKEND_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "planner.db"

VERSION = "0.1.0"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("PLANNER_CLAUDE_MODEL", "claude-opus-4-8")

# Valori iniziali Notion (sovrascrivibili via API /settings/notion)
NOTION_TOKEN_ENV = os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY") or ""
NOTION_TEMPLATES_DB_ID_ENV = os.environ.get("NOTION_TEMPLATES_DB_ID", "")
NOTION_CALENDAR_PARENT_ID_ENV = os.environ.get("NOTION_CALENDAR_PARENT_ID", "")


def mock_mode() -> bool:
    """True quando manca la chiave Anthropic: generazione demo deterministica."""
    return not ANTHROPIC_API_KEY
