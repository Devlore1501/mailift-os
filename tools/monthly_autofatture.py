"""
Orchestratore mensile autofatture — eseguito dal scheduler il giorno 10 del mese
oppure manualmente via CLI.

Pipeline:
    1. Scarica transazioni mese precedente da Revolut Business API
    2. Classifica le candidate autofatture con AI
    3. Accorpa per fornitore e crea su Fatture in Cloud (not_sent)
    4. Salva report .tmp/autofatture_YYYY-MM.json
    5. Ritorna un summary dict (usato dallo scheduler per la notifica Telegram)

Idempotenza: se il CSV del mese è già in inbox/processed/ o il report JSON
esiste già, lo script lo segnala e non ripete la creazione.

Esecuzione CLI:
    python tools/monthly_autofatture.py              # esegue per il mese scorso
    python tools/monthly_autofatture.py --dry-run    # anteprima senza FiC
    python tools/monthly_autofatture.py --force      # riesegue anche se report esiste
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.revolut_client import download_previous_month, get_previous_month_range
from tools.parse_bank_statement import parse_statement
from tools.classify_transactions import classify
from tools.fic_client import AutofatturaInput, AutofatturaLine, FicClient


def _period_label(dates: list[date]) -> str:
    if not dates:
        return ""
    lo, hi = min(dates), max(dates)
    if lo == hi:
        return lo.strftime("%d/%m/%Y")
    if lo.month == hi.month and lo.year == hi.year:
        return lo.strftime("%B %Y")
    return f"{lo.strftime('%d/%m/%Y')} – {hi.strftime('%d/%m/%Y')}"


def _to_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _group_candidates(candidates: list[dict]) -> list[AutofatturaInput]:
    """Accorpa per (fornitore, type_doc, valuta) → 1 autofattura per gruppo."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for c in candidates:
        src = c.get("source_transaction") or {}
        key = (
            (c.get("supplier_name") or "").strip().lower(),
            c.get("type_doc"),
            src.get("currency", "EUR"),
        )
        groups[key].append(c)

    today = date.today()
    result: list[AutofatturaInput] = []
    for (_name_lower, type_doc, currency), items in groups.items():
        items_sorted = sorted(
            items,
            key=lambda i: (i.get("source_transaction") or {}).get("date", ""),
        )
        dates = [
            _to_date(i["source_transaction"]["date"])
            for i in items_sorted
            if i.get("source_transaction") and i["source_transaction"].get("date")
        ]
        first = items_sorted[0]
        ref_src = first.get("source_transaction") or {}
        ref_date = dates[0] if dates else today
        ref_num = (
            (ref_src.get("id") or "")[:50]
            if isinstance(ref_src.get("id"), str)
            else f"{ref_src.get('date','')}-{first.get('supplier_name','')[:20]}"
        )
        total_net = sum(
            abs(float((i.get("source_transaction") or {}).get("amount", 0)))
            for i in items_sorted
        )
        desc = first.get("description", first.get("supplier_name", "Servizio")) or "Servizio"
        line = AutofatturaLine(
            description=desc,
            amount_net=round(total_net, 2),
            vat_rate=float(first.get("vat_rate", 22)),
        )
        result.append(
            AutofatturaInput(
                type_doc=type_doc,
                supplier_name=first["supplier_name"],
                supplier_country=first.get("supplier_country", ""),
                supplier_vat_number=first.get("supplier_vat_number", ""),
                invoice_date=today,
                period_label=_period_label(dates),
                lines=[line],
                ref_invoice_number=ref_num,
                ref_invoice_date=ref_date,
                currency=currency,
            )
        )
    return result


