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
    docs = c.list_self_supplier_invoices(fieldset="detailed")
    return sorted([d for d in docs if d.get("date") == date], key=lambda x: x["number"])


def doc_label(d: dict) -> str:
    return f"{d['number']}/{d['numeration']}"


def rejection_reason(c: FicClient, doc_id: int) -> str | None:
    try:
        return str(c._request(
            "GET", f"/c/{c.company_id}/issued_documents/{doc_id}/e_invoice/error_reason"))
    except Exception:
        return None


def verify_doc(c: FicClient, d: dict) -> tuple[bool, str]:
    """Verifica formale XML di un documento. Ritorna (ok, dettaglio)."""
    try:
        res = c._request("GET", f"/c/{c.company_id}/issued_documents/{d['id']}/e_invoice/xml_verify")
    except Exception as e:
        return False, str(e)[:200]
    data = res.get("data") or {}
    return bool(data.get("success")), "" if data.get("success") else str(data)


def send_doc(c: FicClient, d: dict) -> tuple[bool, str]:
    """Firma e invia al SDI. IRREVERSIBILE. Ritorna (ok, nome file o errore)."""
    try:
        res = c._request("POST", f"/c/{c.company_id}/issued_documents/{d['id']}/e_invoice/send",
                         json={"data": {}})
    except Exception as e:
        return False, str(e)[:200]
    return True, str((res.get("data") or {}).get("name") or "")


def show_status(c: FicClient, docs: list[dict]) -> None:
    cnt: Counter = Counter()
    tot = 0.0
    for d in docs:
        e = d.get("entity") or {}
        st = d.get("ei_status")
        cnt[st] += 1
        tot += d.get("amount_gross") or 0
        line = f"  {doc_label(d)}  {(e.get('name') or '')[:40]:<42} {d.get('amount_gross'):>8.2f}  {st}"
        if st == "rejected":
            line += f"  <- {rejection_reason(c, d['id'])}"
        print(line)
    print(f"\n{len(docs)} documenti | lordo {tot:.2f} | stati: {dict(cnt)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="Data documento del batch (YYYY-MM-DD)")
    ap.add_argument("--confirm", action="store_true", help="Invia davvero al SDI (IRREVERSIBILE)")
    ap.add_argument("--status", action="store_true", help="Mostra solo lo stato SDI del batch")
    args = ap.parse_args()

    c = FicClient()
    docs = load_batch(c, args.date)
    if not docs:
        print(f"Nessuna autofattura con data {args.date}")
        return 1

    if args.status:
        show_status(c, docs)
        return 0

    print(f"== Verifica formale su {len(docs)} documenti del {args.date} ==")
    valid, invalid = [], []
    for d in docs:
        if d.get("ei_status") in ALREADY_SENT:
            print(f"  {doc_label(d)} gia' inviata ({d.get('ei_status')}) - salto")
            continue
        ok, detail = verify_doc(c, d)
        print(f"  {doc_label(d)} {'OK' if ok else 'FAIL -> ' + detail}")
        (valid if ok else invalid).append(d)

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
        ok, detail = send_doc(c, d)
        print(f"  {doc_label(d)} -> {detail}")
        (sent if ok else failed).append(doc_label(d))
        time.sleep(1)

    print(f"\nInviate: {len(sent)} | errori: {len(failed)} {failed}")
    print("\nLo stato SDI definitivo (consegnata / scartata) arriva entro qualche ora.")
    print(f"Ricontrolla con: python tools/send_autofatture_sdi.py --date {args.date} --status")
    return 0


if __name__ == "__main__":
    sys.exit(main())
