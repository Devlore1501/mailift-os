#!/usr/bin/env python3
"""Ads Advisor — analizza i dati del Google Sheet e genera raccomandazioni AI.

Legge i tab Daily Metrics, Campagne, Creatività Test e Prodotti,
li invia a Claude con il contesto del business Mailift, e scrive
un tab "Analisi AI" con raccomandazioni prioritizzate.

Usage:
    python tools/ads_advisor.py          # analisi ultimi 14 giorni
    python tools/ads_advisor.py 7        # analisi ultimi 7 giorni
    python tools/ads_advisor.py 30       # analisi ultimi 30 giorni
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.credentials import Credentials
import anthropic
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

SPREADSHEET_ID = os.environ.get("GSHEETS_SPREADSHEET_ID", "")
TOKEN_FILE     = PROJECT_ROOT / "tokens" / "gsheets.json"
GSHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

ANTHROPIC_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")

# Colori tab Analisi AI
HDR_BG   = "#1a1a2e"
URGENT   = "#fde8e8"
WARN     = "#fff3cd"
OK_COLOR = "#d9f7e8"
INFO_BG  = "#e8f4fd"
ALT_ROW  = "#f8f9fa"


# ── Google Sheets ─────────────────────────────────────────────────────────────

def _gc() -> gspread.Client:
    if not TOKEN_FILE.exists():
        raise RuntimeError("Token GSheets non trovato. Esegui: python tools/gsheets_oauth_setup.py")
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), GSHEETS_SCOPES)
    return gspread.authorize(creds)


def _get_tab(ss: Any, name: str) -> list[list]:
    ws = ss.worksheet(name)
    return ws.get_all_values()


def _safe_float(v: Any) -> float:
    try:
        return float(str(v).replace("€", "").replace(",", ".").replace("%", "").strip())
    except Exception:
        return 0.0


# ── Lettura e aggregazione dati ───────────────────────────────────────────────

def _read_daily(rows: list[list], days: int) -> dict:
    """Aggrega Daily Metrics per gli ultimi N giorni."""
    if len(rows) <= 1:
        return {}
    headers = rows[0]
    data = rows[1:]

    # Ordina per data desc, prendi ultimi N giorni
    data_sorted = sorted(data, key=lambda r: r[0] if r[0] else "", reverse=True)
    data_sorted = [r for r in data_sorted if r[0]][:days]

    def col(row, name):
        try:
            return _safe_float(row[headers.index(name)])
        except (ValueError, IndexError):
            return 0.0

    totals = {
        "giorni": len(data_sorted),
        "spend": 0.0, "revenue": 0.0, "profit": 0.0,
        "ordini": 0, "fe_ordini": 0, "bump_ordini": 0, "oto_ordini": 0,
        "fe_revenue": 0.0, "bump_revenue": 0.0, "oto_revenue": 0.0,
        "fb_acquisti": 0, "impressioni": 0, "click": 0,
        "giorni_dati": [],
    }
    for r in data_sorted:
        totals["spend"]       += col(r, "FB Spend (€)")
        totals["revenue"]     += col(r, "TOT Revenue (€)")
        totals["profit"]      += col(r, "Profitto (€)")
        totals["fe_ordini"]   += int(col(r, "FE Ordini"))
        totals["bump_ordini"] += int(col(r, "BUMP Ordini"))
        totals["oto_ordini"]  += int(col(r, "OTO Ordini"))
        totals["fe_revenue"]  += col(r, "FE Revenue (€)")
        totals["bump_revenue"]+= col(r, "BUMP Revenue (€)")
        totals["oto_revenue"] += col(r, "OTO Revenue (€)")
        totals["fb_acquisti"] += int(col(r, "FB Acquisti"))
        totals["impressioni"] += int(col(r, "Impressioni"))
        totals["click"]       += int(col(r, "Click"))
        totals["giorni_dati"].append({
            "data":    r[0],
            "spend":   col(r, "FB Spend (€)"),
            "revenue": col(r, "TOT Revenue (€)"),
            "profit":  col(r, "Profitto (€)"),
            "roas":    col(r, "ROAS"),
        })

    totals["ordini"]  = totals["fe_ordini"] + totals["bump_ordini"] + totals["oto_ordini"]
    totals["roas"]    = round(totals["revenue"] / totals["spend"], 2) if totals["spend"] > 0 else 0
    totals["cpp"]     = round(totals["spend"] / totals["fb_acquisti"], 2) if totals["fb_acquisti"] > 0 else 0
    totals["aov"]     = round(totals["revenue"] / totals["ordini"], 2) if totals["ordini"] > 0 else 0
    totals["bump_rate"] = round(totals["bump_ordini"] / totals["fe_ordini"] * 100, 1) if totals["fe_ordini"] > 0 else 0
    totals["oto_rate"]  = round(totals["oto_ordini"] / totals["fe_ordini"] * 100, 1) if totals["fe_ordini"] > 0 else 0
    totals["ctr"]     = round(totals["click"] / totals["impressioni"] * 100, 3) if totals["impressioni"] > 0 else 0

    return totals


def _read_campaigns(rows: list[list]) -> list[dict]:
    if len(rows) <= 1:
        return []
    headers = rows[0]
    result  = []
    for r in rows[1:]:
        if not r[0]:
            continue
        def get(name):
            try:
                return r[headers.index(name)]
            except (ValueError, IndexError):
                return ""
        result.append({
            "nome":       get("Campagna"),
            "status":     get("Status"),
            "spend":      _safe_float(get("Spend (€)")),
            "impressioni":_safe_float(get("Impressioni")),
            "click":      _safe_float(get("Click")),
            "ctr":        _safe_float(get("CTR (%)")),
            "cpc":        _safe_float(get("CPC (€)")),
            "acquisti":   _safe_float(get("Acquisti")),
            "revenue":    _safe_float(get("Revenue (€)")),
            "roas":       _safe_float(get("ROAS")),
            "budget":     _safe_float(get("Budget/gg (€)")),
        })
    return result


def _read_creatives(rows: list[list]) -> list[dict]:
    if len(rows) <= 1:
        return []
    headers = rows[0]
    result  = []
    for r in rows[1:]:
        if not r[0]:
            continue
        def get(name):
            try:
                return r[headers.index(name)]
            except (ValueError, IndexError):
                return ""
        result.append({
            "annuncio":  get("Annuncio"),
            "adset":     get("AdSet"),
            "campagna":  get("Campagna"),
            "spend":     _safe_float(get("Spend (€)")),
            "click":     _safe_float(get("Click")),
            "ctr":       _safe_float(get("CTR (%)")),
            "cpc":       _safe_float(get("CPC (€)")),
            "acquisti":  _safe_float(get("Acquisti")),
            "revenue":   _safe_float(get("Revenue (€)")),
            "roas":      _safe_float(get("ROAS")),
        })
    return result


def _read_products(rows: list[list]) -> list[dict]:
    if len(rows) <= 1:
        return []
    headers = rows[0]
    result  = []
    for r in rows[1:]:
        if not r[0]:
            continue
        def get(name):
            try:
                return r[headers.index(name)]
            except (ValueError, IndexError):
                return ""
        result.append({
            "prodotto": get("Prodotto"),
            "tipo":     get("Tipo"),
            "vendite":  int(_safe_float(get("N° Vendite"))),
            "revenue":  _safe_float(get("Revenue (€)")),
            "pct":      _safe_float(get("% Revenue")),
        })
    return result


# ── Prompt Claude ─────────────────────────────────────────────────────────────

def _build_prompt(daily: dict, campaigns: list, creatives: list, products: list, days: int) -> str:
    def fmt_camp(c):
        return (f"  • {c['nome']} [{c['status']}] — Spend: €{c['spend']:.2f} | "
                f"ROAS: {c['roas']:.2f} | Acquisti: {int(c['acquisti'])} | "
                f"CTR: {c['ctr']:.2f}% | Budget/gg: €{c['budget']:.2f}")

    def fmt_ad(a):
        return (f"  • {a['annuncio']} ({a['campagna']}) — Spend: €{a['spend']:.2f} | "
                f"ROAS: {a['roas']:.2f} | CTR: {a['ctr']:.2f}% | Acquisti: {int(a['acquisti'])}")

    def fmt_prod(p):
        return f"  • {p['prodotto']} ({p['tipo']}) — {p['vendite']} vendite | €{p['revenue']:.2f} ({p['pct']:.1f}%)"

    trend_lines = ""
    if daily.get("giorni_dati"):
        ultimi5 = daily["giorni_dati"][:5]
        trend_lines = "\nTrend ultimi 5 giorni (più recente prima):\n"
        for g in ultimi5:
            trend_lines += f"  {g['data']}: Spend €{g['spend']:.2f} | Revenue €{g['revenue']:.2f} | Profitto €{g['profit']:.2f} | ROAS {g['roas']:.2f}\n"

    camps_text = "\n".join(fmt_camp(c) for c in campaigns) if campaigns else "  (nessun dato)"
    ads_text   = "\n".join(fmt_ad(a) for a in creatives[:15]) if creatives else "  (nessun dato)"
    prods_text = "\n".join(fmt_prod(p) for p in products) if products else "  (nessun dato)"

    return f"""Sei un esperto di performance marketing e paid ads per eCommerce DTC italiano.

