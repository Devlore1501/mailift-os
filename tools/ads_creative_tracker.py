#!/usr/bin/env python3
"""
Tracciamento creative ads Facebook.
Scarica per ogni ad: headline, body, CTA + metriche di performance.

CLI:
  python tools/ads_creative_tracker.py              # ultimi 7 giorni, stampa report
  python tools/ads_creative_tracker.py --days 14    # ultimi 14 giorni
  python tools/ads_creative_tracker.py --output .tmp/creatives.csv
  python tools/ads_creative_tracker.py weekly       # analisi angoli + CSV (7 giorni)
"""
from __future__ import annotations

import csv
import json
import os
import sys
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

DEFAULT_OUTPUT = ROOT / ".tmp" / "ads_creatives.csv"
LEAD_GEN_KEYWORDS = ["Modulo", "acquistion", "CBO"]

CPL_TARGET  = 25.0
CPL_WARNING = 40.0


# ── helpers ──────────────────────────────────────────────────────────────────

def _get(url: str, params: dict) -> dict:
    params["access_token"] = TOKEN
    r = requests.get(url, params=params)
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"FB API error: {data['error']['message']}")
    return data


def _paginate(url: str, params: dict) -> list[dict]:
    """Segue i cursori di paginazione e restituisce tutti i risultati."""
    results = []
    data = _get(url, params)
    results.extend(data.get("data", []))
    while data.get("paging", {}).get("next"):
        r = requests.get(data["paging"]["next"])
        data = r.json()
        results.extend(data.get("data", []))
    return results


def leads_from(ad: dict) -> int:
    return next((int(a["value"]) for a in ad.get("actions", [])
                 if a["action_type"] == "lead"), 0)


def cpl_from(ad: dict) -> float | None:
    return next((float(c["value"]) for c in ad.get("cost_per_action_type", [])
                 if c["action_type"] == "lead"), None)


def is_lead_gen(campaign_name: str) -> bool:
    return any(k in campaign_name for k in LEAD_GEN_KEYWORDS)


# ── fetch creative per singolo ad ────────────────────────────────────────────

def fetch_creative(creative_id: str) -> dict:
    """Ritorna headline, body, cta_type per un creative_id."""
    try:
        data = _get(f"{BASE}/{creative_id}", {
            "fields": "title,body,call_to_action_type,object_story_spec,image_url,thumbnail_url"
        })
        headline = data.get("title") or ""
        body     = data.get("body") or ""
        cta      = data.get("call_to_action_type") or ""

        # fallback: prova object_story_spec per post organici o video
        spec = data.get("object_story_spec", {})
        link_data  = spec.get("link_data", {})
        video_data = spec.get("video_data", {})

        if not headline:
            headline = (link_data.get("name") or
                        video_data.get("title") or
                        spec.get("template_data", {}).get("message", ""))
        if not body:
            body = (link_data.get("message") or
                    video_data.get("message") or "")
        if not cta:
            cta = (link_data.get("call_to_action", {}).get("type") or
                   video_data.get("call_to_action", {}).get("type") or "")

        image_url = data.get("image_url") or data.get("thumbnail_url") or ""
        return {"headline": headline, "body": body, "cta": cta, "image_url": image_url}
    except Exception:
        return {"headline": "", "body": "", "cta": "", "image_url": ""}


# ── fetch ads con insights ────────────────────────────────────────────────────

def fetch_ads_with_insights(since: str, until: str) -> list[dict]:
    """
    Tira tutti gli ad con creatives + metriche nel periodo indicato.
    Restituisce lista di dict pronti per il CSV.
    """
    # step 1: insights a livello ad (hanno campaign_name affidabile)
    insights_raw = _paginate(f"{BASE}/{ACCOUNT}/insights", {
        "level": "ad",
        "time_range": json.dumps({"since": since, "until": until}),
        "fields": "ad_id,ad_name,adset_name,campaign_name,spend,impressions,clicks,ctr,cpm,cpc,actions,cost_per_action_type",
        "limit": 200,
    })
    insights_by_id = {r["ad_id"]: r for r in insights_raw}

    # step 2: lista ads con creative_id (solo per gli ad che hanno insights)
    # fetch tutti gli ad con creative
    ads_raw = _paginate(f"{BASE}/{ACCOUNT}/ads", {
        "fields": "id,name,creative",
        "limit": 200,
    })
    creative_by_ad = {a["id"]: a.get("creative", {}).get("id", "") for a in ads_raw}

    rows = []
    for ad_id, ins in insights_by_id.items():
        campaign_name = ins.get("campaign_name", "")
        spend  = float(ins.get("spend", 0))

        # creative — fetch separata
        creative_id = creative_by_ad.get(ad_id, "")
        headline, body, cta = "", "", ""
        if creative_id:
            details  = fetch_creative(creative_id)
            headline = details["headline"]
            body     = details["body"]
            cta      = details["cta"]

        # metriche
        _leads = leads_from(ins)
        _cpl   = cpl_from(ins)

        rows.append({
            "campaign":    campaign_name,
            "adset":       ins.get("adset_name", ""),
            "ad_name":     ins.get("ad_name", ""),
            "creative_id": creative_id,
            "headline":    headline.strip(),
            "body":        body.strip()[:300],   # tronca per leggibilità
            "cta":         cta,
            "spend":       round(spend, 2),
            "impressions": int(ins.get("impressions", 0)),
            "clicks":      int(ins.get("clicks", 0)),
            "ctr":         round(float(ins.get("ctr", 0)), 2),
            "cpm":         round(float(ins.get("cpm", 0)), 2),
            "leads":       _leads,
            "cpl":         round(_cpl, 2) if _cpl else None,
        })

    return sorted(rows, key=lambda x: x["spend"], reverse=True)


