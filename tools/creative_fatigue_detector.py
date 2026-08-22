#!/usr/bin/env python3
"""
Rilevatore di affaticamento creativo per le ads Facebook.

Confronta le performance degli ultimi 3 giorni vs i 4 giorni precedenti
per ogni ad e identifica segnali di fatigue:
  - Frequenza alta (> 2.0)
  - CTR in calo
  - CPM in aumento
  - CPL in peggioramento
  - Impressioni in calo con spesa stabile (reach esaurita)

CLI:
  python tools/creative_fatigue_detector.py
  python tools/creative_fatigue_detector.py --days-recent 3 --days-baseline 7
  python tools/creative_fatigue_detector.py --threshold-freq 1.8
"""
from __future__ import annotations

import os
import sys
import json
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path.home() / ".secrets" / "mailift" / ".env")
load_dotenv(ROOT / ".env")

TOKEN  = os.environ.get("FB_ACCESS_TOKEN", "")
ACCOUNT = os.environ.get("FB_AD_ACCOUNT_ID", "")
BASE   = "https://graph.facebook.com/v21.0"

# Soglie di fatigue
FREQ_WARNING   = 1.8   # frequenza oltre la quale inizia il rischio
FREQ_CRITICAL  = 2.5   # frequenza critica
CTR_DROP_PCT   = 20.0  # calo CTR % che segnala fatigue
CPM_RISE_PCT   = 25.0  # aumento CPM % che segnala audience esaurita
CPL_RISE_PCT   = 30.0  # peggioramento CPL %
MIN_SPEND      = 8.0   # spesa minima per considerare un ad (evita rumore)


# ── helpers ──────────────────────────────────────────────────────────────────

def _get(url: str, params: dict) -> dict:
    params["access_token"] = TOKEN
    r = requests.get(url, params=params)
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"FB API: {data['error']['message']}")
    return data


def _paginate(url: str, params: dict) -> list[dict]:
    results, data = [], _get(url, params)
    results.extend(data.get("data", []))
    while data.get("paging", {}).get("next"):
        data = requests.get(data["paging"]["next"]).json()
        results.extend(data.get("data", []))
    return results


def leads_from(ad: dict) -> int:
    return next((int(a["value"]) for a in ad.get("actions", [])
                 if a["action_type"] == "lead"), 0)


def cpl_from(ad: dict) -> float | None:
    return next((float(c["value"]) for c in ad.get("cost_per_action_type", [])
                 if c["action_type"] == "lead"), None)


def fetch_period(since: str, until: str) -> dict[str, dict]:
    """Ritorna dict {ad_id: metrics} per il periodo."""
    rows = _paginate(f"{BASE}/{ACCOUNT}/insights", {
        "level": "ad",
        "time_range": json.dumps({"since": since, "until": until}),
        "fields": "ad_id,ad_name,adset_name,campaign_name,spend,impressions,reach,frequency,clicks,ctr,cpm,actions,cost_per_action_type",
        "limit": 200,
    })
    result = {}
    for r in rows:
        result[r["ad_id"]] = {
            "ad_name":      r.get("ad_name", "?"),
            "adset_name":   r.get("adset_name", "?"),
            "campaign_name": r.get("campaign_name", "?"),
            "spend":        float(r.get("spend", 0)),
            "impressions":  int(r.get("impressions", 0)),
            "reach":        int(r.get("reach", 0)),
            "frequency":    float(r.get("frequency", 0)),
            "clicks":       int(r.get("clicks", 0)),
            "ctr":          float(r.get("ctr", 0)),
            "cpm":          float(r.get("cpm", 0)),
            "leads":        leads_from(r),
            "cpl":          cpl_from(r),
        }
    return result


def pct_change(new: float, old: float) -> float | None:
    if old == 0:
        return None
    return round((new - old) / old * 100, 1)


def fatigue_score(recent: dict, baseline: dict) -> list[str]:
    """Ritorna lista di segnali di fatigue per un ad."""
    signals = []

    # 1. Frequenza alta
    if recent["frequency"] >= FREQ_CRITICAL:
        signals.append(f"⛔ Frequenza critica {recent['frequency']:.1f} (soglia {FREQ_CRITICAL})")
    elif recent["frequency"] >= FREQ_WARNING:
        signals.append(f"⚠️  Frequenza alta {recent['frequency']:.1f} (soglia {FREQ_WARNING})")

    # 2. CTR in calo
    ctr_chg = pct_change(recent["ctr"], baseline["ctr"])
    if ctr_chg is not None and ctr_chg <= -CTR_DROP_PCT:
        signals.append(f"⚠️  CTR calato {abs(ctr_chg):.0f}%: {baseline['ctr']:.2f}% → {recent['ctr']:.2f}%")

    # 3. CPM in aumento (audience esaurita, Meta paga di più per raggiungerla)
    cpm_chg = pct_change(recent["cpm"], baseline["cpm"])
    if cpm_chg is not None and cpm_chg >= CPM_RISE_PCT:
        signals.append(f"⚠️  CPM aumentato +{cpm_chg:.0f}%: €{baseline['cpm']:.1f} → €{recent['cpm']:.1f}")

    # 4. CPL in peggioramento
    if recent["cpl"] and baseline["cpl"]:
        cpl_chg = pct_change(recent["cpl"], baseline["cpl"])
        if cpl_chg is not None and cpl_chg >= CPL_RISE_PCT:
            signals.append(f"⚠️  CPL peggiorato +{cpl_chg:.0f}%: €{baseline['cpl']:.0f} → €{recent['cpl']:.0f}")

    # 5. Impressioni in calo con spesa stabile (reach esaurita)
    impr_chg = pct_change(recent["impressions"], baseline["impressions"])
    spend_chg = pct_change(recent["spend"], baseline["spend"])
    if (impr_chg is not None and spend_chg is not None
            and impr_chg <= -20 and spend_chg >= -10):
        signals.append(f"⚠️  Reach in calo: impressioni -{abs(impr_chg):.0f}% con spesa stabile")

    return signals