CONTESTO BUSINESS:
- Azienda: Mailift Srl — gestisce gli ads per conto proprio (funnel di info-prodotti/coaching)
- Struttura funnel: FE (front-end) → BUMP (order bump) → OTO (one-time offer)
- Piattaforma ads: Facebook/Instagram
- Obiettivi: ROAS ≥ 2.0, profitto positivo, scalare le creative vincenti
- Budget tipico: €50/gg per campagna

DATI ULTIMI {days} GIORNI — ACCOUNT OVERVIEW:
- Spend totale:    €{daily.get('spend', 0):.2f}
- Revenue totale:  €{daily.get('revenue', 0):.2f}
- Profitto:        €{daily.get('profit', 0):.2f}
- ROAS:            {daily.get('roas', 0):.2f}
- CPP (cost/acquisto FB): €{daily.get('cpp', 0):.2f}
- AOV (ticket medio GHL): €{daily.get('aov', 0):.2f}
- Ordini totali:   {daily.get('ordini', 0)} (FE: {daily.get('fe_ordini', 0)} | BUMP: {daily.get('bump_ordini', 0)} | OTO: {daily.get('oto_ordini', 0)})
- Bump rate:       {daily.get('bump_rate', 0):.1f}%
- OTO take rate:   {daily.get('oto_rate', 0):.1f}%
- CTR medio:       {daily.get('ctr', 0):.3f}%
- Click totali:    {daily.get('click', 0):,}
- Impressioni:     {daily.get('impressioni', 0):,}
{trend_lines}
CAMPAGNE ATTIVE:
{camps_text}

