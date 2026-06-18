"""reengagement_radar.py — Radar prospect non chiusi: legge i trigger di riapertura dai README e segnala chi contattare.

Ogni README prospect può avere una sezione:
  ## Trigger di riapertura
  **Blocco originale:** ...
  **Tipo trigger:** data | evento-esterno | stagionalità | case-study | time-based
  **Condizione:** ...
  **Data reminder:** YYYY-MM-DD   (solo per trigger tipo 'data', 'stagionalità', 'time-based')
  **Messaggio suggerito:** ...

Usage:
    python tools/reengagement_radar.py              # mostra prospect da contattare oggi (±30gg)
    python tools/reengagement_radar.py --all        # mostra tutti i trigger indipendentemente dalla data
    python tools/reengagement_radar.py --days 60    # finestra ±60 giorni
"""

from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SKIP_FOLDERS = {"_mailift-team"}
RETAINER_STATI = {"retainer attivo", "retainer", "ex cliente", "non attivo"}

TODAY = date.today()


def parse_trigger(text: str) -> dict | None:
    """Estrae la sezione ## Trigger di riapertura da un README."""
    m = re.search(r"## Trigger di riapertura\n(.*?)(?:\n##|\Z)", text, re.S)
    if not m:
        return None

    block = m.group(1)

    def field(name: str) -> str:
        fm = re.search(rf"\*\*{re.escape(name)}:?\*\*:?\s*(.+?)(?:\n|$)", block, re.I)
        return fm.group(1).strip() if fm else ""

    blocco = field("Blocco originale")
    tipo = field("Tipo trigger").lower()
    condizione = field("Condizione")
    data_str = field("Data reminder")
    messaggio = field("Messaggio suggerito")

    data_reminder = None
    if data_str:
        try:
            data_reminder = datetime.strptime(data_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            pass

    return {
        "blocco": blocco,
        "tipo": tipo,
        "condizione": condizione,
        "data_reminder": data_reminder,
        "messaggio": messaggio,
    }


def parse_stato(text: str) -> str:
    m = re.search(r"\*\*Stato\*\*:?\s*(.+?)(?:\n|$)", text, re.I)
    if not m:
        m = re.search(r"\|\s*\*\*Stato\*\*\s*\|\s*(.+?)\s*\|", text, re.I)
    return m.group(1).strip() if m else ""


def days_until(d: date) -> int:
    return (d - TODAY).days


def urgency_label(days: int) -> str:
    if days < 0:
        return f"⚠️  SCADUTO ({-days}gg fa)"
    if days == 0:
        return "🔴 OGGI"
    if days <= 7:
        return f"🔴 {days}gg"
    if days <= 21:
        return f"🟠 {days}gg"
    if days <= 60:
        return f"🟡 {days}gg"
    return f"🟢 {days}gg"


def scan_clients(window_days: int = 30, show_all: bool = False) -> list[dict]:
    clients_dir = PROJECT_ROOT / "clients"
    results = []

    for folder in sorted(clients_dir.iterdir()):
        if not folder.is_dir() or folder.name in SKIP_FOLDERS:
            continue
        readme = folder / "README.md"
        if not readme.exists():
            continue

        text = readme.read_text(encoding="utf-8")

        # Skip retainer / ex clienti (non sono prospect da ricontattare)
        stato = parse_stato(text).lower()
        if any(s in stato for s in RETAINER_STATI):
            continue

        trigger = parse_trigger(text)
        if not trigger:
            continue

        # Determina se è nella finestra
        d = trigger["data_reminder"]
        if d:
            days = days_until(d)
            in_window = show_all or (days <= window_days)
        else:
            # Trigger senza data (evento-esterno, case-study) → mostra sempre se --all, altrimenti includi
            days = None
            in_window = show_all or True  # sempre visibili (non hanno scadenza)

        if not in_window:
            continue

        # Titolo H1
        title_m = re.search(r"^#\s+(.+)$", text, re.M)
        nome = title_m.group(1).strip() if title_m else folder.name

        results.append({
            "folder": folder.name,
            "nome": nome,
            "stato": stato,
            "trigger": trigger,
            "days": days,
        })

    # Sort: prima quelli con data (per urgency), poi quelli senza
    results.sort(key=lambda r: (r["days"] is None, r["days"] if r["days"] is not None else 9999))
    return results


def print_report(results: list[dict], window_days: int) -> None:
    print(f"\n{'='*60}")
    print(f"  REENGAGEMENT RADAR — {TODAY.strftime('%d %b %Y')}")
    print(f"  Finestra: prossimi {window_days} giorni")
    print(f"{'='*60}\n")

    if not results:
        print("  Nessun prospect nella finestra. Tutto a posto.\n")
        return

    date_based = [r for r in results if r["days"] is not None]
    no_date = [r for r in results if r["days"] is None]

    if date_based:
        print("📅 TRIGGER CON DATA\n")
        for r in date_based:
            t = r["trigger"]
            days = r["days"]
            label = urgency_label(days)
            print(f"  {label}  —  {r['nome']}  [{r['folder']}]")
            print(f"    Data reminder: {t['data_reminder']}")
            print(f"    Blocco: {t['blocco']}")
            print(f"    Condizione: {t['condizione']}")
            print(f"    Messaggio: \"{t['messaggio']}\"")
            print()

    if no_date:
        print("📌 TRIGGER SENZA DATA (evento / case-study)\n")
        for r in no_date:
            t = r["trigger"]
            print(f"  •  {r['nome']}  [{r['folder']}]")
            print(f"    Tipo: {t['tipo']}")
            print(f"    Blocco: {t['blocco']}")
            print(f"    Condizione: {t['condizione']}")
            print(f"    Messaggio: \"{t['messaggio']}\"")
            print()

    total_urgent = sum(1 for r in date_based if r["days"] is not None and r["days"] <= 7)
    print(f"{'='*60}")
    print(f"  Totale prospect: {len(results)}  |  Urgenti (≤7gg): {total_urgent}")
    print(f"{'='*60}\n")


def main() -> None:
    args = sys.argv[1:]
    show_all = "--all" in args

    window_days = 30
    for i, a in enumerate(args):
        if a == "--days" and i + 1 < len(args):
            try:
                window_days = int(args[i + 1])
            except ValueError:
                pass

    results = scan_clients(window_days=window_days, show_all=show_all)
    print_report(results, window_days)


if __name__ == "__main__":
    main()
