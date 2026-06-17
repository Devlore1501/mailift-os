#!/usr/bin/env python3
"""Facebook Ads client — recupera metriche giornaliere via Graph API.

Variabili .env richieste:
  FB_ACCESS_TOKEN   — long-lived user/system token (dura 60 giorni)
  FB_AD_ACCOUNT_ID  — ID numerico o con prefisso "act_"

Come ottenere il token long-lived:
  1. Vai su business.facebook.com → Impostazioni → Utenti di sistema
  2. Crea "Utente di sistema admin" → Genera token (scopes: ads_read, ads_management)
  3. Oppure: usa il Graph API Explorer → estendi a 60 giorni

CLI:
  python tools/fb_ads_client.py today
  python tools/fb_ads_client.py days 7
  python tools/fb_ads_client.py date 2026-06-17
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN", "")
AD_ACCOUNT_ID = os.environ.get("FB_AD_ACCOUNT_ID", "")
API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{API_VERSION}"

INSIGHT_FIELDS = [
    "date_start",
    "spend",
    "impressions",
    "reach",
    "clicks",
    "ctr",
    "cpm",
    "cpc",
    "actions",
    "action_values",
    "purchase_roas",
]


def _configured() -> bool:
    return bool(ACCESS_TOKEN and AD_ACCOUNT_ID)


def _account_id() -> str:
    aid = AD_ACCOUNT_ID.strip()
    return f"act_{aid}" if not aid.startswith("act_") else aid


def _action_val(lst: list[dict], action_type: str) -> float:
    for a in lst or []:
        if a.get("action_type") == action_type:
            return float(a.get("value", 0))
    return 0.0


def fetch_daily_insights(start_date: str, end_date: str) -> list[dict]:
    """
    Recupera insight giornalieri per l'ad account configurato.
    Ritorna lista di dict normalizzati (una riga per giorno).
    """
    if not _configured():
        print("⚠️  FB_ACCESS_TOKEN o FB_AD_ACCOUNT_ID non configurati")
        return []

    url = f"{GRAPH_BASE}/{_account_id()}/insights"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": ",".join(INSIGHT_FIELDS),
        "time_range": f'{{"since":"{start_date}","until":"{end_date}"}}',
        "time_increment": "1",
        "level": "account",
        "limit": 100,
    }

    rows = []
    while url:
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code != 200:
            err = resp.json().get("error", {})
            print(f"❌ FB API {resp.status_code}: {err.get('message', resp.text[:100])}")
            break
        data = resp.json()
        rows.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}

    return [_normalize(r) for r in rows]


def _normalize(raw: dict) -> dict:
    actions = raw.get("actions", [])
    action_values = raw.get("action_values", [])
    purchases = _action_val(actions, "purchase")
    purchase_value = _action_val(action_values, "purchase")
    spend = float(raw.get("spend", 0))
    roas_list = raw.get("purchase_roas", [])
    roas = float(roas_list[0]["value"]) if roas_list else (purchase_value / spend if spend else 0)

    return {
        "date": raw.get("date_start", ""),
        "spend": round(spend, 2),
        "impressions": int(raw.get("impressions", 0)),
        "reach": int(raw.get("reach", 0)),
        "clicks": int(raw.get("clicks", 0)),
        "ctr": round(float(raw.get("ctr", 0)), 3),
        "cpm": round(float(raw.get("cpm", 0)), 2),
        "cpc": round(float(raw.get("cpc", 0)), 2),
        "fb_purchases": int(purchases),
        "fb_purchase_value": round(purchase_value, 2),
        "roas": round(roas, 2),
    }


def as_dict_by_date(start_date: str, end_date: str) -> dict[str, dict]:
    rows = fetch_daily_insights(start_date, end_date)
    return {r["date"]: r for r in rows}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "today"
    today = datetime.now(timezone.utc).date().isoformat()

    if cmd == "today":
        start, end = today, today
    elif cmd == "days" and len(sys.argv) > 2:
        n = int(sys.argv[2])
        start = (datetime.now(timezone.utc).date() - timedelta(days=n - 1)).isoformat()
        end = today
    elif cmd == "date" and len(sys.argv) > 2:
        start = end = sys.argv[2]
    else:
        print("Usage: python tools/fb_ads_client.py [today|days N|date YYYY-MM-DD]")
        sys.exit(1)

    if not _configured():
        print("⚠️  Configura FB_ACCESS_TOKEN e FB_AD_ACCOUNT_ID nel .env")
        sys.exit(1)

    rows = fetch_daily_insights(start, end)
    if not rows:
        print("Nessun dato FB per il periodo selezionato.")
    else:
        print(f"{'Data':<12} {'Spend':>8} {'Impr':>8} {'Click':>6} {'CTR':>6} {'CPC':>6} {'ROAS':>6} {'Acquisti':>9} {'RevFB':>8}")
        print("-" * 85)
        for r in rows:
            print(f"{r['date']:<12} {r['spend']:>8.2f} {r['impressions']:>8} {r['clicks']:>6} {r['ctr']:>6.2f}% {r['cpc']:>6.2f} {r['roas']:>6.2f} {r['fb_purchases']:>9} {r['fb_purchase_value']:>8.2f}")
