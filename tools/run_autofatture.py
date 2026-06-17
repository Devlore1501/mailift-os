"""
Orchestratore end-to-end:

    1. Parsea l'estratto conto (PDF/CSV/XLSX)
    2. Classifica le candidate autofatture con AI
    3. ACCORPA per fornitore in UN'UNICA RIGA per autofattura
       (es. 11 addebiti Facebook Ads -> 1 fattura con 1 riga aggregata)
    4. Crea su Fatture in Cloud:
       - data documento = data odierna (per evitare ritardi sanzionabili)
       - sezionale "a" (configurabile via FIC_NUMERATION)
       - e_invoice=true ma NON firmata/inviata: l'utente la rivede e invia da UI
    5. Scrive un report .tmp/autofatture_report.json

Esempi:
    python tools/run_autofatture.py inbox/estratto.csv --dry-run
    python tools/run_autofatture.py inbox/estratto.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from parse_bank_statement import parse_statement
from classify_transactions import classify
from fic_client import AutofatturaInput, AutofatturaLine, FicClient


def _to_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _period_label(dates: list[date]) -> str:
    if not dates:
        return ""
    lo, hi = min(dates), max(dates)
    if lo == hi:
        return lo.strftime("%d/%m/%Y")
    if lo.month == hi.month and lo.year == hi.year:
        return lo.strftime("%B %Y")
    return f"{lo.strftime('%d/%m/%Y')} - {hi.strftime('%d/%m/%Y')}"


def group_candidates(candidates: list[dict]) -> list[AutofatturaInput]:
    """Accorpa per (fornitore_normalizzato, type_doc, valuta) e produce
    una autofattura con UNA SOLA riga per ciascun gruppo.

    invoice_date = data odierna (per evitare ritardi sanzionabili).
    ref_invoice_number/ref_invoice_date = dati del primo addebito del periodo,
    usati come riferimento DatiFattureCollegate (campo SDI 2.1.6).
    """
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
        first = items[0]
        # Ordina cronologicamente per estrarre il primo addebito come "fattura di riferimento"
        items_sorted = sorted(
            items,
            key=lambda i: (i.get("source_transaction") or {}).get("date", ""),
        )
        dates = [
            _to_date(i["source_transaction"]["date"])
            for i in items_sorted
            if i.get("source_transaction") and i["source_transaction"].get("date")
        ]

        ref_src = items_sorted[0].get("source_transaction") or {}
        ref_invoice_date = dates[0] if dates else today
        # Best-effort: usa l'id transazione (Revolut "ID") o un descrittore
        ref_invoice_number = (
            (ref_src.get("id") or "")[:50]
            if isinstance(ref_src.get("id"), str)
            else f"{ref_src.get('date','')}-{first.get('supplier_name','')[:20]}"
        )

        # Una sola riga aggregata, descrizione NEUTRA (no date, no conteggio addebiti)
        total_net = sum(abs(float((i.get("source_transaction") or {}).get("amount", 0))) for i in items_sorted)
        period = _period_label(dates)
        neutral_desc = first.get("description", first.get("supplier_name", "Servizio")) or "Servizio"

        line = AutofatturaLine(
            description=neutral_desc,
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
                period_label=period,
                lines=[line],
                ref_invoice_number=ref_invoice_number,
                ref_invoice_date=ref_invoice_date,
                currency=currency,
            )
        )
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("statement", type=Path, help="PDF / CSV / XLSX dell'estratto conto")
    ap.add_argument("--dry-run", action="store_true", help="Non chiama FiC, salva solo il piano")
    ap.add_argument("--min-confidence", choices=["low", "medium", "high"], default="medium")
    args = ap.parse_args()

    print(f"[1/4] Parsing {args.statement}...")
    transactions = parse_statement(args.statement)
    outflows = [t for t in transactions if t["amount"] < 0]
    print(f"      {len(transactions)} movimenti totali, {len(outflows)} in uscita")

    print("[2/4] Classificazione AI dei movimenti...")
    candidates = classify(outflows)
    levels = {"low": 0, "medium": 1, "high": 2}
    candidates = [
        c for c in candidates
        if levels.get(c.get("confidence", "low"), 0) >= levels[args.min_confidence]
    ]
    print(f"      {len(candidates)} righe candidate (>= {args.min_confidence})")

    print("[3/4] Accorpamento per fornitore (1 riga per autofattura)...")
    grouped = group_candidates(candidates)
    print(f"      -> {len(grouped)} autofatture da creare")
    if not grouped:
        print("Nessuna autofattura da emettere.")
        return 0

    for i, af in enumerate(grouped, 1):
        line = af.lines[0]
        print(
            f"  [{i}] {af.type_doc} | {af.supplier_name} ({af.supplier_country}) | "
            f"data={af.invoice_date} | totale {af.total_net:.2f} {af.currency}"
        )
        print(f"         line: {line.description[:120]}  {line.amount_net:.2f}")
        print(f"         ref:  invoice_number={af.ref_invoice_number[:30]}  invoice_date={af.ref_invoice_date}")

    if args.dry_run:
        out = Path(".tmp/autofatture_plan.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        plan = [
            {
                "type_doc": af.type_doc,
                "supplier_name": af.supplier_name,
                "supplier_country": af.supplier_country,
                "supplier_vat_number": af.supplier_vat_number,
                "invoice_date": af.invoice_date.isoformat(),
                "period_label": af.period_label,
                "currency": af.currency,
                "total_net": af.total_net,
                "ref_invoice_number": af.ref_invoice_number,
                "ref_invoice_date": af.ref_invoice_date.isoformat() if af.ref_invoice_date else None,
                "line": vars(af.lines[0]),
            }
            for af in grouped
        ]
        out.write_text(json.dumps(plan, ensure_ascii=False, indent=2))
        print(f"\n[dry-run] Piano salvato in {out}. Nessuna chiamata a FiC.")
        return 0

    print("\n[4/4] Creazione su Fatture in Cloud...")
    client = FicClient()
    report: list[dict] = []
    for i, af in enumerate(grouped, 1):
        try:
            created = client.create_self_supplier_invoice(af)
            print(
                f"  [{i}] OK -> id={created.get('id')} "
                f"num={created.get('number')}/{created.get('numeration','')}  ({af.supplier_name})"
            )
            report.append({
                "status": "ok",
                "supplier": af.supplier_name,
                "type_doc": af.type_doc,
                "total_net": af.total_net,
                "result": {
                    "id": created.get("id"),
                    "number": created.get("number"),
                    "numeration": created.get("numeration"),
                },
            })
        except Exception as e:
            print(f"  [{i}] ERRORE ({af.supplier_name}): {e}")
            report.append({
                "status": "error",
                "supplier": af.supplier_name,
                "error": str(e),
            })

    out = Path(".tmp/autofatture_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    ok = sum(1 for r in report if r["status"] == "ok")
    print(f"\nFatto: {ok}/{len(report)} autofatture create. Report -> {out}")
    print(
        "NB: sono NON inviate al SDI. Vai su Fatture in Cloud, "
        "rivedi e clicca 'Verifica formale' + 'Firma e invia' per ciascuna."
    )
    return 0 if ok == len(report) else 1


if __name__ == "__main__":
    sys.exit(main())