# ── analisi angoli ────────────────────────────────────────────────────────────

def analyze_angles(rows: list[dict]) -> str:
    """Produce un testo con top performer, worst e pattern vincenti."""
    active = [r for r in rows if r["spend"] > 5]
    if not active:
        return "Nessun ad con spesa sufficiente per l'analisi."

    with_cpl = [r for r in active if r["cpl"]]
    without  = [r for r in active if not r["cpl"]]

    ranked = sorted(with_cpl, key=lambda x: x["cpl"])
    top3   = ranked[:3]
    worst3 = ranked[-3:]

    lines = ["=" * 50, "ANALISI ANGOLI — ULTIMI 7 GIORNI", "=" * 50, ""]

    lines.append("TOP PERFORMER (CPL più basso):")
    for r in top3:
        lines.append(f"  [{r['ad_name']}]")
        lines.append(f"  Headline: {r['headline'] or '(non disponibile)'}")
        lines.append(f"  CPL: €{r['cpl']:.2f} | Spend: €{r['spend']:.0f} | Lead: {r['leads']}")
        lines.append(f"  CTR: {r['ctr']:.2f}% | CPM: €{r['cpm']:.2f}")
        lines.append("")

    lines.append("WORST PERFORMER (CPL più alto):")
    for r in worst3:
        lines.append(f"  [{r['ad_name']}]")
        lines.append(f"  Headline: {r['headline'] or '(non disponibile)'}")
        lines.append(f"  CPL: €{r['cpl']:.2f} | Spend: €{r['spend']:.0f} | Lead: {r['leads']}")
        lines.append("")

    if without:
        lines.append(f"AD SENZA LEAD ({len(without)} ad con spesa > €5):")
        for r in without:
            lines.append(f"  [{r['ad_name']}] — €{r['spend']:.0f} spesi, 0 lead → candidato PAUSA")
        lines.append("")

    # CPL medio per adset
    adsets: dict[str, list] = {}
    for r in active:
        adsets.setdefault(r["adset"], []).append(r)

    lines.append("CPL MEDIO PER ADSET:")
    for adset, ads in sorted(adsets.items()):
        total_spend = sum(a["spend"] for a in ads)
        total_leads = sum(a["leads"] for a in ads)
        avg_cpl = total_spend / total_leads if total_leads else None
        cpl_str = f"€{avg_cpl:.2f}" if avg_cpl else "nessun lead"
        lines.append(f"  {adset}: {cpl_str} ({len(ads)} ad, €{total_spend:.0f} spesi)")
    lines.append("")

    # pattern vincenti dai top3
    lines.append("PATTERN VINCENTI (da top performer):")
    winning_headlines = [r["headline"] for r in top3 if r["headline"]]
    if winning_headlines:
        lines.append("  Headline che convertono:")
        for h in winning_headlines:
            lines.append(f"    • \"{h[:80]}\"")
    lines.append("")

    lines.append("FLAG CRITICI:")
    critical = [r for r in active if r["cpl"] and r["cpl"] > CPL_WARNING]
    drains   = [r for r in active if not r["cpl"] and r["spend"] > 20]
    if critical:
        for r in critical:
            lines.append(f"  ⚠️ [{r['ad_name']}] CPL €{r['cpl']:.0f} — oltre soglia warning €{CPL_WARNING:.0f}")
    if drains:
        for r in drains:
            lines.append(f"  ⛔ [{r['ad_name']}] €{r['spend']:.0f} spesi, 0 lead")
    if not critical and not drains:
        lines.append("  Nessun flag critico.")

    return "\n".join(lines)


# ── export CSV ────────────────────────────────────────────────────────────────

def save_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["campaign","adset","ad_name","creative_id","headline","body","cta",
                  "spend","impressions","clicks","ctr","cpm","leads","cpl"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"CSV salvato: {output_path} ({len(rows)} righe)")


# ── build_weekly_report (usato dal task schedulato) ──────────────────────────

