#!/usr/bin/env python3
"""Creative Fatigue Detector — rileva annunci Meta in calo per fatica creativa.

Dall'update Andromeda (2025) un concept creativo esaurisce il pubblico
indirizzabile in 2-3 settimane invece delle 6+ pre-Andromeda, perché
l'algoritmo scala aggressivamente i vincitori e si affida sempre più alla
creatività (meno targeting dettagliato disponibile). Segnali di fatica:
CTR in calo settimana su settimana, frequency in salita, età annuncio
oltre 14-21 giorni.

Variabili .env richieste:
  FB_ACCESS_TOKEN, FB_AD_ACCOUNT_ID  (stesse di tools/fb_ads_client.py)

Usage:
    python tools/creative_fatigue_detector.py            # ultimi 28gg, solo ACTIVE
    python tools/creative_fatigue_detector.py --days 35
    python tools/creative_fatigue_detector.py --all       # include anche PAUSED
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

TOKEN = os.environ.get("FB_ACCESS_TOKEN", "")
RAW_ID = os.environ.get("FB_AD_ACCOUNT_ID", "").strip()
ACCOUNT_ID = f"act_{RAW_ID}" if RAW_ID and not RAW_ID.startswith("act_") else RAW_ID
API_VER = "v21.0"
BASE = f"https://graph.facebook.com/{API_VER}"

# Soglie basate sui benchmark Andromeda 2026 (creative fatigue post-update):
# un concept ora brucia il pubblico in 2-3 settimane invece delle 6+ pre-Andromeda.
AGE_WATCH_DAYS = 14        # da qui in poi tenere d'occhio il concept
AGE_URGENT_DAYS = 21       # da qui in poi il concept ha probabilmente esaurito il pubblico
CTR_DECLINE_WATCH = 0.10   # -10% CTR settimana su settimana
CTR_DECLINE_URGENT = 0.20  # -20% CTR settimana su settimana
FREQ_RISE_WATCH = 0.15     # +15% frequency settimana su settimana
MIN_IMPRESSIONS = 500      # sotto questa soglia il dato non è statisticamente significativo


def _paginate(path: str, **params) -> list[dict]:
    rows: list[dict] = []
    url = f"{BASE}/{path}"
    while url:
        r = requests.get(url, params={"access_token": TOKEN, **params}, timeout=30)
        if not r.ok:
            raise RuntimeError(f"GET {url} → {r.status_code}: {r.text[:300]}")
        data = r.json()
        rows.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}
    return rows


def fetch_ads(include_all: bool) -> dict[str, dict]:
    """Ritorna {ad_id: {name, adset_name, campaign_name, created_time, status}}."""
    statuses = ["ACTIVE", "PAUSED"] if include_all else ["ACTIVE"]
    rows = _paginate(
        f"{ACCOUNT_ID}/ads",
        fields="id,name,adset{name},campaign{name},created_time,effective_status",
        effective_status=json.dumps(statuses),
        limit=200,
    )
    ads = {}
    for r in rows:
        ads[r["id"]] = {
            "name": r.get("name", ""),
            "adset_name": (r.get("adset") or {}).get("name", ""),
            "campaign_name": (r.get("campaign") or {}).get("name", ""),
            "created_time": r.get("created_time", ""),
            "status": r.get("effective_status", ""),
        }
    return ads


def fetch_weekly_insights(days: int) -> dict[str, list[dict]]:
    """Ritorna {ad_id: [bucket settimanale...]} con impressions/clicks/ctr/frequency/spend."""
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days - 1)
    rows = _paginate(
        f"{ACCOUNT_ID}/insights",
        level="ad",
        fields="ad_id,impressions,clicks,ctr,frequency,spend,date_start,date_stop",
        time_range=json.dumps({"since": start.isoformat(), "until": end.isoformat()}),
        time_increment="7",
        limit=500,
    )
    by_ad: dict[str, list[dict]] = {}
    for r in rows:
        by_ad.setdefault(r["ad_id"], []).append({
            "date_start": r.get("date_start", ""),
            "impressions": int(r.get("impressions", 0)),
            "clicks": int(r.get("clicks", 0)),
            "ctr": float(r.get("ctr", 0)),
            "frequency": float(r.get("frequency", 0)),
            "spend": float(r.get("spend", 0)),
        })
    for buckets in by_ad.values():
        buckets.sort(key=lambda b: b["date_start"])
    return by_ad


def _pct_change(old: float, new: float) -> float | None:
    if not old:
        return None
    return (new - old) / old


def analyze(ads: dict[str, dict], weekly: dict[str, list[dict]]) -> list[dict]:
    today = datetime.now(timezone.utc).date()
    results = []
    for ad_id, meta in ads.items():
        buckets = weekly.get(ad_id, [])
        if not buckets:
            continue
        total_impr = sum(b["impressions"] for b in buckets)
        if total_impr < MIN_IMPRESSIONS:
            continue

        age_days = None
        created = meta.get("created_time", "")
        if created:
            try:
                created_date = datetime.fromisoformat(created.replace("Z", "+00:00")).date()
                age_days = (today - created_date).days
            except ValueError:
                pass

        last = buckets[-1]
        prev = buckets[-2] if len(buckets) >= 2 else None
        ctr_change = _pct_change(prev["ctr"], last["ctr"]) if prev else None
        freq_change = _pct_change(prev["frequency"], last["frequency"]) if prev else None

        signals: list[str] = []
        severity = "OK"

        def _bump(level: str) -> None:
            nonlocal severity
            if level == "URGENTE" or severity == "OK":
                severity = level

        if age_days is not None and age_days >= AGE_URGENT_DAYS:
            signals.append(f"età {age_days}gg ≥ {AGE_URGENT_DAYS}gg")
            _bump("URGENTE")
        elif age_days is not None and age_days >= AGE_WATCH_DAYS:
            signals.append(f"età {age_days}gg ≥ {AGE_WATCH_DAYS}gg")
            _bump("WATCH")

        if ctr_change is not None and ctr_change <= -CTR_DECLINE_URGENT:
            signals.append(f"CTR {ctr_change:+.0%} sett/sett")
            _bump("URGENTE")
        elif ctr_change is not None and ctr_change <= -CTR_DECLINE_WATCH:
            signals.append(f"CTR {ctr_change:+.0%} sett/sett")
            _bump("WATCH")

        if freq_change is not None and freq_change >= FREQ_RISE_WATCH:
            signals.append(f"frequency {freq_change:+.0%} sett/sett")
            _bump("WATCH")

        if severity == "URGENTE":
            action = "Refresh o pausa: sostituisci il concept, non solo la variante"
        elif severity == "WATCH":
            action = "Prepara una variante di ricambio, monitora la prossima settimana"
        else:
            action = "Nessuna azione"

        results.append({
            "ad_id": ad_id,
            "name": meta["name"],
            "adset": meta["adset_name"],
            "campaign": meta["campaign_name"],
            "status": meta["status"],
            "age_days": age_days,
            "ctr_last": last["ctr"],
            "ctr_change": ctr_change,
            "frequency_last": last["frequency"],
            "freq_change": freq_change,
            "impressions_period": total_impr,
            "severity": severity,
            "signals": signals,
            "action": action,
        })

    order = {"URGENTE": 0, "WATCH": 1, "OK": 2}
    results.sort(key=lambda r: (order[r["severity"]], -r["impressions_period"]))
    return results


def print_report(results: list[dict], days: int) -> None:
    print(f"\n[creative-fatigue] Analisi {days}gg — {len(results)} annunci con dati sufficienti\n")
    if not results:
        print("Nessun annuncio con abbastanza impressioni nel periodo (soglia: "
              f"{MIN_IMPRESSIONS}).")
        return

    icons = {"URGENTE": "🔴", "WATCH": "🟡", "OK": "🟢"}
    for r in results:
        icon = icons[r["severity"]]
        age_str = f"{r['age_days']}gg" if r["age_days"] is not None else "n/d"
        ctr_str = f"{r['ctr_last']:.2f}%"
        if r["ctr_change"] is not None:
            ctr_str += f" ({r['ctr_change']:+.0%} vs sett. prec.)"
        freq_str = f"{r['frequency_last']:.2f}"
        if r["freq_change"] is not None:
            freq_str += f" ({r['freq_change']:+.0%})"
        print(f"{icon} {r['severity']:<8} {r['name']}  [{r['campaign']} / {r['adset']}]")
        print(f"    Età: {age_str} | CTR: {ctr_str} | Frequency: {freq_str} | "
              f"Impr. periodo: {r['impressions_period']:,}")
        if r["signals"]:
            print(f"    Segnali: {', '.join(r['signals'])}")
        print(f"    Azione: {r['action']}\n")

    urgent = sum(1 for r in results if r["severity"] == "URGENTE")
    watch = sum(1 for r in results if r["severity"] == "WATCH")
    ok = len(results) - urgent - watch
    print(f"Riepilogo: {urgent} urgenti | {watch} da monitorare | {ok} OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rileva creative fatigue sugli annunci Meta")
    parser.add_argument("--days", type=int, default=28, help="Finestra di analisi in giorni (default 28)")
    parser.add_argument("--all", action="store_true", help="Includi anche annunci PAUSED")
    args = parser.parse_args()

    if not TOKEN or not ACCOUNT_ID:
        print("❌ FB_ACCESS_TOKEN o FB_AD_ACCOUNT_ID non configurati nel .env")
        sys.exit(1)

    print(f"[creative-fatigue] Recupero annunci ({'tutti' if args.all else 'solo ACTIVE'})...")
    ads = fetch_ads(include_all=args.all)
    print(f"    {len(ads)} annunci trovati")

    print(f"[creative-fatigue] Recupero insight settimanali ultimi {args.days}gg...")
    weekly = fetch_weekly_insights(args.days)

    results = analyze(ads, weekly)
    print_report(results, args.days)


if __name__ == "__main__":
    main()
