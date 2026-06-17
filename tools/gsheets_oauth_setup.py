#!/usr/bin/env python3
"""Setup OAuth per Google Sheets — eseguire una volta sola.

Usa lo stesso credentials_gmail.json di Gmail/GCal, aggiunge lo scope
spreadsheets. Salva il token in tokens/gsheets.json.

    python tools/gsheets_oauth_setup.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else Path(".env"))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]
CREDENTIALS_FILE = Path.home() / ".secrets" / "mailift" / "credentials_gmail.json"
TOKEN_FILE = PROJECT_ROOT / "tokens" / "gsheets.json"


def setup() -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    print(f"✓ Token salvato in {TOKEN_FILE}")
    print("  Ora puoi usare tools/ads_dashboard_sync.py")


if __name__ == "__main__":
    setup()