def build_weekly_report() -> tuple[str, str]:
    """
    Genera report settimanale: analisi angoli + CSV.
    Ritorna (testo, html) come ads_report.py.
    """
    today     = date.today()
    week_ago  = today - timedelta(days=7)
    since_str = week_ago.strftime("%Y-%m-%d")
    until_str = today.strftime("%Y-%m-%d")

    rows = fetch_ads_with_insights(since_str, until_str)
    save_csv(rows, DEFAULT_OUTPUT)

    analysis = analyze_angles(rows)

    # --- TESTO ---
    text = f"📊 REPORT SETTIMANALE CREATIVE — {today.strftime('%d/%m/%Y')}\n"
    text += f"Periodo: {since_str} → {until_str}\n\n"
    text += analysis
    text += f"\n\nCSV completo: {DEFAULT_OUTPUT}\n"
    text += "\n" + "=" * 50 + "\n"
    text += "PROPOSTE NUOVE CREATIVE DA TESTARE\n"
    text += "=" * 50 + "\n"
    text += "(Vedi analisi Claude nella sezione dedicata dell'email)\n"

    # --- HTML ---
    analysis_html = analysis.replace("\n", "<br>").replace("  ", "&nbsp;&nbsp;")

    rows_html = ""
    for r in rows[:20]:  # prime 20 per non appesantire l'email
        cpl_str   = f"€{r['cpl']:.2f}" if r["cpl"] else "—"
        cpl_color = ""
        if r["cpl"]:
            if r["cpl"] <= CPL_TARGET:
                cpl_color = "color:#38a169;font-weight:bold"
            elif r["cpl"] > CPL_WARNING:
                cpl_color = "color:#e53e3e;font-weight:bold"
        hl = (r["headline"] or "—")[:60]
        rows_html += f"""
        <tr>
          <td style="padding:6px;border-bottom:1px solid #eee;font-size:12px">{r['ad_name'][:35]}</td>
          <td style="padding:6px;border-bottom:1px solid #eee;font-size:12px">{hl}</td>
          <td style="padding:6px;border-bottom:1px solid #eee;font-size:12px">{r['cta'] or '—'}</td>
          <td style="padding:6px;border-bottom:1px solid #eee;text-align:center">€{r['spend']:.0f}</td>
          <td style="padding:6px;border-bottom:1px solid #eee;text-align:center">{r['leads']}</td>
          <td style="padding:6px;border-bottom:1px solid #eee;text-align:center;{cpl_color}">{cpl_str}</td>
        </tr>"""

    html = f"""
<div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto">
  <h2 style="color:#1a202c">📊 Report Settimanale Creative Ads</h2>
  <p style="color:#718096">{since_str} → {until_str}</p>

  <h3 style="color:#1a202c">Tutti gli ad ({len(rows)} totali)</h3>
  <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:20px">
    <tr style="background:#2d3748;color:white">
      <th style="padding:8px;text-align:left">Ad</th>
      <th style="padding:8px;text-align:left">Headline</th>
      <th style="padding:8px">CTA</th>
      <th style="padding:8px">Spesa</th>
      <th style="padding:8px">Lead</th>
      <th style="padding:8px">CPL</th>
    </tr>
    {rows_html}
  </table>

  <h3 style="color:#1a202c">Analisi angoli</h3>
  <div style="background:#f7fafc;padding:16px;border-radius:6px;font-size:13px;line-height:1.6">
    {analysis_html}
  </div>

  <h3 style="color:#1a202c">Proposte creative da testare</h3>
  <div style="background:#fffbeb;border-left:4px solid #d69e2e;padding:16px;font-size:13px;line-height:1.6">
    <p><i>Questa sezione viene completata dall'analisi AI nella sessione Claude dedicata.</i></p>
  </div>

  <p style="color:#718096;font-size:11px;margin-top:20px">
    CSV completo disponibile su: {DEFAULT_OUTPUT}<br>
    Generato automaticamente da Mailift · <a href="mailto:info@mailift.com">info@mailift.com</a>
  </p>
</div>
"""
    return text, html


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mode   = sys.argv[1] if len(sys.argv) > 1 else "weekly"
    days   = int(next((sys.argv[i+1] for i, a in enumerate(sys.argv) if a == "--days"), 7))
    output = Path(next((sys.argv[i+1] for i, a in enumerate(sys.argv) if a == "--output"),
                       str(DEFAULT_OUTPUT)))

    today    = date.today()
    since    = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    until    = today.strftime("%Y-%m-%d")

    if mode == "weekly":
        text, html = build_weekly_report()
        print(text)
        if "--html" in sys.argv:
            print("\n--- HTML ---\n", html)
    else:
        rows = fetch_ads_with_insights(since, until)
        save_csv(rows, output)

        print(f"\nRiepilogo {since} → {until}:")
        print(f"  Ad trovati:    {len(rows)}")
        print(f"  Totale spesa:  €{sum(r['spend'] for r in rows):.2f}")
        print(f"  Totale lead:   {sum(r['leads'] for r in rows)}")
        print()
        print(analyze_angles(rows))
