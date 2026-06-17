"""Path/env setup. Carica il .env del progetto root e inietta tools/ in sys.path."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# webapp/backend/app/settings.py -> parents[3] = root del progetto "workflow ai"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = PROJECT_ROOT / "tools"
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
if not ENV_PATH.exists():
    ENV_PATH = PROJECT_ROOT / ".env"  # Fallback per compatibilità
TMP_DIR = Path(__file__).resolve().parents[2] / ".tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Carica .env del progetto principale (credenziali Mailift, FiC, Anthropic)
load_dotenv(ENV_PATH)

# Inietta tools/ in sys.path PRIMA di qualsiasi import dei moduli wrapper
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

# Allow disabling real FiC writes via env (es. test e2e)
DRY_RUN_DEFAULT = os.getenv("WEBAPP_DRY_RUN", "false").lower() in {"1", "true", "yes"}
