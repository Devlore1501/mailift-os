"""Path/env setup. Carica il .env delle credenziali e inietta tools/ in sys.path.

In locale tutto vive nel repo come prima. Online (Docker) le variabili
d'ambiente spostano i dati su un volume persistente:

    WEBAPP_DATA_DIR   DB, estratti caricati (default: webapp/backend/.tmp)
    MAILIFT_ENV_PATH  file .env con FIC_* e ANTHROPIC_API_KEY; il refresh del
                      token FiC lo riscrive, quindi deve stare sul volume
    WEBAPP_PASSWORD   password di accesso; se vuota l'auth e' disattivata
                      (solo per uso locale)
    WEBAPP_SECRET     chiave per firmare il cookie di sessione
    WEBAPP_DEV        "true" abilita CORS per il dev server Vite su :5173
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv

# webapp/backend/app/settings.py -> parents[3] = root del progetto "workflow ai"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = PROJECT_ROOT / "tools"
ENV_PATH = Path(os.environ.get("MAILIFT_ENV_PATH") or Path.home() / ".secrets" / "mailift" / ".env")
if not ENV_PATH.exists():
    ENV_PATH = PROJECT_ROOT / ".env"  # Fallback per compatibilità
TMP_DIR = Path(os.environ.get("WEBAPP_DATA_DIR") or Path(__file__).resolve().parents[1] / ".tmp")
TMP_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DIST = Path(os.environ.get("WEBAPP_FRONTEND_DIST") or PROJECT_ROOT / "webapp" / "frontend" / "dist")

def _bootstrap_persistent_secrets() -> None:
    """Primo avvio online: porta sul volume i segreti che il server riscrive.

    Il refresh del token FiC e quello dei token Gmail aggiornano dei file: se
    restassero solo variabili d'ambiente dell'host, a ogni riavvio si
    ripartirebbe dal token vecchio. Al primo avvio quindi si copiano su file:
      - FIC_*                      -> MAILIFT_ENV_PATH
      - GMAIL_TOKEN_<ACCOUNT>_JSON -> GMAIL_TOKEN_<ACCOUNT> (path del token)
    Dal secondo avvio in poi i file sul volume sono la fonte di verita'.
    """
    env_file = os.environ.get("MAILIFT_ENV_PATH")
    if env_file and not Path(env_file).exists():
        fic = {k: v for k, v in os.environ.items() if k.startswith("FIC_")}
        if fic:
            Path(env_file).parent.mkdir(parents=True, exist_ok=True)
            Path(env_file).write_text("".join(f"{k}={v}\n" for k, v in sorted(fic.items())))
            os.chmod(env_file, 0o600)
    for account in ("PERSONAL", "BUSINESS"):
        content = os.environ.get(f"GMAIL_TOKEN_{account}_JSON")
        target = os.environ.get(f"GMAIL_TOKEN_{account}")
        if content and target and not Path(target).exists():
            Path(target).parent.mkdir(parents=True, exist_ok=True)
            Path(target).write_text(content)
            os.chmod(target, 0o600)


_bootstrap_persistent_secrets()

# Carica .env del progetto principale (credenziali Mailift, FiC, Anthropic).
# Online il file sul volume vince sulle variabili dell'host: contiene i token
# FiC aggiornati dall'ultimo refresh.
load_dotenv(ENV_PATH, override=bool(os.environ.get("MAILIFT_ENV_PATH")))

# Inietta tools/ in sys.path PRIMA di qualsiasi import dei moduli wrapper
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


def _flag(name: str) -> bool:
    return os.getenv(name, "false").lower() in {"1", "true", "yes"}


# Allow disabling real FiC writes via env (es. test e2e)
DRY_RUN_DEFAULT = _flag("WEBAPP_DRY_RUN")
DEV_MODE = _flag("WEBAPP_DEV")

PASSWORD = os.getenv("WEBAPP_PASSWORD", "")
# Senza WEBAPP_SECRET la chiave cambia a ogni riavvio: le sessioni scadono, niente di peggio.
SECRET = os.getenv("WEBAPP_SECRET") or secrets.token_hex(32)
SESSION_HOURS = int(os.getenv("WEBAPP_SESSION_HOURS", "12"))
# Dietro HTTPS (deploy) il cookie deve essere Secure; in locale su http no.
COOKIE_SECURE = _flag("WEBAPP_COOKIE_SECURE")