def run(dry_run: bool = False, force: bool = False) -> dict:
    """Esegue la pipeline completa. Ritorna un summary dict.

    Returns:
        {
            "month": "maggio 2026",
            "month_key": "2026-05",
            "created": 7,
            "skipped": 0,
            "errors": [...],
            "already_done": True/False,
            "dry_run": True/False,
            "report_path": "...",
        }
    """
    from_dt, _ = get_previous_month_range()
    month_key = from_dt.strftime("%Y-%m")
    month_label = from_dt.strftime("%B %Y")

    report_path = ROOT / ".tmp" / f"autofatture_{month_key}.json"
    csv_path = ROOT / "inbox" / f"revolut_{month_key}.csv"
    processed_path = ROOT / "inbox" / "processed" / f"revolut_{month_key}.csv"

    # Idempotenza: se report esiste già e non --force, esci
    if report_path.exists() and not force:
        print(f"[monthly] Report {report_path} già esiste. Usa --force per rieseguire.")
        existing = json.loads(report_path.read_text())
        ok_count = sum(1 for r in existing if r.get("status") == "ok")
        return {
            "month": month_label,
            "month_key": month_key,
            "created": ok_count,
            "skipped": 0,
            "errors": [],
            "already_done": True,
            "dry_run": dry_run,
            "report_path": str(report_path),
        }

    # Step 1: scarica CSV da Revolut (a meno che non esista già)
    if csv_path.exists():
        print(f"[monthly] CSV già presente: {csv_path}")
    elif processed_path.exists():
        csv_path = processed_path
        print(f"[monthly] CSV già processato: {csv_path}")
    else:
        csv_path, _ = download_previous_month(ROOT / "inbox")

    # Step 2: parsing
    print(f"[monthly] Parsing {csv_path}...")
    transactions = parse_statement(csv_path)
    outflows = [t for t in transactions if t["amount"] < 0]
    print(f"[monthly] {len(transactions)} transazioni, {len(outflows)} uscite.")

    # Step 3: classificazione AI
    print("[monthly] Classificazione AI...")
    candidates = classify(outflows)
    candidates = [c for c in candidates if c.get("confidence") in ("medium", "high")]
    print(f"[monthly] {len(candidates)} candidate autofatture.")

    # Step 4: accorpamento
    grouped = _group_candidates(candidates)
    print(f"[monthly] → {len(grouped)} autofatture da creare.")

    if not grouped:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps([], ensure_ascii=False, indent=2))
        return {
            "month": month_label,
            "month_key": month_key,
            "created": 0,
            "skipped": 0,
            "errors": [],
            "already_done": False,
            "dry_run": dry_run,
            "report_path": str(report_path),
        }

    # Step 5: dry-run o creazione FiC
    report: list[dict] = []
    errors: list[str] = []

    if dry_run:
        for af in grouped:
            report.append({
                "status": "dry_run",
                "supplier": af.supplier_name,
                "type_doc": af.type_doc,
                "total_net": af.total_net,
                "currency": af.currency,
            })
        print(f"[monthly] dry-run: {len(grouped)} autofatture simulate (nessuna FiC).")
    else:
        client = FicClient()
        for af in grouped:
            try:
                created = client.create_self_supplier_invoice(af)
                print(
                    f"  OK → {created.get('number')}/{created.get('numeration','')} "
                    f"{af.supplier_name} ({af.total_net:.2f} {af.currency})"
                )
                report.append({
                    "status": "ok",
                    "supplier": af.supplier_name,
                    "type_doc": af.type_doc,
                    "total_net": af.total_net,
                    "currency": af.currency,
                    "result": {
                        "id": created.get("id"),
                        "number": created.get("number"),
                        "numeration": created.get("numeration"),
                    },
                })
            except Exception as e:
                print(f"  ERRORE ({af.supplier_name}): {e}")
                errors.append(f"{af.supplier_name}: {e}")
                report.append({
                    "status": "error",
                    "supplier": af.supplier_name,
                    "error": str(e),
                })

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    # Sposta il CSV in processed/
    if not dry_run and csv_path == ROOT / "inbox" / f"revolut_{month_key}.csv":
        processed_dir = ROOT / "inbox" / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        csv_path.rename(processed_dir / csv_path.name)
        print(f"[monthly] CSV spostato in processed/.")

    ok_count = sum(1 for r in report if r["status"] == "ok")
    return {
        "month": month_label,
        "month_key": month_key,
        "created": ok_count,
        "skipped": len(report) - ok_count - len(errors),
        "errors": errors,
        "already_done": False,
        "dry_run": dry_run,
        "report_path": str(report_path),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Pipeline mensile autofatture Revolut → FiC")
    ap.add_argument("--dry-run", action="store_true", help="Simula senza creare su FiC")
    ap.add_argument("--force", action="store_true", help="Riesegui anche se il report esiste già")
    args = ap.parse_args()

    summary = run(dry_run=args.dry_run, force=args.force)

    print(f"\n{'='*50}")
    print(f"Mese: {summary['month']}")
    if summary["already_done"]:
        print(f"✅ Già eseguito (trovato report esistente). --force per rieseguire.")
    elif summary["dry_run"]:
        print(f"🔍 Dry-run: {summary['created']} autofatture simulate.")
    else:
        print(f"✅ Autofatture create: {summary['created']}")
    if summary["errors"]:
        print(f"❌ Errori ({len(summary['errors'])}):")
        for e in summary["errors"]:
            print(f"   • {e}")
    print(f"Report: {summary['report_path']}")
    return 0 if not summary["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