def recommend(signals: list[str], recent: dict) -> str:
    if not signals:
        return "✅ Nessun segnale di fatigue"
    critical = [s for s in signals if "⛔" in s]
    if critical or len(signals) >= 3:
        return "⛔ REFRESH URGENTE — sostituisci la creative"
    if recent["leads"] == 0 and recent["spend"] > 20:
        return "⛔ PAUSA — spesa senza lead"
    return "⚠️  MONITORA — valuta refresh entro 3 giorni"


# ── main report ──────────────────────────────────────────────────────────────

def build_fatigue_report(days_recent: int = 3, days_baseline: int = 4) -> str:
    today      = date.today()
    r_end      = today - timedelta(days=1)
    r_start    = r_end - timedelta(days=days_recent - 1)
    b_end      = r_start - timedelta(days=1)
    b_start    = b_end - timedelta(days=days_baseline - 1)

    recent_str   = f"{r_start.strftime('%d/%m')} → {r_end.strftime('%d/%m')}"
    baseline_str = f"{b_start.strftime('%d/%m')} → {b_end.strftime('%d/%m')}"

    print(f"Fetching periodo recente   {recent_str}...")
    recent_data   = fetch_period(r_start.isoformat(), r_end.isoformat())
    print(f"Fetching periodo baseline  {baseline_str}...")
    baseline_data = fetch_period(b_start.isoformat(), b_end.isoformat())

    lines = [
        "=" * 55,
        f"  CREATIVE FATIGUE DETECTOR — {today.strftime('%d/%m/%Y')}",
        f"  Recente:  {recent_str}  ({days_recent}gg)",
        f"  Baseline: {baseline_str} ({days_baseline}gg)",
        "=" * 55,
        "",
    ]

    # Solo ad presenti in entrambi i periodi e con spesa sufficiente
    common_ids = set(recent_data) & set(baseline_data)
    recent_only = {k: v for k, v in recent_data.items()
                   if k not in baseline_data and v["spend"] >= MIN_SPEND}

    results = []
    for ad_id in common_ids:
        rec = recent_data[ad_id]
        bas = baseline_data[ad_id]
        if rec["spend"] < MIN_SPEND and bas["spend"] < MIN_SPEND:
            continue
        signals = fatigue_score(rec, bas)
        rec_str = recommend(signals, rec)
        results.append((len(signals), ad_id, rec, bas, signals, rec_str))

    # Ordina per severità (più segnali = più urgente)
    results.sort(key=lambda x: x[0], reverse=True)

    urgent, warning, ok = [], [], []
    for severity, ad_id, rec, bas, signals, rec_str in results:
        block = [
            f"[{rec['adset_name'][:25]}] {rec['ad_name']}",
            f"  Campagna: {rec['campaign_name'][:45]}",
            f"  Recente:  spend €{rec['spend']:.0f} | freq {rec['frequency']:.1f} | CTR {rec['ctr']:.2f}% | CPM €{rec['cpm']:.1f} | lead {rec['leads']}" + (f" | CPL €{rec['cpl']:.0f}" if rec['cpl'] else ""),
            f"  Baseline: spend €{bas['spend']:.0f} | freq {bas['frequency']:.1f} | CTR {bas['ctr']:.2f}% | CPM €{bas['cpm']:.1f} | lead {bas['leads']}" + (f" | CPL €{bas['cpl']:.0f}" if bas['cpl'] else ""),
        ]
        for s in signals:
            block.append(f"  {s}")
        block.append(f"  → {rec_str}")
        block.append("")

        if "⛔" in rec_str:
            urgent.append(block)
        elif "⚠️" in rec_str:
            warning.append(block)
        else:
            ok.append(block)

    if urgent:
        lines.append(f"⛔ AZIONE URGENTE ({len(urgent)} ad)")
        lines.append("-" * 55)
        for b in urgent:
            lines.extend(b)

    if warning:
        lines.append(f"⚠️  DA MONITORARE ({len(warning)} ad)")
        lines.append("-" * 55)
        for b in warning:
            lines.extend(b)

    if ok:
        lines.append(f"✅ NESSUN SEGNALE ({len(ok)} ad)")
        lines.append("-" * 55)
        for b in ok:
            lines.extend(b)

    # Ad solo nel periodo recente (nuovi, nessun baseline)
    if recent_only:
        lines.append(f"🆕 AD NUOVI — ancora in fase di apprendimento ({len(recent_only)})")
        lines.append("-" * 55)
        for rec in recent_only.values():
            lines.append(f"  {rec['ad_name']} — €{rec['spend']:.0f} | freq {rec['frequency']:.1f} | CTR {rec['ctr']:.2f}% | lead {rec['leads']}")
        lines.append("")

    lines += [
        "=" * 55,
        f"  Totale ad analizzati: {len(results)} | Urgenti: {len(urgent)} | Warning: {len(warning)} | OK: {len(ok)}",
        "=" * 55,
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    days_recent   = int(next((sys.argv[i+1] for i, a in enumerate(sys.argv) if a == "--days-recent"),   3))
    days_baseline = int(next((sys.argv[i+1] for i, a in enumerate(sys.argv) if a == "--days-baseline"), 4))

    thresh_freq = next((sys.argv[i+1] for i, a in enumerate(sys.argv) if a == "--threshold-freq"), None)
    if thresh_freq:
        FREQ_WARNING = float(thresh_freq)

    report = build_fatigue_report(days_recent, days_baseline)
    print(report)
