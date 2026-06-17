"""
Parser estratti conto bancari -> lista normalizzata di transazioni.

Supporta:
    - PDF (testuale, non scansionato) tramite pdfplumber
    - CSV / XLS / XLSX tramite pandas

Output uniforme:
    [
        {
            "date": "2026-03-15",        # ISO
            "amount": -123.45,            # negativo = uscita
            "currency": "EUR",
            "description": "ADDEBITO SEPA GOOGLE IRELAND LTD ...",
            "raw": "...riga originale per debug..."
        },
        ...
    ]

Solo le uscite (amount < 0) sono rilevanti per l'autofattura passiva.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

DATE_PATTERNS = [
    ("%d/%m/%Y", re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")),
    ("%d-%m-%Y", re.compile(r"\b(\d{2}-\d{2}-\d{4})\b")),
    ("%Y-%m-%d", re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")),
    ("%d/%m/%y", re.compile(r"\b(\d{2}/\d{2}/\d{2})\b")),
]
AMOUNT_RE = re.compile(r"-?\d{1,3}(?:[\.\s]\d{3})*,\d{2}|-?\d+\.\d{2}")


def _parse_date(s: str) -> str | None:
    for fmt, pat in DATE_PATTERNS:
        m = pat.search(s)
        if m:
            try:
                return datetime.strptime(m.group(1), fmt).date().isoformat()
            except ValueError:
                continue
    return None


def _parse_amount(s) -> float | None:
    # Caso 1: è già un numero (pandas legge i CSV con Amount come float)
    if isinstance(s, (int, float)):
        try:
            f = float(s)
            return f if f == f else None  # esclude NaN
        except (TypeError, ValueError):
            return None
    s = str(s)
    # Caso 2: prova un parse "puro" (solo numero, anche senza 2 cifre decimali)
    try:
        return float(s.strip().replace(" ", ""))
    except ValueError:
        pass
    # Caso 3: regex su testo libero (estratti conto in formato italiano "1.234,56" o inglese)
    m = AMOUNT_RE.findall(s)
    if not m:
        return None
    raw = m[-1]
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(".", "").replace(" ", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def parse_pdf(path: Path) -> list[dict[str, Any]]:
    import pdfplumber  # lazy import

    rows: list[dict[str, Any]] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            # Prova prima con extract_tables (estratti conto strutturati)
            for table in page.extract_tables() or []:
                for row in table:
                    cells = [c or "" for c in row]
                    line = " | ".join(cells).strip()
                    if not line:
                        continue
                    d = _parse_date(line)
                    a = _parse_amount(line)
                    if d and a is not None:
                        rows.append({
                            "date": d,
                            "amount": a,
                            "currency": "EUR",
                            "description": " ".join(c for c in cells if c).strip(),
                            "raw": line,
                        })
            # Fallback: linee di testo
            text = page.extract_text() or ""
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                d = _parse_date(line)
                a = _parse_amount(line)
                if d and a is not None and not any(r["raw"] == line for r in rows):
                    rows.append({
                        "date": d,
                        "amount": a,
                        "currency": "EUR",
                        "description": line,
                        "raw": line,
                    })
    return rows


def parse_tabular(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, sep=None, engine="python")
    else:
        df = pd.read_excel(path)

    cols = {c.lower().strip(): c for c in df.columns}

    def find(*candidates: str) -> str | None:
        for c in candidates:
            if c in cols:
                return cols[c]
        for key, orig in cols.items():
            for c in candidates:
                if c in key:
                    return orig
        return None

    date_col = find("date completed", "data operazione", "data valuta", "data", "date")
    desc_col = find("descrizione", "description", "causale", "operazione")
    amount_col = find("amount", "importo", "dare/avere")
    debit_col = find("dare", "uscite", "debit", "addebiti")
    credit_col = find("avere", "entrate", "credit", "accrediti")
    currency_col = find("payment currency", "divisa", "valuta", "currency")

    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        raw_line = " | ".join(str(v) for v in r.values if pd.notna(v))
        d = None
        if date_col and pd.notna(r[date_col]):
            raw_date = str(r[date_col])
            # Format ISO YYYY-MM-DD: parsalo esplicitamente, non con dayfirst (pandas lo swapperebbe)
            if re.match(r"^\d{4}-\d{2}-\d{2}", raw_date):
                try:
                    d = pd.to_datetime(raw_date, format="%Y-%m-%d", errors="raise").date().isoformat()
                except Exception:
                    d = _parse_date(raw_date)
            else:
                try:
                    d = pd.to_datetime(r[date_col], dayfirst=True).date().isoformat()
                except Exception:
                    d = _parse_date(raw_date)
        if not d:
            d = _parse_date(raw_line)
        if not d:
            continue

        amount: float | None = None
        if amount_col and pd.notna(r[amount_col]):
            amount = _parse_amount(str(r[amount_col]))
        elif debit_col or credit_col:
            deb = _parse_amount(str(r[debit_col])) if debit_col and pd.notna(r[debit_col]) else None
            cre = _parse_amount(str(r[credit_col])) if credit_col and pd.notna(r[credit_col]) else None
            if deb is not None:
                amount = -abs(deb)
            elif cre is not None:
                amount = abs(cre)
        if amount is None:
            amount = _parse_amount(raw_line)
        if amount is None:
            continue

        desc = str(r[desc_col]) if desc_col and pd.notna(r[desc_col]) else raw_line
        currency = str(r[currency_col]) if currency_col and pd.notna(r[currency_col]) else "EUR"

        rows.append({
            "date": d,
            "amount": amount,
            "currency": currency.strip().upper()[:3] or "EUR",
            "description": desc.strip(),
            "raw": raw_line,
        })
    return rows


def parse_statement(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix in {".csv", ".xls", ".xlsx"}:
        return parse_tabular(path)
    raise ValueError(f"Formato non supportato: {suffix}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, default=Path(".tmp/transactions.json"))
    ap.add_argument("--only-outflows", action="store_true", help="Solo movimenti negativi")
    args = ap.parse_args()

    rows = parse_statement(args.input)
    if args.only_outflows:
        rows = [r for r in rows if r["amount"] < 0]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"Estratte {len(rows)} transazioni -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
