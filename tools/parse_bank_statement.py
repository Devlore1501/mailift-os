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


# ---------------------------------------------------------------------------
# Revolut Business - export PDF in italiano, multi-conto
#
# Layout: "23 ago 2026 CAR Manychat.com €14.55 €1 579.06", con tre colonne di
# importi allineate a destra (uscita / entrata / saldo). Dal solo testo le
# colonne sono indistinguibili (una riga ha sempre due numeri: movimento +
# saldo), quindi la colonna va dedotta dalle coordinate x. Il parser verifica
# poi la catena dei saldi: se delta_saldo != importo la riga e' sbagliata.
# Vedi workflows/emit_autofatture.md, sessione 2026-11-19.
# ---------------------------------------------------------------------------
_IT_MONTHS = {"gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
              "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12}
_REV_DATE_RE = re.compile(
    r"^(\d{1,2}) (gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic) (\d{4})$")
_CUR_SYM = {"\u20ac": "EUR", "$": "USD", "\u00a3": "GBP"}
_REV_NUM_RE = re.compile(r"^[\u20ac$\u00a3]?-?[\d\s]*\d(?:[.,]\d{2})?$")

# x1 del token finale del numero: <=408 uscita, <=485 entrata, oltre = saldo.
_REV_OUT_MAX, _REV_IN_MAX = 408.0, 485.0
# Le continuazioni di descrizione stanno nella colonna descrizione (x0~175);
# footer e riepiloghi stanno a x0<=72 o x0>=190.
_REV_CONT_X0 = (170.0, 186.0)
# Righe di footer/riepilogo da non confondere con una continuazione di descrizione.
_REV_TABLE_END = ("Segnala carta come smarrita", "Tipi di transazione",
                  "Non ci sono state transazioni", "Documento informativo",
                  "Per maggiori informazioni")


def _rev_visual_rows(page):
    lines: dict[int, list] = {}
    for w in page.extract_words(use_text_flow=False):
        lines.setdefault(round(w["top"] / 3.0), []).append(w)
    return [sorted(ws, key=lambda w: w["x0"]) for _, ws in sorted(lines.items())]


def _rev_merge_amounts(ws: list[dict]) -> list[dict]:
    """Riunisce i token di un importo con separatore migliaia ('\u20ac2' + '600.00')."""
    out, i = [], 0
    while i < len(ws):
        w = dict(ws[i])
        if w["text"][:1] in _CUR_SYM:
            j = i + 1
            while j < len(ws) and re.fullmatch(r"\d{3}(?:[.,]\d{2})?", ws[j]["text"]):
                w["text"] += " " + ws[j]["text"]
                w["x1"] = ws[j]["x1"]
                j += 1
            out.append(w)
            i = j
        else:
            out.append(w)
            i += 1
    return out


def _rev_amount(token: str) -> tuple[float | None, str]:
    sym = token[:1] if token[:1] in _CUR_SYM else None
    body = (token[1:] if sym else token).replace(" ", "").replace(",", "")
    try:
        return float(body), _CUR_SYM.get(sym, "EUR")
    except ValueError:
        return None, "EUR"


def is_revolut_it_pdf(path: Path) -> bool:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        head = (pdf.pages[0].extract_text() or "")
    return "Data (UTC) Descrizione" in head and "Fondi in uscita" in head


def parse_revolut_it_pdf(path: Path) -> list[dict[str, Any]]:
    import pdfplumber

    txns: list[dict[str, Any]] = []
    account, currency, in_table = None, "EUR", False
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for ws in _rev_visual_rows(page):
                text = " ".join(w["text"] for w in ws)
                if "Nome del conto" in text:
                    account = text.split("Nome del conto", 1)[1].strip()
                    in_table = False
                    continue
                m = re.search(r"\bValuta ([A-Z]{3})\b", text)
                if m:
                    currency = m.group(1)
                if text.startswith("Data (UTC) Descrizione"):
                    in_table = True
                    continue
                if not in_table:
                    continue
                ws = _rev_merge_amounts(ws)
                dm = _REV_DATE_RE.match(" ".join(w["text"] for w in ws[:3]))
                if not dm:
                    x0 = ws[0]["x0"] if ws else 0
                    is_noise = any(k in text for k in _REV_TABLE_END)
                    if (txns and not is_noise
                            and _REV_CONT_X0[0] <= x0 <= _REV_CONT_X0[1]):
                        txns[-1]["description"] += " " + text.strip()
                    continue
                date = f"{dm.group(3)}-{_IT_MONTHS[dm.group(2)]:02d}-{int(dm.group(1)):02d}"

                outflow = inflow = balance = None
                desc_tok: list[str] = []
                for w in ws[3:]:
                    if w["text"][:1] in _CUR_SYM and _REV_NUM_RE.match(w["text"]):
                        val, _ = _rev_amount(w["text"])
                        if val is not None:
                            if w["x1"] <= _REV_OUT_MAX:
                                outflow = val
                            elif w["x1"] <= _REV_IN_MAX:
                                inflow = val
                            else:
                                balance = val
                            continue
                    desc_tok.append(w["text"])
                if outflow is None and inflow is None:
                    continue

                code = None
                if desc_tok and re.fullmatch(r"[A-Z]{3}", desc_tok[0]):
                    code, desc_tok = desc_tok[0], desc_tok[1:]

                txns.append({
                    "date": date,
                    "amount": round(-outflow if outflow is not None else inflow, 2),
                    "currency": currency,
                    "description": " ".join(desc_tok).strip(),
                    "account": account,
                    "code": code,
                    "balance": balance,
                    "raw": text,
                })
    return txns


def validate_balance_chain(txns: list[dict[str, Any]]) -> tuple[int, list[str]]:
    """Controlla che delta_saldo == importo su righe consecutive dello stesso conto.

    Le righe sono ordinate dal movimento piu' recente, quindi il saldo della
    riga precedente meno quello della successiva deve dare l'importo.
    Ritorna (coppie_verificate, lista_errori).
    """
    by_acct: dict[tuple, list] = {}
    for t in txns:
        by_acct.setdefault((t.get("account"), t.get("currency")), []).append(t)
    checked, errors = 0, []
    for rows in by_acct.values():
        for cur, nxt in zip(rows, rows[1:]):
            if cur.get("balance") is None or nxt.get("balance") is None:
                continue
            checked += 1
            delta = round(cur["balance"] - nxt["balance"], 2)
            if abs(delta - cur["amount"]) > 0.015:
                errors.append(
                    f"{cur['date']} {cur['description'][:40]!r}: "
                    f"importo {cur['amount']:.2f} ma delta saldo {delta:.2f}")
    return checked, errors


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
        if is_revolut_it_pdf(path):
            return parse_revolut_it_pdf(path)
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
    if any("balance" in r for r in rows):
        checked, errors = validate_balance_chain(rows)
        print(f"Catena saldi: {checked} coppie verificate, {len(errors)} incoerenze")
        for e in errors[:10]:
            print(f"  [!] {e}")
    if args.only_outflows:
        rows = [r for r in rows if r["amount"] < 0]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"Estratte {len(rows)} transazioni -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
