#!/usr/bin/env python3
"""GHL Orders client — recupera e classifica ordini digitali per la dashboard.

Ogni ordine viene classificato in:
- FRONT END: sourceSubType = one_step_order_form, bumpProduct = False
- BUMP:      sourceSubType = one_step_order_form, bumpProduct = True
- OTO:       sourceSubType = upsell

Variabili .env richieste:
- GHL_API_KEY
- GHL_LOCATION_ID

Funzioni esposte:
- get_orders(start_date, end_date)  → list[OrderRow]
- get_orders_today()                → list[OrderRow]
- get_orders_range(days)            → list[OrderRow] (ultimi N giorni)

OrderRow è un dict con:
    order_id, date, funnel_name, product_type (FE/BUMP/OTO),
    product_name, amount, status, contact_name, contact_email

CLI:
    python tools/ghl_orders_client.py today
    python tools/ghl_orders_client.py days 7
    python tools/ghl_orders_client.py date 2026-06-17
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

BASE_URL = "https://services.leadconnectorhq.com"
API_VERSION = "2021-07-28"
API_KEY = os.environ.get("GHL_API_KEY")
LOCATION_ID = os.environ.get("GHL_LOCATION_ID")

PRODUCT_TYPE_MAP = {
    "upsell": "OTO",
    "one_step_order_form": None,  # dipende da bumpProduct
    "downsell": "DOWNSELL",
}


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Version": API_VERSION,
        "Accept": "application/json",
    }


def _fetch_orders_all() -> list[dict]:
    """Recupera tutti gli ordini (GHL date filter non affidabile, filtriamo client-side)."""
    all_orders = []
    offset = 0
    limit = 100
    while True:
        params = {"altId": LOCATION_ID, "altType": "location", "limit": limit, "offset": offset}
        resp = requests.get(f"{BASE_URL}/payments/orders", headers=_headers(), params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("data", [])
        all_orders.extend(batch)
        total = data.get("totalCount", 0)
        offset += limit
        if offset >= total or not batch:
            break
    return all_orders


def _fetch_order_detail(order_id: str) -> dict:
    resp = requests.get(
        f"{BASE_URL}/payments/orders/{order_id}",
        headers=_headers(),
        params={"altId": LOCATION_ID, "altType": "location"},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def _classify_item(order: dict, item: dict) -> str:
    sub = order.get("sourceSubType", "")
    if sub == "upsell":
        return "OTO"
    if sub == "one_step_order_form":
        return "BUMP" if item.get("bumpProduct") else "FE"
    return sub.upper() if sub else "FE"


TEST_EMAILS = {"lorenzo.baretta997@gmail.com"}


def _parse_orders(raw_orders: list[dict]) -> list[dict]:
    rows = []
    for o in raw_orders:
        # Solo ordini pagati da clienti reali
        if o.get("paymentStatus") != "paid":
            continue
        if o.get("contactEmail", "").lower() in TEST_EMAILS:
            continue
        detail = _fetch_order_detail(o["_id"])
        items = detail.get("items", [])
        created_raw = o.get("createdAt", "")
        date_str = created_raw[:10] if created_raw else ""
        for item in items:
            product_type = _classify_item(o, item)
            rows.append({
                "order_id": o["_id"],
                "date": date_str,
                "funnel_name": o.get("sourceName", ""),
                "product_type": product_type,
                "product_name": item.get("name", ""),
                "amount": item.get("price", {}).get("amount", 0),
                "status": o.get("status", ""),
                "payment_status": o.get("paymentStatus", ""),
                "contact_name": o.get("contactName", ""),
                "contact_email": o.get("contactEmail", ""),
            })
    return rows


def get_orders(start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    """Recupera ordini nel range ISO date (YYYY-MM-DD). Filtro client-side."""
    raw = _fetch_orders_all()
    if start_date or end_date:
        def in_range(o: dict) -> bool:
            d = o.get("createdAt", "")[:10]
            if start_date and d < start_date:
                return False
            if end_date and d > end_date:
                return False
            return True
        raw = [o for o in raw if in_range(o)]
    return _parse_orders(raw)


def get_orders_today() -> list[dict]:
    today = datetime.now(timezone.utc).date().isoformat()
    return get_orders(start_date=today, end_date=today)


def get_orders_range(days: int = 30) -> list[dict]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days - 1)
    return get_orders(start_date=start.isoformat(), end_date=end.isoformat())


def summarize_by_date(rows: list[dict]) -> dict[str, dict]:
    """Aggrega righe per data → {date: {fe_count, fe_rev, bump_count, bump_rev, oto_count, oto_rev}}"""
    summary: dict[str, dict] = {}
    for r in rows:
        d = r["date"]
        if d not in summary:
            summary[d] = {
                "fe_count": 0, "fe_revenue": 0.0,
                "bump_count": 0, "bump_revenue": 0.0,
                "oto_count": 0, "oto_revenue": 0.0,
            }
        t = r["product_type"]
        amt = float(r["amount"] or 0)
        if t == "FE":
            summary[d]["fe_count"] += 1
            summary[d]["fe_revenue"] += amt
        elif t == "BUMP":
            summary[d]["bump_count"] += 1
            summary[d]["bump_revenue"] += amt
        elif t == "OTO":
            summary[d]["oto_count"] += 1
            summary[d]["oto_revenue"] += amt
    return summary


if __name__ == "__main__":
    import json
    cmd = sys.argv[1] if len(sys.argv) > 1 else "today"

    if cmd == "today":
        rows = get_orders_today()
    elif cmd == "days" and len(sys.argv) > 2:
        rows = get_orders_range(int(sys.argv[2]))
    elif cmd == "date" and len(sys.argv) > 2:
        d = sys.argv[2]
        rows = get_orders(start_date=d, end_date=d)
    else:
        print("Usage: python tools/ghl_orders_client.py [today|days N|date YYYY-MM-DD]")
        sys.exit(1)

    if not rows:
        print("Nessun ordine trovato.")
    else:
        print(f"{'Data':<12} {'Tipo':<6} {'Prodotto':<40} {'€':>8} {'Status':<12} {'Contatto'}")
        print("-" * 100)
        for r in rows:
            print(f"{r['date']:<12} {r['product_type']:<6} {r['product_name'][:38]:<40} {r['amount']:>8.2f} {r['status']:<12} {r['contact_name']}")

        summary = summarize_by_date(rows)
        print("\n=== RIEPILOGO PER GIORNO ===")
        for d, s in sorted(summary.items()):
            total_rev = s['fe_revenue'] + s['bump_revenue'] + s['oto_revenue']
            total_cnt = s['fe_count'] + s['bump_count'] + s['oto_count']
            print(f"{d} | FE: {s['fe_count']}x €{s['fe_revenue']:.2f} | BUMP: {s['bump_count']}x €{s['bump_revenue']:.2f} | OTO: {s['oto_count']}x €{s['oto_revenue']:.2f} | TOT: {total_cnt}x €{total_rev:.2f}")
