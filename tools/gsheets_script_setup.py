#!/usr/bin/env python3
"""Deploya l'Apps Script Mailift Sync nel Google Sheet.

Crea un menu '🔄 Mailift Sync' nel foglio con voci:
  • Sync oggi
  • Sync ultimi 7 giorni
  • Sync ultimi 30 giorni

Usage:
    python tools/gsheets_script_setup.py

Prerequisiti:
    - GSHEETS_SPREADSHEET_ID nel .env
    - Apps Script API abilitata:
      https://console.cloud.google.com/apis/library/script.googleapis.com
    - Stesse credenziali OAuth di gsheets_oauth_setup.py

Dopo il deployment, impostare le proprietà script nel foglio:
    Estensioni → Apps Script → ⚙️ Impostazioni progetto → Proprietà script
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

CREDENTIALS_FILE = Path.home() / ".secrets" / "mailift" / "credentials_gmail.json"
TOKEN_FILE       = PROJECT_ROOT / "tokens" / "apps_script.json"
SCRIPT_FILE      = PROJECT_ROOT / "tools" / "mailift_sync.gs"
SCRIPT_ID_FILE   = PROJECT_ROOT / "tokens" / "apps_script_id.txt"

SCOPES = [
    "https://www.googleapis.com/auth/script.projects",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

SPREADSHEET_ID = os.environ.get("GSHEETS_SPREADSHEET_ID", "")

APPSSCRIPT_MANIFEST = json.dumps({
    "timeZone": "Europe/Rome",
    "exceptionLogging": "STACKDRIVER",
    "runtimeVersion": "V8",
    "oauthScopes": [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/script.external_request",
    ],
})


def get_creds() -> Credentials:
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
    return creds


def _h(creds: Credentials) -> dict:
    return {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}


def get_or_create_script(creds: Credentials) -> str:
    if SCRIPT_ID_FILE.exists():
        sid = SCRIPT_ID_FILE.read_text().strip()
        r = requests.get(f"https://script.googleapis.com/v1/projects/{sid}", headers=_h(creds))
        if r.status_code == 200:
            print(f"  ✓ Script esistente: {sid}")
            return sid
        print("  → Script ID non valido, ne creo uno nuovo...")

    r = requests.post(
        "https://script.googleapis.com/v1/projects",
        headers=_h(creds),
        json={"title": "Mailift Sync", "parentId": SPREADSHEET_ID},
    )
    if r.status_code != 200:
        print(f"  DEBUG status: {r.status_code}")
        print(f"  DEBUG body: {r.text[:600]}")
        err = r.json().get("error", {})
        if err.get("code") in (403, 401):
            raise RuntimeError(
                "❌ Apps Script API non abilitata o accesso negato.\n"
                "   Abilita qui: https://console.cloud.google.com/apis/library/script.googleapis.com\n"
                "   Poi riprova."
            )
        raise RuntimeError(f"Errore creazione script: {r.status_code} — {r.text[:300]}")

    sid = r.json()["scriptId"]
    SCRIPT_ID_FILE.write_text(sid)
    print(f"  ✓ Script creato: {sid}")
    return sid


def push_code(creds: Credentials, script_id: str) -> None:
    gs_code = SCRIPT_FILE.read_text()
    r = requests.put(
        f"https://script.googleapis.com/v1/projects/{script_id}/content",
        headers=_h(creds),
        json={
            "files": [
                {"name": "mailift_sync", "type": "SERVER_JS",  "source": gs_code},
                {"name": "appsscript",   "type": "JSON",       "source": APPSSCRIPT_MANIFEST},
            ]
        },
    )
    if r.status_code != 200:
        raise RuntimeError(f"Errore push codice: {r.status_code} — {r.text[:300]}")
    print("  ✓ Codice sincronizzato")


def print_props_instructions() -> None:
    props = {
        "GHL_API_KEY":      os.environ.get("GHL_API_KEY",      ""),
        "GHL_LOCATION_ID":  os.environ.get("GHL_LOCATION_ID",  ""),
        "FB_ACCESS_TOKEN":  os.environ.get("FB_ACCESS_TOKEN",  ""),
        "FB_AD_ACCOUNT_ID": os.environ.get("FB_AD_ACCOUNT_ID", ""),
    }
    print("\n📋 Ultimo step — imposta le proprietà script nel foglio:")
    print("   Estensioni → Apps Script → ⚙️ Impostazioni progetto → Proprietà script → Aggiungi")
    print()
    for k, v in props.items():
        if v:
            display = v[:14] + "..." if len(v) > 14 else v
            print(f"   {k:<20} = {display}")
        else:
            print(f"   {k:<20} = ⚠️ non trovato nel .env")


def setup() -> None:
    if not SPREADSHEET_ID:
        raise RuntimeError("GSHEETS_SPREADSHEET_ID non configurato nel .env")
    if not SCRIPT_FILE.exists():
        raise RuntimeError(f"File .gs non trovato: {SCRIPT_FILE}")

    print("[gsheets-script-setup] Deployment Apps Script...")
    creds     = get_creds()
    script_id = get_or_create_script(creds)
    push_code(creds, script_id)
    print_props_instructions()
    print(f"\n✅ Apps Script deployato!")
    print(f"   Riapri il foglio — comparirà il menu '🔄 Mailift Sync'")
    print(f"   Script ID: {script_id}")
    print(f"   Script URL: https://script.google.com/d/{script_id}/edit")


if __name__ == "__main__":
    try:
        setup()
    except RuntimeError as e:
        print(f"\n{e}")
        sys.exit(1)
