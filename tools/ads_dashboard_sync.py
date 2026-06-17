#!/usr/bin/env python3
"""Ads Dashboard Sync — sincronizza GHL orders + Facebook Ads su Google Sheets.

Struttura del Google Sheet (3 tab):
  1. "Daily Metrics"  — una riga per giorno: FB spend, clicks, revenue, ROAS
  2. "Orders Log"     — ogni ordine/prodotto venduto (FE/BUMP/OTO)
  3. "Prodotti"       — aggregato per prodotto

Variabili .env richieste:
  GHL_API_KEY, GHL_LOCATION_ID
  FB_ACCESS_TOKEN        — long-lived token da Meta Business Manager
  FB_AD_ACCOUNT_ID       — es. "act_123456789" o solo "123456789"
  GSHEETS_SPREADSHEET_ID — ID del Google Sheet (dalla URL)

Setup:
  1. python tools/gsheets_oauth_setup.py  (una volta)
  2. Aggiungi FB_ACCESS_TOKEN e FB_AD_ACCOUNT_ID nel .env
  3. Crea un Google Sheet vuoto e copia l'ID nell'URL nel .env
  4. python tools/ads_dashboard_sync.py           → sync ultimi 30 giorni
  5. python tools/ads_dashboard_sync.py today     → sync solo oggi
  6. python tools/ads_dashboard_sync.py days 7   → sync ultimi 7 giorni

Schedulabile con cron:
  0 8 * * * /path/to/.venv/bin/python /path/to/tools/ads_dashboard_sync.py today
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
import gspread
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

# Allow importing sibling tools
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Credenziali ──────────────────────────────────────────────────────────────

SPREADSHEET_ID = os.environ.get("GSHEETS_SPREADSHEET_ID", "")
TOKEN_FILE = PROJECT_ROOT / "tokens" / "gsheets.json"
GSHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# ── Facebook Ads ─────────────────────────────────────────────────────────────

def _empty_fb() -> dict:
    return {
        "spend": 0, "impressions": "", "reach": "", "clicks": "", "ctr": "",
        "cpm": "", "cpc": "", "fb_purchases": "", "fb_purchase_value": "", "roas": "",
    }


# ── Google Sheets ────────────────────────────────────────────────────────────

DAILY_HEADERS = [
    "Data",
    "FB Spend (€)", "Impressioni", "Reach", "Click", "CTR (%)", "CPM (€)", "CPC (€)",
    "FB Acquisti", "FB Revenue (€)", "ROAS",
    "FE Ordini", "FE Revenue (€)",
    "BUMP Ordini", "BUMP Revenue (€)",
    "OTO Ordini", "OTO Revenue (€)",
    "TOT Ordini", "TOT Revenue GHL (€)",
    "Profitto (€)",
]

ORDERS_HEADERS = [
    "Data", "Order ID", "Funnel", "Tipo (FE/BUMP/OTO)",
    "Prodotto", "Importo (€)", "Status", "Payment Status",
    "Contatto", "Email",
]

PRODUCTS_HEADERS = [
    "Prodotto", "Tipo", "N° Vendite", "Revenue Totale (€)", "% Revenue",
]


def get_gsheets_client() -> gspread.Client:
    if not TOKEN_FILE.exists():
        raise RuntimeError("Token Google Sheets non trovato. Esegui: python tools/gsheets_oauth_setup.py")
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), GSHEETS_SCOPES)
    return gspread.authorize(creds)


def ensure_sheets(gc: gspread.Client) -> tuple[Any, Any, Any]:
    """Assicura che il foglio abbia i 3 tab con le intestazioni giuste."""
    if not SPREADSHEET_ID:
        raise RuntimeError("GSHEETS_SPREADSHEET_ID non configurato nel .env")

    ss = gc.open_by_key(SPREADSHEET_ID)
    existing = {ws.title: ws for ws in ss.worksheets()}

    def get_or_create(name: str, headers: list[str]) -> Any:
        if name not in existing:
            ws = ss.add_worksheet(title=name, rows=1000, cols=len(headers) + 2)
            ws.append_row(headers, value_input_option="USER_ENTERED")
            print(f"  ✓ Creato tab '{name}'")
        else:
            ws = existing[name]
            first_row = ws.row_values(1)
            if not first_row:
                ws.insert_row(headers, 1)
        return ws

    daily_ws = get_or_create("Daily Metrics", DAILY_HEADERS)
    orders_ws = get_or_create("Orders Log", ORDERS_HEADERS)
    products_ws = get_or_create("Prodotti", PRODUCTS_HEADERS)
    return daily_ws, orders_ws, products_ws


def get_existing_dates(ws: Any) -> set[str]:
    """Legge la colonna Data e ritorna le date già presenti."""
    try:
        values = ws.col_values(1)[1:]  # skip header
        return set(v for v in values if v)
    except Exception:
        return set()


def get_existing_order_ids(ws: Any) -> set[str]:
    """Costruisce chiavi composte order_id|product_type|product_name per evitare duplicati."""
    try:
        rows = ws.get_all_values()[1:]  # skip header
        keys = set()
        for r in rows:
            if len(r) >= 5 and r[1]:
                keys.add(f"{r[1]}|{r[3]}|{r[4]}")  # order_id|product_type|product_name
        return keys
    except Exception:
        return set()


# ── Sync principale ──────────────────────────────────────────────────────────

def sync(start_date: str, end_date: str, fb_data: dict[str, dict] | None = None) -> None:
    from tools.ghl_orders_client import get_orders, summarize_by_date
    from tools.fb_ads_client import as_dict_by_date

    print(f"[ads-dashboard] Sync {start_date} → {end_date}")

    # 1. GHL orders
    print("  → Recupero ordini GHL...")
    ghl_rows = get_orders(start_date=start_date, end_date=end_date)
    ghl_summary = summarize_by_date(ghl_rows)
    print(f"     {len(ghl_rows)} righe prodotto | {len(ghl_summary)} giorni")

    # 2. Facebook Ads (da Graph API o da fb_data passato esternamente)
    print("  → Recupero dati Facebook Ads...")
    if fb_data is not None:
        fb_by_date = fb_data
    else:
        fb_by_date = as_dict_by_date(start_date, end_date)
    print(f"     {len(fb_by_date)} giorni FB")

    # 3. Google Sheets
    print("  → Scrittura su Google Sheets...")
    gc = get_gsheets_client()
    daily_ws, orders_ws, products_ws = ensure_sheets(gc)

    existing_dates = get_existing_dates(daily_ws)
    existing_order_ids = get_existing_order_ids(orders_ws)

    # Costruisci date range completo
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)
    dates = [(start_dt + timedelta(days=i)).date().isoformat()
             for i in range((end_dt - start_dt).days + 1)]

    # ── Tab "Daily Metrics" ──
    daily_new_rows = []
    for d in dates:
        if d in existing_dates:
            continue
        fb = fb_by_date.get(d, _empty_fb())
        ghl = ghl_summary.get(d, {})
        fe_rev = ghl.get("fe_revenue", 0)
        bump_rev = ghl.get("bump_revenue", 0)
        oto_rev = ghl.get("oto_revenue", 0)
        total_rev = fe_rev + bump_rev + oto_rev
        total_orders = ghl.get("fe_count", 0) + ghl.get("bump_count", 0) + ghl.get("oto_count", 0)
        spend = fb.get("spend", 0) or 0
        profit = total_rev - spend

        daily_new_rows.append([
            d,
            spend, fb.get("impressions", ""), fb.get("reach", ""),
            fb.get("clicks", ""), fb.get("ctr", ""), fb.get("cpm", ""), fb.get("cpc", ""),
            fb.get("fb_purchases", ""), fb.get("fb_purchase_value", ""), fb.get("roas", ""),
            ghl.get("fe_count", 0), round(fe_rev, 2),
            ghl.get("bump_count", 0), round(bump_rev, 2),
            ghl.get("oto_count", 0), round(oto_rev, 2),
            total_orders, round(total_rev, 2),
            round(profit, 2),
        ])

    if daily_new_rows:
        daily_ws.append_rows(daily_new_rows, value_input_option="USER_ENTERED")
        print(f"     ✓ {len(daily_new_rows)} nuove righe in 'Daily Metrics'")
    else:
        print("     ✓ 'Daily Metrics' già aggiornato")

    # ── Tab "Orders Log" ── (una riga per item, chiave = order_id + product_type)
    orders_new_rows = []
    for r in ghl_rows:
        item_key = f"{r['order_id']}|{r['product_type']}|{r['product_name']}"
        if item_key in existing_order_ids:
            continue
        orders_new_rows.append([
            r["date"], r["order_id"], r["funnel_name"], r["product_type"],
            r["product_name"], round(float(r["amount"] or 0), 2),
            r["status"], r["payment_status"],
            r["contact_name"], r["contact_email"],
        ])
        existing_order_ids.add(item_key)

    if orders_new_rows:
        orders_ws.append_rows(orders_new_rows, value_input_option="USER_ENTERED")
        print(f"     ✓ {len(orders_new_rows)} nuove righe in 'Orders Log'")
    else:
        print("     ✓ 'Orders Log' già aggiornato")

    # ── Tab "Prodotti" (riscrive tutto) ──
    product_stats: dict[str, dict] = {}
    all_ghl = get_orders()  # tutti i dati storici per avere il quadro completo
    for r in all_ghl:
        key = r["product_name"]
        if key not in product_stats:
            product_stats[key] = {"type": r["product_type"], "count": 0, "revenue": 0.0}
        product_stats[key]["count"] += 1
        product_stats[key]["revenue"] += float(r["amount"] or 0)

    total_all_rev = sum(v["revenue"] for v in product_stats.values()) or 1
    products_rows = [PRODUCTS_HEADERS]
    for name, s in sorted(product_stats.items(), key=lambda x: -x[1]["revenue"]):
        pct = round(s["revenue"] / total_all_rev * 100, 1)
        products_rows.append([name, s["type"], s["count"], round(s["revenue"], 2), pct])

    products_ws.clear()
    products_ws.update(products_rows, value_input_option="USER_ENTERED")
    print(f"     ✓ 'Prodotti' aggiornato ({len(products_rows) - 1} prodotti)")

    print(f"\n✅ Sync completato — apri il foglio:")
    print(f"   https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "days"
    today = datetime.now(timezone.utc).date().isoformat()

    if cmd == "today":
        sync(today, today)
    elif cmd == "days":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        start = (datetime.now(timezone.utc).date() - timedelta(days=n - 1)).isoformat()
        sync(start, today)
    elif cmd == "date":
        d = sys.argv[2] if len(sys.argv) > 2 else today
        sync(d, d)
    elif cmd == "range":
        sync(sys.argv[2], sys.argv[3])
    else:
        print("Usage: python tools/ads_dashboard_sync.py [today|days N|date YYYY-MM-DD|range START END]")
        sys.exit(1)
