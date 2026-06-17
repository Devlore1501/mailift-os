#!/usr/bin/env python3
"""Inietta dati FB Ads (passati come JSON) nel Google Sheet Daily Metrics.

Usato quando il token Graph API non è disponibile: Claude recupera i dati
via MCP Facebook Ads e li passa a questo script come JSON.

Usage:
    python tools/fb_mcp_inject.py '{"2026-06-17": {"spend": 45.2, "impressions": 3200, ...}}'
    python tools/fb_mcp_inject.py --file /tmp/fb_data.json

Formato JSON atteso — dict keyed by date (YYYY-MM-DD):
{
  "2026-06-17": {
    "spend": 45.20,
    "impressions": 3200,
    "reach": 2800,
    "clicks": 120,
    "ctr": 3.75,
    "cpm": 14.12,
    "cpc": 0.38,
    "fb_purchases": 3,
    "fb_purchase_value": 109.70,
    "roas": 2.43
  }
}
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import gspread
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

SPREADSHEET_ID = os.environ.get("GSHEETS_SPREADSHEET_ID", "")
TOKEN_FILE = PROJECT_ROOT / "tokens" / "gsheets.json"
GSHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# Posizioni colonne in Daily Metrics (0-indexed, dopo "Data")
COL_SPEND = 2        # B
COL_IMPRESSIONS = 3  # C
COL_REACH = 4        # D
COL_CLICKS = 5       # E
COL_CTR = 6          # F
COL_CPM = 7          # G
COL_CPC = 8          # H
COL_PURCHASES = 9    # I
COL_PURCHASE_VAL = 10 # J
COL_ROAS = 11        # K


def inject(fb_by_date: dict[str, dict]) -> None:
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), GSHEETS_SCOPES)
    gc = gspread.authorize(creds)
    ss = gc.open_by_key(SPREADSHEET_ID)
    ws = ss.worksheet("Daily Metrics")

    all_values = ws.get_all_values()
    if not all_values:
        print("❌ Foglio vuoto")
        return

    updated = 0
    for i, row in enumerate(all_values[1:], start=2):  # skip header, 1-indexed
        date = row[0] if row else ""
        if date not in fb_by_date:
            continue
        fb = fb_by_date[date]

        # Aggiorna le celle FB per questa riga
        updates = [
            gspread.Cell(i, 2, fb.get("spend", "")),
            gspread.Cell(i, 3, fb.get("impressions", "")),
            gspread.Cell(i, 4, fb.get("reach", "")),
            gspread.Cell(i, 5, fb.get("clicks", "")),
            gspread.Cell(i, 6, fb.get("ctr", "")),
            gspread.Cell(i, 7, fb.get("cpm", "")),
            gspread.Cell(i, 8, fb.get("cpc", "")),
            gspread.Cell(i, 9, fb.get("fb_purchases", "")),
            gspread.Cell(i, 10, fb.get("fb_purchase_value", "")),
            gspread.Cell(i, 11, fb.get("roas", "")),
        ]
        ws.update_cells(updates, value_input_option="USER_ENTERED")

        # Aggiorna anche il Profitto (col 20) = GHL revenue - spend
        try:
            ghl_rev = float(row[18]) if len(row) > 18 and row[18] else 0
            spend = float(fb.get("spend", 0) or 0)
            profit = round(ghl_rev - spend, 2)
            ws.update_cell(i, 20, profit)
        except (ValueError, IndexError):
            pass

        print(f"  ✓ {date} → spend={fb.get('spend')} | impressioni={fb.get('impressions')} | ROAS={fb.get('roas')}")
        updated += 1

    print(f"\n✅ {updated} giorni aggiornati con dati FB")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/fb_mcp_inject.py '<json>' | --file path.json")
        sys.exit(1)

    if sys.argv[1] == "--file":
        data = json.loads(Path(sys.argv[2]).read_text())
    else:
        data = json.loads(sys.argv[1])

    inject(data)
