"""
Verifica formale + invio al SDI delle autofatture di un batch.

Equivale ai due click "Verifica formale" e "Firma e invia" sulla UI di Fatture in Cloud,
ma in batch. L'invio al SDI e' IRREVERSIBILE: per annullare un documento consegnato
serve una nota di variazione. Per questo:

  - senza --confirm lo script esegue SOLO la verifica formale (read-only) e si ferma
  - l'invio parte solo con --confirm esplicito
  - i documenti che non superano la verifica formale non vengono mai inviati

Usage:
    python tools/send_autofatture_sdi.py --date 2026-08-22              # solo verifica
    python tools/send_autofatture_sdi.py --date 2026-08-22 --confirm    # verifica + invio
    python tools/send_autofatture_sdi.py --date 2026-08-22 --status     # stato SDI del batch
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fic_client import FicClient  # noqa: E402

ALREADY_SENT = {"pending", "processing", "sent", "delivered", "not_delivered", "rejected"}


def load_batch(c: FicClient, date: str) -> list[dict]:
    r = c._request(
        "GET",
        f"/c/{c.company_id}/issued_documents",
        params={"type": "self_supplier_invoice", "per_page": 100,
                "fieldset": "detailed", "sort": "-id"},
    )
    return sorted([d for d in r.get("data", []) if d.get("date") == date],
                  key=lambda x: x["number"])


def show_status(docs: list[dict]) -> None:
    cnt: Counter = Counter()
    tot = 0.0
    for d in docs:
        e = d.get("entity") or {}
        st = d.get("ei_status")
        cnt[st] += 1
        tot += d.get("amount_gross") or 0
        line = f"  {d['number']}/{d['numeration']}  {(e.get('name') or '')[:40]:<42} {d.get('amount_gross'):>8.2f}  {st}"
        if st == "rejected":
            try:
                reason = c._request(
                    "GET", f"/c/{c.company_id}/issued_documents/{d['id']}/e_invoice/error_reason"
                )
                line += f"  <- {reason}"
            except Exception:
                pass
        print(line)
    print(f"\n{len(docs)} documenti | lordo {tot:.2f} | stati: {dict(cnt)}")


def main() -> int:
    global c
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="Data documento del batch (YYYY-MM-DD)")
    ap.add_argument("--confirm", action="store_true", help="Invia davvero al SDI (IRREVERSIBILE)")
    ap.add_argument("--status", action="store_true", help="Mostra solo lo stato SDI del batch")
    args = ap.parse_args()

    c = FicClient()
    c.refresh_if_needed()
    docs = load_batch(c, args.date)
    if not docs:
        print(f"Nessuna autofattura con data {args.date}")
        return 1

    if args.status:
        show_status(docs)
        return 0

    print(f"== Verifica formale su {len(docs)} documenti del {args.date} ==")
    valid, invalid = [], []
    for d in docs:
        n = f"{d['number']}/{d['numeration']}"
        if d.get("ei_status") in ALREADY_SENT:
            print(f"  {n} gia' inviata ({d.get('ei_status')}) - salto")
            continue
        try:
            res = c._request("GET", f"/c/{c.company_id}/issued_documents/{d['id']}/e_invoice/xml_verify")
            if (res.get("data") or {}).get("success"):
                print(f"  {n} OK")
                valid.append(d)
            else:
                print(f"  {n} FAIL -> {res.get('data')}")
                invalid.append(d)
        except Exception as e:
            print(f"  {n} ERRORE -> {str(e)[:200]}")
            invalid.append(d)

    print(f"\nVerifica formale: {len(valid)} OK, {len(invalid)} da correggere")
    if invalid:
        print("I documenti che non superano la verifica NON verranno inviati.")
    if not args.confirm:
        print("\nNessun invio eseguito (manca --confirm). L'invio al SDI e' irreversibile.")
        return 0
    if not valid:
        return 1

    print(f"\n== Invio al SDI di {len(valid)} documenti ==")
    sent, failed = [], []
    for d in valid:
        n = f"{d['number']}/{d['numeration']}"
        try:
            res = c._request("POST", f"/c/{c.company_id}/issued_documents/{d['id']}/e_invoice/send",
                             json={"data": {}})
            print(f"  {n} -> {(res.get('data') or {}).get('name')}")
            sent.append(n)
        except Exception as e:
            print(f"  {n} ERRORE -> {str(e)[:200]}")
            failed.append(n)
        time.sleep(1)

    print(f"\nInviate: {len(sent)} | errori: {len(failed)} {failed}")
    print("\nLo stato SDI definitivo (consegnata / scartata) arriva entro qualche ora.")
    print(f"Ricontrolla con: python tools/send_autofatture_sdi.py --date {args.date} --status")
    return 0


if __name__ == "__main__":
    sys.exit(main())