TOP CREATIVITÀ (per spend, ultimi 14gg):
{ads_text}

PRODOTTI (per revenue):
{prods_text}

---

Analizza i dati e produci un report strutturato con:

1. **STATO ACCOUNT** (1-2 righe): salute generale, segnale principale
2. **AZIONI PRIORITARIE** (max 5, ordinate per impatto): ogni azione deve avere:
   - Priorità: 🔴 URGENTE / 🟡 IMPORTANTE / 🟢 OTTIMIZZAZIONE
   - Titolo breve (max 8 parole)
   - Cosa fare esattamente (concreta, attuabile oggi)
   - Perché (il dato che la motiva)
3. **ANALISI CREATIVE**: quali annunci scalare, quali killare, pattern vincenti
4. **ANALISI FUNNEL**: bump rate e OTO rate sono buoni? cosa ottimizzare
5. **PROSSIMI TEST DA LANCIARE** (2-3 idee concrete basate sui dati)

Sii diretto, concreto, senza introduzioni generiche. Ogni raccomandazione deve essere attuabile entro 24 ore.
Rispondi in italiano."""


# ── Scrittura tab Analisi AI ──────────────────────────────────────────────────

def _write_analysis_tab(ss: Any, analysis_text: str, daily: dict, days: int) -> None:
    tab_name = "Analisi AI"
    try:
        ws = ss.worksheet(tab_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=tab_name, rows=200, cols=4)

    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    # Intestazione
    ws.update("A1:D1", [["🤖 Analisi AI — Mailift Ads Dashboard", "", "", ""]])
    ws.update("A2:D2", [[f"Generata: {now}  |  Periodo analizzato: ultimi {days} giorni", "", "", ""]])
    ws.update("A3:D3", [["", "", "", ""]])

    # KPI summary
    ws.update("A4:D4", [["📊 KPI PERIODO", "Valore", "Target", "Stato"]])
    kpis = [
        ["ROAS",         f"{daily.get('roas', 0):.2f}",         "≥ 2.0",  "✅" if daily.get("roas", 0) >= 2 else "⚠️" if daily.get("roas", 0) >= 1 else "🔴"],
        ["Profitto (€)", f"€{daily.get('profit', 0):.2f}",      "> 0",    "✅" if daily.get("profit", 0) > 0 else "🔴"],
        ["CPP (€)",      f"€{daily.get('cpp', 0):.2f}",         "< AOV",  "✅" if daily.get("cpp", 0) < daily.get("aov", 0) else "🔴"],
        ["AOV (€)",      f"€{daily.get('aov', 0):.2f}",         "—",      "ℹ️"],
        ["Bump Rate",    f"{daily.get('bump_rate', 0):.1f}%",   "≥ 30%",  "✅" if daily.get("bump_rate", 0) >= 30 else "⚠️"],
        ["OTO Take Rate",f"{daily.get('oto_rate', 0):.1f}%",   "≥ 20%",  "✅" if daily.get("oto_rate", 0) >= 20 else "⚠️"],
        ["CTR",          f"{daily.get('ctr', 0):.3f}%",         "≥ 1.0%", "✅" if daily.get("ctr", 0) >= 1 else "⚠️"],
        ["Spend totale", f"€{daily.get('spend', 0):.2f}",       "—",      "ℹ️"],
        ["Revenue totale",f"€{daily.get('revenue', 0):.2f}",   "—",      "ℹ️"],
    ]
    kpi_start = 5
    ws.update(f"A{kpi_start}:D{kpi_start + len(kpis) - 1}", kpis)

    # Spacer
    analysis_start = kpi_start + len(kpis) + 2
    ws.update(f"A{analysis_start - 1}:D{analysis_start - 1}", [["📝 ANALISI & RACCOMANDAZIONI AI", "", "", ""]])

    # Testo analisi — split per righe, max 3 celle unite
    lines = analysis_text.split("\n")
    cell_data = []
    for line in lines:
        cell_data.append([line, "", "", ""])

    if cell_data:
        ws.update(
            f"A{analysis_start}:D{analysis_start + len(cell_data) - 1}",
            cell_data,
        )

    # ── Formattazione via batch_update ────────────────────────────────────────
    sheet_id = ws._properties["sheetId"]

    def _rgb(hex_color: str) -> dict:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return {"red": r/255, "green": g/255, "blue": b/255}

    def _hdr_fmt(row: int, bg: str, fg: str = "#ffffff", size: int = 11, bold: bool = True) -> dict:
        return {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": row-1, "endRowIndex": row, "startColumnIndex": 0, "endColumnIndex": 4},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": _rgb(bg),
                    "textFormat": {"foregroundColor": _rgb(fg), "bold": bold, "fontSize": size},
                    "verticalAlignment": "MIDDLE",
                }},
                "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)",
            }
        }

    def _row_fmt(start_row: int, end_row: int, bg: str) -> dict:
        return {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": start_row-1, "endRowIndex": end_row, "startColumnIndex": 0, "endColumnIndex": 4},
                "cell": {"userEnteredFormat": {"backgroundColor": _rgb(bg)}},
                "fields": "userEnteredFormat(backgroundColor)",
            }
        }

    def _merge(start_row: int, end_row: int) -> dict:
        return {
            "mergeCells": {
                "range": {"sheetId": sheet_id, "startRowIndex": start_row-1, "endRowIndex": end_row, "startColumnIndex": 0, "endColumnIndex": 4},
                "mergeType": "MERGE_ALL",
            }
        }

    def _freeze(rows: int) -> dict:
        return {
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": rows}},
                "fields": "gridProperties.frozenRowCount",
            }
        }

    def _col_width(col_idx: int, px: int) -> dict:
        return {
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": col_idx, "endIndex": col_idx+1},
                "properties": {"pixelSize": px},
                "fields": "pixelSize",
            }
        }

    requests = [
        _merge(1, 1), _hdr_fmt(1, "#1a1a2e", "#ffffff", 13),
        _merge(2, 2), _hdr_fmt(2, "#16213e", "#aaaaaa", 10, False),
        _hdr_fmt(4, "#e94560", "#ffffff", 10),
        _row_fmt(kpi_start, kpi_start + len(kpis), "#f8f9fa"),
        _hdr_fmt(analysis_start - 1, "#16213e", "#ffffff", 11),
        _col_width(0, 500), _col_width(1, 120), _col_width(2, 100), _col_width(3, 80),
        _freeze(1),
    ]

    # KPI row coloring (stato)
    for i, kpi in enumerate(kpis):
        stato = kpi[3]
        bg = OK_COLOR if "✅" in stato else WARN if "⚠️" in stato else URGENT if "🔴" in stato else INFO_BG
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id,
                          "startRowIndex": kpi_start + i - 1,
                          "endRowIndex":   kpi_start + i,
                          "startColumnIndex": 3, "endColumnIndex": 4},
                "cell": {"userEnteredFormat": {"backgroundColor": _rgb(bg)}},
                "fields": "userEnteredFormat(backgroundColor)",
            }
        })

    # Analisi text rows: colora le righe con emoji priorità
    for i, line in enumerate(lines):
        row_idx = analysis_start + i
        bg = None
        if "🔴" in line or "URGENTE" in line:
            bg = URGENT
        elif "🟡" in line or "IMPORTANTE" in line:
            bg = WARN
        elif "🟢" in line or "OTTIMIZZAZIONE" in line:
            bg = OK_COLOR
        elif line.startswith("##") or line.startswith("**"):
            bg = "#e8f4fd"
        if bg:
            requests.append(_row_fmt(row_idx, row_idx, bg))

    ss.batch_update({"requests": requests})
    print(f"  ✓ Tab '{tab_name}' aggiornato ({len(lines)} righe)")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(days: int = 14) -> None:
    if not SPREADSHEET_ID:
        raise RuntimeError("GSHEETS_SPREADSHEET_ID non configurato nel .env")
    if not ANTHROPIC_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY non configurato nel .env")

    print(f"[ads-advisor] Analisi ultimi {days} giorni...")

    # 1. Lettura dati dal foglio
    print("  → Lettura Google Sheet...")
    gc = _gc()
    ss = gc.open_by_key(SPREADSHEET_ID)

    daily_raw   = _get_tab(ss, "Daily Metrics")   if _has_tab(ss, "Daily Metrics")   else []
    camps_raw   = _get_tab(ss, "Campagne")         if _has_tab(ss, "Campagne")         else []
    creative_raw= _get_tab(ss, "Creatività Test")  if _has_tab(ss, "Creatività Test")  else []
    products_raw= _get_tab(ss, "Prodotti")          if _has_tab(ss, "Prodotti")          else []

    daily     = _read_daily(daily_raw, days)
    campaigns = _read_campaigns(camps_raw)
    creatives = _read_creatives(creative_raw)
    products  = _read_products(products_raw)

    if not daily:
        raise RuntimeError("Nessun dato in 'Daily Metrics'. Esegui prima il sync dal foglio.")

    print(f"     {len(campaigns)} campagne | {len(creatives)} creative | {len(products)} prodotti | {daily.get('giorni', 0)} giorni dati")

    # 2. Analisi Claude
    print("  → Analisi AI in corso...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    prompt = _build_prompt(daily, campaigns, creatives, products, days)

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    analysis = message.content[0].text
    print(f"     {len(analysis)} caratteri generati")

    # 3. Scrittura tab
    print("  → Scrittura tab 'Analisi AI'...")
    _write_analysis_tab(ss, analysis, daily, days)

    print(f"\n✅ Analisi completata!")
    print(f"   Apri il foglio → tab 'Analisi AI'")
    print(f"   https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")


def _has_tab(ss: Any, name: str) -> bool:
    return any(ws.title == name for ws in ss.worksheets())


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    try:
        run(days)
    except Exception as e:
        print(f"\n❌ {e}")
        sys.exit(1)
