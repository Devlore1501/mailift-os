"""
Preparazione deterministica dei movimenti prima della classificazione AI.

Toglie dagli addebiti tutto cio' che NON e' un acquisto da autofatturare, senza
spendere chiamate Anthropic e senza margine di interpretazione:

  - giroconti tra conti Revolut della stessa societa' ("A LOD operativo" /
    "Da Main"): spostano soldi, non comprano niente
  - addebiti rimborsati per intero nello stesso estratto ("Rimborso da parte di
    X" con stesso importo e stesso esercente): l'operazione e' annullata, niente
    autofattura

I rimborsi che non trovano l'addebito originale nell'estratto (es. Apple €26,12
di agosto su un addebito gia' autofatturato a luglio) NON si compensano: servono
una nota di variazione, da far valutare al commercialista. Vengono restituiti a
parte come `orphan_refunds`.

Usage:
    python tools/autofatture_prep.py .tmp/txns.json        # stampa il riepilogo
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_REFUND_RE = re.compile(r"^\s*(rimborso da parte di|refund from)\s+", re.I)
_TRANSFER_RE = re.compile(r"^\s*(a|da|to|from)\s+(.+?)\s*$", re.I)
_STOPWORDS = {
    "inc", "ltd", "llc", "srl", "gmbh", "the", "com", "www", "tasso", "eur",
    "usd", "gbp", "commissione", "subscr", "subscription", "technology",
    "technologies", "limited", "company", "payment", "pagamento",
}


def _tokens(text: str) -> set[str]:
    text = re.split(r"\btasso fx\b|•", text.lower())[0]
    return {t for t in re.findall(r"[a-z0-9]{3,}", text) if t not in _STOPWORDS}


def _account_names(txns: list[dict]) -> set[str]:
    return {(t.get("account") or "").strip().lower() for t in txns if t.get("account")}


def _is_internal_transfer(t: dict, accounts: set[str]) -> bool:
    m = _TRANSFER_RE.match(t.get("description") or "")
    return bool(m and m.group(2).strip().lower() in accounts)


def prepare(txns: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Ritorna {outflows, excluded, orphan_refunds}.

    - outflows: addebiti da passare al classificatore
    - excluded: addebiti tolti, ognuno con `exclude_reason` e (per i rimborsi)
      `refund` = movimento di rimborso che lo annulla
    - orphan_refunds: rimborsi senza addebito corrispondente nell'estratto
    """
    accounts = _account_names(txns)
    excluded: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for t in txns:
        if t.get("amount", 0) >= 0:
            continue
        if _is_internal_transfer(t, accounts):
            excluded.append({**t, "exclude_reason": "giroconto interno"})
        else:
            candidates.append(t)

    refunds = [
        t for t in txns
        if t.get("amount", 0) > 0 and _REFUND_RE.match(t.get("description") or "")
    ]
    # I rimborsi piu' vecchi si abbinano per primi, ognuno all'addebito
    # precedente piu' recente con stesso importo ed esercente compatibile.
    refunds.sort(key=lambda r: r["date"])
    matched: set[int] = set()
    orphans: list[dict[str, Any]] = []
    for r in refunds:
        merchant = _tokens(_REFUND_RE.sub("", r["description"]))
        best = None
        for i, t in enumerate(candidates):
            if i in matched or t["date"] > r["date"]:
                continue
            if t.get("currency") != r.get("currency"):
                continue
            if abs(abs(t["amount"]) - r["amount"]) > 0.005:
                continue
            if not merchant & _tokens(t.get("description") or ""):
                continue
            if best is None or t["date"] > candidates[best]["date"]:
                best = i
        if best is None:
            orphans.append(r)
        else:
            matched.add(best)
            excluded.append({**candidates[best], "exclude_reason": "rimborsato per intero", "refund": r})

    outflows = [t for i, t in enumerate(candidates) if i not in matched]
    return {"outflows": outflows, "excluded": excluded, "orphan_refunds": orphans}


_SUBJECT_MONTH_RE = re.compile(r"\[(\d{4}-\d{2})\]\s*$")


def find_duplicates(planned: list[dict[str, Any]], existing: list[dict[str, Any]]) -> list[dict[str, Any] | None]:
    """Confronta le autofatture in preparazione con quelle gia' su FiC.

    `planned`: dict con supplier_name, net, first_date, last_date (YYYY-MM-DD).
    `existing`: documenti FiC (fieldset basic: entity, amount_net, date, subject).
    Ritorna, per ogni planned, None oppure {level, fic_id, fic_number, fic_date, reason}:

      - "duplicate": stesso fornitore, stesso netto e stesso mese di addebito
        scritto nell'oggetto interno (documenti emessi da qui in poi)
      - "possible": documenti vecchi senza mese nell'oggetto; stesso fornitore e
        stesso netto, emessi dopo il primo addebito, quindi potrebbero coprirlo.
        Gli abbonamenti a prezzo fisso danno falsi positivi: va guardata la data.
    """
    out: list[dict[str, Any] | None] = []
    for p in planned:
        p_tokens = _tokens(p.get("supplier_name") or "")
        month = (p.get("first_date") or "")[:7]
        hit = None
        for d in existing:
            if abs((d.get("amount_net") or 0) - p["net"]) > 0.005:
                continue
            if not p_tokens & _tokens((d.get("entity") or {}).get("name") or ""):
                continue
            num = f"{d.get('number')}/{d.get('numeration')}"
            tag = _SUBJECT_MONTH_RE.search(d.get("subject") or "")
            if tag:
                if tag.group(1) == month:
                    hit = {"level": "duplicate", "reason": f"gia' emessa per {month}"}
                    hit.update(fic_id=d.get("id"), fic_number=num, fic_date=d.get("date"))
                    break
                continue
            if (d.get("date") or "") >= (p.get("first_date") or ""):
                hit = hit or {
                    "level": "possible",
                    "reason": f"stesso importo, emessa il {d.get('date')} (dopo il primo addebito del {p.get('first_date')})",
                    "fic_id": d.get("id"), "fic_number": num, "fic_date": d.get("date"),
                }
        out.append(hit)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("txns", type=Path, help="JSON prodotto da parse_bank_statement.py")
    args = ap.parse_args()
    res = prepare(json.loads(args.txns.read_text()))
    print(f"Addebiti da classificare: {len(res['outflows'])}")
    print(f"Esclusi: {len(res['excluded'])}")
    for e in res["excluded"]:
        print(f"  {e['date']} {e['amount']:>10.2f}  {e['exclude_reason']:<22} {e['description'][:50]}")
    if res["orphan_refunds"]:
        print("Rimborsi senza addebito nell'estratto (valutare nota di variazione):")
        for r in res["orphan_refunds"]:
            print(f"  {r['date']} {r['amount']:>10.2f}  {r['description'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
