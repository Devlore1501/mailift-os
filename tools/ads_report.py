#!/usr/bin/env python3
"""
Report giornaliero ads Facebook — mattina e sera.
Genera testo + HTML con trend, CPL per adset e azioni consigliate.

CLI:
  python tools/ads_report.py          # report oggi + ieri
  python tools/ads_report.py morning  # report mattutino (ultimi 2gg)
  python tools/ads_report.py evening  # report serale (solo oggi)
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path.home() / ".secrets" / "mailift" / ".env")
load_dotenv(ROOT / ".env")

TOKEN = os.environ.get("FB_ACCESS_TOKEN", "")
ACCOUNT = os.environ.get("FB_AD_ACCOUNT_ID", "")
BASE = "https://graph.facebook.com/v21.0"

LEAD_GEN_KEYWORDS = ["Modulo", "acquistion", "CBO"]
CPL_TARGET = 25.0      # CPL obiettivo
CPL_WARNING = 40.0     # soglia warning
SPEND_DAILY_MAX = 60.0 # soglia spesa giornaliera


def fetch_adsets(since: str, until: str) -> list[dict]:
    r = requests.get(f"{BASE}/{ACCOUNT}/insights", params={
        "access_token": TOKEN,
        "level": "adset",
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "fields": "campaign_name,adset_name,spend,impressions,clicks,ctr,cpm,cpc,actions,cost_per_action_type",
        "limit": 100,
    })
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"FB API error: {data['error']}")
    return data.get("data", [])


def fetch_campaigns(since: str, until: str) -> list[dict]:
    r = requests.get(f"{BASE}/{ACCOUNT}/insights", params={
        "access_token": TOKEN,
        "level": "campaign",
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "fields": "campaign_name,spend,impressions,clicks,ctr,cpm,actions,cost_per_action_type",
        "limit": 50,
    })
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"FB API error: {data['error']}")
    return data.get("data", [])


def leads(ad: dict) -> int:
    return next((int(a["value"]) for a in ad.get("actions", []) if a["action_type"] == "lead"), 0)


def cpl(ad: dict) -> float | None:
    return next((float(c["value"]) for c in ad.get("cost_per_action_type", []) if c["action_type"] == "lead"), None)


def purchase(ad: dict) -> int:
    return next((int(a["value"]) for a in ad.get("actions", []) if a["action_type"] == "purchase"), 0)


def is_lead_gen(campaign_name: str) -> bool:
    return any(k in campaign_name for k in LEAD_GEN_KEYWORDS)


def summarize(adsets: list[dict]) -> dict:
    lead_adsets = [a for a in adsets if is_lead_gen(a.get("campaign_name", ""))]
    total_spend = sum(float(a.get("spend", 0)) for a in adsets)
    total_leads = sum(leads(a) for a in lead_adsets)
    total_purchase = sum(purchase(a) for a in adsets)
    return {
        "spend": total_spend,
        "leads": total_leads,
        "purchases": total_purchase,
        "cpl": total_spend / total_leads if total_leads else None,
        "lead_adsets": lead_adsets,
    }


def adset_rows(adsets: list[dict]) -> list[dict]:
    rows = []
    for a in sorted(adsets, key=lambda x: float(x.get("spend", 0)), reverse=True):
        spend = float(a.get("spend", 0))
        if spend == 0:
            continue
        _leads = leads(a)
        _cpl = cpl(a)
        rows.append({
            "name": a.get("adset_name", "?"),
            "campaign": a.get("campaign_name", "?"),
            "spend": spend,
            "ctr": float(a.get("ctr", 0)),
            "cpm": float(a.get("cpm", 0)),
            "leads": _leads,
            "cpl": _cpl,
        })
    return rows


def recommend(row: dict) -> str:
    if row["leads"] == 0 and row["spend"] > 20:
        return "⛔ PAUSA — spesa alta, 0 lead"
    if row["cpl"] and row["cpl"] > CPL_WARNING:
        return f"⚠️ CPL alto (€{row['cpl']:.0f}) — monitora"
    if row["cpl"] and row["cpl"] <= CPL_TARGET:
        return "✅ SCALA — CPL sotto obiettivo"
    if row["ctr"] < 0.8:
        return "⚠️ CTR basso — creative da rivedere"
    return "👀 Monitora"


def trend_arrow(today_val: float | None, yesterday_val: float | None, lower_is_better: bool = True) -> str:
    if today_val is None or yesterday_val is None or yesterday_val == 0:
        return "—"
    delta = today_val - yesterday_val
    if abs(delta) < 0.5:
        return "→"
    if lower_is_better:
        return "↓ migliora" if delta < 0 else "↑ peggiora"
    return "↑ migliora" if delta > 0 else "↓ peggiora"


def build_report(mode: str = "morning") -> tuple[str, str]:
    today = date.today()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)

    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    week_str = week_ago.strftime("%Y-%m-%d")

    # Dati
    adsets_today = fetch_adsets(today_str, today_str)
    adsets_yesterday = fetch_adsets(yesterday_str, yesterday_str)
    adsets_week = fetch_adsets(week_str, yesterday_str)

    s_today = summarize(adsets_today)
    s_yest = summarize(adsets_yesterday)
    s_week = summarize(adsets_week)

    rows_today = adset_rows([a for a in adsets_today if is_lead_gen(a.get("campaign_name", ""))])
    rows_yest = adset_rows([a for a in adsets_yesterday if is_lead_gen(a.get("campaign_name", ""))])

    # CPL trend
    cpl_trend = trend_arrow(s_today["cpl"], s_yest["cpl"], lower_is_better=True)
    spend_trend = trend_arrow(s_today["spend"], s_yest["spend"], lower_is_better=False)

    period = "MATTINO" if mode == "morning" else "SERA"
    dt = datetime.now().strftime("%d/%m/%Y %H:%M")

    # --- TESTO ---
    lines = [
        f"📊 REPORT ADS — {period} {dt}",
        "=" * 45,
        "",
        "OGGI",
        f"  Spesa:   €{s_today['spend']:.2f}  {spend_trend}",
        f"  Lead:    {s_today['leads']}",
        f"  CPL:     " + (f"€{s_today['cpl']:.2f}  {cpl_trend}" if s_today['cpl'] else f"—  {cpl_trend}"),
        f"  Acquisti: {s_today['purchases']}",
        "",
        "IERI",
        f"  Spesa:  €{s_yest['spend']:.2f}",
        f"  Lead:   {s_yest['leads']}",
        f"  CPL:    " + (f"€{s_yest['cpl']:.2f}" if s_yest["cpl"] else "—"),
        "",
        f"ULTIMI 7 GIORNI",
        f"  Spesa totale: €{s_week['spend']:.2f}",
        f"  Lead totali:  {s_week['leads']}",
        f"  CPL medio:    " + (f"€{s_week['cpl']:.2f}" if s_week["cpl"] else "—"),
        "",
        "ADSET OGGI",
        "-" * 45,
    ]

    for row in rows_today:
        yest_row = next((r for r in rows_yest if r["name"] == row["name"]), None)
        cpl_t = trend_arrow(row["cpl"], yest_row["cpl"] if yest_row else None, lower_is_better=True)
        lines += [
            f"[{row['name']}]",
            f"  €{row['spend']:.2f} | CTR {row['ctr']:.2f}% | CPM €{row['cpm']:.2f}",
            f"  Lead: {row['leads']}" + (f" | CPL €{row['cpl']:.2f} {cpl_t}" if row["cpl"] else ""),
            f"  → {recommend(row)}",
            "",
        ]

    if not rows_today:
        lines.append("  Nessun adset attivo oggi.\n")

    # Azioni consigliate aggregate
    lines += ["AZIONI CONSIGLIATE", "-" * 45]
    actions = []
    for row in rows_today:
        r = recommend(row)
        if "PAUSA" in r:
            actions.append(f"• Pausa [{row['name']}] — €{row['spend']:.0f} spesi, 0 lead")
        elif "SCALA" in r:
            actions.append(f"• Scala [{row['name']}] — CPL €{row['cpl']:.2f}, sotto obiettivo")

    if s_today["spend"] > SPEND_DAILY_MAX:
        actions.append(f"• ⚠️ Spesa oggi €{s_today['spend']:.0f} > soglia €{SPEND_DAILY_MAX:.0f} — controlla budget")

    if not actions:
        actions.append("• Nessuna azione urgente. Monitora domani.")

    lines += actions

    text = "\n".join(lines)

    # --- HTML ---
    def badge(val: str) -> str:
        if "PAUSA" in val or "⛔" in val:
            return f'<span style="color:#e53e3e;font-weight:bold">{val}</span>'
        if "SCALA" in val or "✅" in val:
            return f'<span style="color:#38a169;font-weight:bold">{val}</span>'
        if "⚠️" in val:
            return f'<span style="color:#d69e2e;font-weight:bold">{val}</span>'
        return f'<span style="color:#718096">{val}</span>'

    adset_html = ""
    for row in rows_today:
        yest_row = next((r for r in rows_yest if r["name"] == row["name"]), None)
        cpl_t = trend_arrow(row["cpl"], yest_row["cpl"] if yest_row else None, lower_is_better=True)
        cpl_str = f"€{row['cpl']:.2f} {cpl_t}" if row["cpl"] else "—"
        rec = recommend(row)
        adset_html += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee"><b>{row['name']}</b></td>
          <td style="padding:8px;border-bottom:1px solid #eee">€{row['spend']:.2f}</td>
          <td style="padding:8px;border-bottom:1px solid #eee">{row['ctr']:.2f}%</td>
          <td style="padding:8px;border-bottom:1px solid #eee">{row['leads']}</td>
          <td style="padding:8px;border-bottom:1px solid #eee">{cpl_str}</td>
          <td style="padding:8px;border-bottom:1px solid #eee">{badge(rec)}</td>
        </tr>"""

    actions_html = "".join(f"<li>{a}</li>" for a in actions)

    html = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
  <h2 style="color:#1a202c">📊 Report Ads — {period} {dt}</h2>

  <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
    <tr>
      <th style="background:#1a202c;color:white;padding:10px;text-align:left">Periodo</th>
      <th style="background:#1a202c;color:white;padding:10px">Spesa</th>
      <th style="background:#1a202c;color:white;padding:10px">Lead</th>
      <th style="background:#1a202c;color:white;padding:10px">CPL</th>
    </tr>
    <tr style="background:#f7fafc">
      <td style="padding:8px;font-weight:bold">Oggi {spend_trend}</td>
      <td style="padding:8px;text-align:center">€{s_today['spend']:.2f}</td>
      <td style="padding:8px;text-align:center">{s_today['leads']}</td>
      <td style="padding:8px;text-align:center">{"€"+f"{s_today['cpl']:.2f} "+cpl_trend if s_today['cpl'] else "—"}</td>
    </tr>
    <tr>
      <td style="padding:8px">Ieri</td>
      <td style="padding:8px;text-align:center">€{s_yest['spend']:.2f}</td>
      <td style="padding:8px;text-align:center">{s_yest['leads']}</td>
      <td style="padding:8px;text-align:center">{"€"+f"{s_yest['cpl']:.2f}" if s_yest['cpl'] else "—"}</td>
    </tr>
    <tr style="background:#f7fafc">
      <td style="padding:8px">7 giorni</td>
      <td style="padding:8px;text-align:center">€{s_week['spend']:.2f}</td>
      <td style="padding:8px;text-align:center">{s_week['leads']}</td>
      <td style="padding:8px;text-align:center">{"€"+f"{s_week['cpl']:.2f}" if s_week['cpl'] else "—"}</td>
    </tr>
  </table>

  <h3 style="color:#1a202c">Adset oggi</h3>
  <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
    <tr style="background:#2d3748;color:white">
      <th style="padding:8px;text-align:left">Adset</th>
      <th style="padding:8px">Spesa</th>
      <th style="padding:8px">CTR</th>
      <th style="padding:8px">Lead</th>
      <th style="padding:8px">CPL</th>
      <th style="padding:8px">Azione</th>
    </tr>
    {adset_html if adset_html else '<tr><td colspan="6" style="padding:12px;text-align:center;color:#718096">Nessun adset attivo</td></tr>'}
  </table>

  <h3 style="color:#1a202c">Azioni consigliate</h3>
  <ul style="background:#fffbeb;border-left:4px solid #d69e2e;padding:12px 12px 12px 30px;margin:0">
    {actions_html}
  </ul>

  <p style="color:#718096;font-size:12px;margin-top:20px">
    Generato automaticamente da Mailift · <a href="mailto:info@mailift.com">info@mailift.com</a>
  </p>
</div>
"""
    return text, html


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    text, html = build_report(mode)
    print(text)
    if "--html" in sys.argv:
        print("\n--- HTML ---\n")
        print(html)
