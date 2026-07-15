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
    python tools/creative_fatigue_detector.py --no-html   # solo report da terminale

Di default scrive anche un report HTML navigabile in `.tmp/creative_fatigue_report.html`
(passa `--html PATH` per un percorso diverso, `--no-html` per saltarlo).
"""

from __future__ import annotations

import argparse
import csv
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


def _classify(age_days: int | None, ctr_change: float | None, freq_change: float | None) -> tuple[str, list[str], str]:
    """Applica le soglie di fatica e ritorna (severity, signals, action)."""
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
        signals.append(f"CTR {ctr_change:+.0%} vs periodo precedente")
        _bump("URGENTE")
    elif ctr_change is not None and ctr_change <= -CTR_DECLINE_WATCH:
        signals.append(f"CTR {ctr_change:+.0%} vs periodo precedente")
        _bump("WATCH")

    if freq_change is not None and freq_change >= FREQ_RISE_WATCH:
        signals.append(f"frequency {freq_change:+.0%} vs periodo precedente")
        _bump("WATCH")

    if severity == "URGENTE":
        action = "Refresh o pausa: sostituisci il concept, non solo la variante"
    elif severity == "WATCH":
        action = "Prepara una variante di ricambio, monitora la prossima settimana"
    else:
        action = "Nessuna azione"
    return severity, signals, action


def analyze(ads: dict[str, dict], weekly: dict[str, list[dict]], min_impressions: int = MIN_IMPRESSIONS) -> list[dict]:
    today = datetime.now(timezone.utc).date()
    results = []
    for ad_id, meta in ads.items():
        buckets = weekly.get(ad_id, [])
        if not buckets:
            continue
        total_impr = sum(b["impressions"] for b in buckets)
        if total_impr < min_impressions:
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

        severity, signals, action = _classify(age_days, ctr_change, freq_change)

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


# ── Modalità CSV (export manuale da Meta Ads Manager, nessun token richiesto) ──

def _csv_float(v: str | None) -> float:
    try:
        return float(v) if v else 0.0
    except ValueError:
        return 0.0


def parse_meta_csv(path: Path) -> dict[str, list[dict]]:
    """Legge un export CSV di Ads Manager (breakdown giornaliero per annuncio).

    Colonne attese (export standard "per giorno" a livello annuncio):
    Reporting starts, Ad name, Ad delivery, Reach, Frequency,
    Amount spent (EUR), Impressions, CTR (all).
    """
    by_ad: dict[str, list[dict]] = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = (row.get("Ad name") or "").strip()
            if not name:
                continue
            by_ad.setdefault(name, []).append({
                "date": row.get("Reporting starts", ""),
                "delivery": (row.get("Ad delivery") or "").strip().lower(),
                "impressions": int(_csv_float(row.get("Impressions"))),
                "reach": int(_csv_float(row.get("Reach"))),
                "frequency": _csv_float(row.get("Frequency")),
                "ctr": _csv_float(row.get("CTR (all)")),
                "spend": _csv_float(row.get("Amount spent (EUR)")),
            })
    for rows in by_ad.values():
        rows.sort(key=lambda r: r["date"])
    return by_ad


def analyze_csv(path: Path, min_impressions: int, include_inactive: bool, exclude_today: bool = True) -> list[dict]:
    """Analizza un export CSV Ads Manager con la stessa logica di `analyze()`.

    Senza `created_time` (non presente in questo export) l'età non è
    calcolabile: la severità si basa solo su trend CTR/frequency, confrontando
    la prima metà vs la seconda metà dei giorni con delivery reale nel file.

    Per default esclude la giornata odierna (`exclude_today`): un giorno
    ancora in corso ha metriche parziali e falsa il confronto di trend.
    """
    by_ad = parse_meta_csv(path)
    today_str = datetime.now(timezone.utc).date().isoformat()
    results = []

    for name, rows in by_ad.items():
        latest_status = rows[-1]["delivery"] if rows else ""
        if not include_inactive and latest_status != "active":
            continue

        active_days = [r for r in rows if r["impressions"] > 0]
        today_excluded = exclude_today and any(r["date"] == today_str for r in active_days)
        if exclude_today:
            active_days = [r for r in active_days if r["date"] != today_str]
        total_impr = sum(r["impressions"] for r in active_days)
        if total_impr < min_impressions or len(active_days) < 2:
            continue

        mid = max(1, len(active_days) // 2)
        first_half = active_days[:mid]
        second_half = active_days[mid:] or active_days[-1:]

        def _wavg(subset: list[dict], key: str) -> float:
            impr_sum = sum(r["impressions"] for r in subset) or 1
            return sum(r[key] * r["impressions"] for r in subset) / impr_sum

        ctr_before, ctr_after = _wavg(first_half, "ctr"), _wavg(second_half, "ctr")
        freq_before, freq_after = _wavg(first_half, "frequency"), _wavg(second_half, "frequency")
        ctr_change = _pct_change(ctr_before, ctr_after)
        freq_change = _pct_change(freq_before, freq_after)

        severity, signals, action = _classify(None, ctr_change, freq_change)
        signals = signals + [f"{len(active_days)} giorni con delivery reale nel file"]
        if today_excluded:
            signals.append("giorno odierno escluso (dati parziali)")

        results.append({
            "ad_id": name,
            "name": name,
            "adset": "—",
            "campaign": "—",
            "status": latest_status.upper() or "N/D",
            "age_days": None,
            "ctr_last": ctr_after,
            "ctr_change": ctr_change,
            "frequency_last": freq_after,
            "freq_change": freq_change,
            "impressions_period": total_impr,
            "severity": severity,
            "signals": signals,
            "action": action,
        })

    order = {"URGENTE": 0, "WATCH": 1, "OK": 2}
    results.sort(key=lambda r: (order[r["severity"]], -r["impressions_period"]))
    return results


def print_report(results: list[dict], period_label: str) -> None:
    print(f"\n[creative-fatigue] Analisi {period_label} — {len(results)} annunci con dati sufficienti\n")
    if not results:
        print("Nessun annuncio con abbastanza impressioni nel periodo.")
        return

    icons = {"URGENTE": "🔴", "WATCH": "🟡", "OK": "🟢"}
    for r in results:
        icon = icons[r["severity"]]
        age_str = f"{r['age_days']}gg" if r["age_days"] is not None else "n/d"
        ctr_str = f"{r['ctr_last']:.2f}%"
        if r["ctr_change"] is not None:
            ctr_str += f" ({r['ctr_change']:+.0%} vs periodo prec.)"
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


_SEVERITY_CSS = {"URGENTE": "critical", "WATCH": "warning", "OK": "good"}
_SEVERITY_LABEL = {"URGENTE": "Urgente", "WATCH": "Watch", "OK": "OK"}
_SEVERITY_ICON = {"URGENTE": "🔴", "WATCH": "🟡", "OK": "🟢"}

_HTML_TEMPLATE = """<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>Creative Fatigue — Mailift Meta Ads</title>
<style>
  :root {{
    --surface-1: #fcfcfb; --page-plane: #f9f9f7; --text-primary: #0b0b0b;
    --text-secondary: #52514e; --text-muted: #898781; --gridline: #e1e0d9;
    --border: rgba(11,11,11,0.10); --good: #0ca30c; --warning: #fab219;
    --critical: #d03b3b; --good-bg: #e7f6e7; --warning-bg: #fff6e0;
    --critical-bg: #fbe9e9; --accent: #2a78d6;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --surface-1: #232322; --page-plane: #0d0d0d; --text-primary: #ffffff;
      --text-secondary: #c3c2b7; --gridline: #2c2c2a; --border: rgba(255,255,255,0.10);
      --good-bg: #10240f; --warning-bg: #2b2210; --critical-bg: #2c1414; --accent: #3987e5;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--page-plane); color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif; padding: 32px 20px 64px; }}
  .wrap {{ max-width: 980px; margin: 0 auto; }}
  .eyebrow {{ font-size: 12px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
    color: var(--accent); margin: 0 0 6px; }}
  h1 {{ font-size: 22px; font-weight: 700; margin: 0 0 6px; }}
  .sub {{ color: var(--text-secondary); font-size: 14px; margin: 0 0 20px; }}
  .stat-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 28px; }}
  @media (max-width: 640px) {{ .stat-row {{ grid-template-columns: repeat(2, 1fr); }} }}
  .stat-tile {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }}
  .stat-label {{ font-size: 12px; color: var(--text-secondary); margin: 0 0 8px; display:flex; align-items:center; gap:6px; }}
  .stat-value {{ font-size: 28px; font-weight: 700; margin: 0; font-variant-numeric: tabular-nums; }}
  .dot {{ width: 9px; height: 9px; border-radius: 50%; display:inline-block; flex: none; }}
  .dot.critical {{ background: var(--critical); }} .dot.warning {{ background: var(--warning); }}
  .dot.good {{ background: var(--good); }} .dot.neutral {{ background: var(--text-muted); }}
  .panel {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; margin-bottom: 20px; }}
  .panel-head {{ padding: 14px 18px; border-bottom: 1px solid var(--gridline); display: flex;
    align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; }}
  .panel-head h2 {{ font-size: 15px; margin: 0; font-weight: 650; }}
  .panel-head .hint {{ font-size: 12px; color: var(--text-muted); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  thead th {{ text-align: left; font-weight: 600; color: var(--text-muted); font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.03em; padding: 10px 18px; border-bottom: 1px solid var(--gridline); }}
  tbody td {{ padding: 12px 18px; border-bottom: 1px solid var(--gridline); vertical-align: top; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  .ad-name {{ font-weight: 600; }} .ad-meta {{ color: var(--text-muted); font-size: 12px; margin-top: 2px; }}
  .badge {{ display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600;
    padding: 3px 9px; border-radius: 999px; white-space: nowrap; }}
  .badge.critical {{ background: var(--critical-bg); color: var(--critical); }}
  .badge.warning {{ background: var(--warning-bg); color: #9a6b0e; }}
  .badge.good {{ background: var(--good-bg); color: var(--good); }}
  @media (prefers-color-scheme: dark) {{ .badge.warning {{ color: var(--warning); }} }}
  .metric {{ font-variant-numeric: tabular-nums; }}
  .delta {{ font-size: 11px; margin-left: 4px; }}
  .delta.down {{ color: var(--critical); }} .delta.up {{ color: var(--good); }} .delta.flat {{ color: var(--text-muted); }}
  .action {{ color: var(--text-secondary); max-width: 260px; }}
  .legend {{ display: flex; gap: 18px; flex-wrap: wrap; padding: 12px 18px; font-size: 12px;
    color: var(--text-secondary); border-top: 1px solid var(--gridline); }}
  .legend span {{ display:inline-flex; align-items:center; gap:6px; }}
  footer {{ font-size: 12px; color: var(--text-muted); text-align: center; margin-top: 12px; }}
</style>
</head>
<body>
<div class="wrap">
  <p class="eyebrow">Mailift — Meta Ads</p>
  <h1>Creative Fatigue Dashboard</h1>
  <p class="sub">Generato {generated_at} · {period_label} · soglia minima {min_impr} impr.</p>

  <div class="stat-row">
    <div class="stat-tile"><p class="stat-label"><span class="dot critical"></span>Urgenti</p>
      <p class="stat-value" style="color:var(--critical)">{urgent}</p></div>
    <div class="stat-tile"><p class="stat-label"><span class="dot warning"></span>Da monitorare</p>
      <p class="stat-value" style="color:#9a6b0e">{watch}</p></div>
    <div class="stat-tile"><p class="stat-label"><span class="dot good"></span>OK</p>
      <p class="stat-value" style="color:var(--good)">{ok}</p></div>
    <div class="stat-tile"><p class="stat-label"><span class="dot neutral"></span>Annunci analizzati</p>
      <p class="stat-value">{total}</p></div>
  </div>

  <div class="panel">
    <div class="panel-head">
      <h2>Annunci — ordinati per severità</h2>
      <span class="hint">Ordinati per severità, poi per impressioni nel periodo</span>
    </div>
    <table>
      <thead><tr><th>Annuncio</th><th>Età</th><th>CTR</th><th>Frequency</th><th>Stato</th><th>Azione</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <div class="legend">
      <span><span class="badge critical">🔴 Urgente</span> età ≥{age_urgent}gg o CTR ≤ -{ctr_urgent:.0f}% sett/sett</span>
      <span><span class="badge warning">🟡 Watch</span> età ≥{age_watch}gg, CTR ≤ -{ctr_watch:.0f}%, o frequency ≥ +{freq_watch:.0f}%</span>
      <span><span class="badge good">🟢 OK</span> nessun segnale di fatica</span>
    </div>
  </div>
  <footer>Generato da tools/creative_fatigue_detector.py — vedi workflows/creative_fatigue_monitoring.md</footer>
</div>
</body>
</html>
"""


def _delta_html(v: float | None, invert: bool) -> str:
    if v is None:
        return '<span class="delta flat">—</span>'
    good = (v <= 0) if invert else (v >= 0)
    cls = "flat" if abs(v) < 0.02 else ("up" if good else "down")
    sign = "+" if v > 0 else ""
    return f'<span class="delta {cls}">{sign}{round(v * 100)}%</span>'


def render_html(results: list[dict], period_label: str, min_impr: int) -> str:
    urgent = sum(1 for r in results if r["severity"] == "URGENTE")
    watch = sum(1 for r in results if r["severity"] == "WATCH")
    ok = len(results) - urgent - watch

    row_tpl = """<tr>
        <td><div class="ad-name">{name}</div><div class="ad-meta">{campaign} / {adset}</div></td>
        <td class="metric">{age}</td>
        <td class="metric">{ctr:.2f}% {ctr_delta}</td>
        <td class="metric">{freq:.2f} {freq_delta}</td>
        <td><span class="badge {css}">{icon} {label}</span></td>
        <td class="action">{action}</td>
    </tr>"""

    rows_html = "\n".join(
        row_tpl.format(
            name=r["name"],
            campaign=r["campaign"],
            adset=r["adset"],
            age=f"{r['age_days']}gg" if r["age_days"] is not None else "n/d",
            ctr=r["ctr_last"],
            ctr_delta=_delta_html(r["ctr_change"], invert=False),
            freq=r["frequency_last"],
            freq_delta=_delta_html(r["freq_change"], invert=True),
            css=_SEVERITY_CSS[r["severity"]],
            icon=_SEVERITY_ICON[r["severity"]],
            label=_SEVERITY_LABEL[r["severity"]],
            action=r["action"],
        )
        for r in results
    )
    if not rows_html:
        rows_html = '<tr><td colspan="6" class="action">Nessun annuncio con dati sufficienti nel periodo.</td></tr>'

    return _HTML_TEMPLATE.format(
        generated_at=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        period_label=period_label,
        min_impr=min_impr,
        urgent=urgent,
        watch=watch,
        ok=ok,
        total=len(results),
        rows=rows_html,
        age_urgent=AGE_URGENT_DAYS,
        age_watch=AGE_WATCH_DAYS,
        ctr_urgent=CTR_DECLINE_URGENT * 100,
        ctr_watch=CTR_DECLINE_WATCH * 100,
        freq_watch=FREQ_RISE_WATCH * 100,
    )


def write_html_report(results: list[dict], period_label: str, min_impr: int, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_html(results, period_label, min_impr), encoding="utf-8")
    print(f"\n📊 Report HTML: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rileva creative fatigue sugli annunci Meta")
    parser.add_argument("--days", type=int, default=28, help="Finestra di analisi in giorni (default 28, ignorato con --csv)")
    parser.add_argument("--all", action="store_true", help="Includi anche annunci PAUSED/non ACTIVE")
    parser.add_argument("--csv", type=str, default=None,
                        help="Analizza un export CSV di Ads Manager invece di chiamare l'API (nessun token richiesto)")
    parser.add_argument("--min-impressions", type=int, default=None,
                        help="Soglia minima impressioni nel periodo (default: 500 via API, 100 via --csv)")
    parser.add_argument("--include-today", action="store_true",
                        help="(solo --csv) includi la giornata odierna, di default esclusa perché parziale")
    parser.add_argument("--html", type=str, default=str(PROJECT_ROOT / ".tmp" / "creative_fatigue_report.html"),
                        help="Percorso del report HTML (default .tmp/creative_fatigue_report.html)")
    parser.add_argument("--no-html", action="store_true", help="Salta la scrittura del report HTML")
    args = parser.parse_args()

    if args.csv:
        csv_path = Path(args.csv)
        if not csv_path.exists():
            print(f"❌ File non trovato: {csv_path}")
            sys.exit(1)
        min_impr = args.min_impressions if args.min_impressions is not None else 100
        print(f"[creative-fatigue] Analisi export CSV: {csv_path}")
        results = analyze_csv(csv_path, min_impressions=min_impr, include_inactive=args.all,
                               exclude_today=not args.include_today)
        period_label = "export CSV (nessuna finestra temporale fissa — vedi giorni per annuncio)"
    else:
        if not TOKEN or not ACCOUNT_ID:
            print("❌ FB_ACCESS_TOKEN o FB_AD_ACCOUNT_ID non configurati nel .env "
                  "(oppure usa --csv per analizzare un export manuale di Ads Manager)")
            sys.exit(1)

        min_impr = args.min_impressions if args.min_impressions is not None else MIN_IMPRESSIONS

        print(f"[creative-fatigue] Recupero annunci ({'tutti' if args.all else 'solo ACTIVE'})...")
        ads = fetch_ads(include_all=args.all)
        print(f"    {len(ads)} annunci trovati")

        print(f"[creative-fatigue] Recupero insight settimanali ultimi {args.days}gg...")
        weekly = fetch_weekly_insights(args.days)

        results = analyze(ads, weekly, min_impressions=min_impr)
        period_label = f"ultimi {args.days}gg"

    print_report(results, period_label)

    if not args.no_html:
        write_html_report(results, period_label, min_impr, Path(args.html))


if __name__ == "__main__":
    main()
