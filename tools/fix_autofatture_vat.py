"""
One-shot: corregge le autofatture extra-UE 2026 per mettere vat_id=10 (0%)
e RegimeFiscale RF18, come richiede il commercialista per fornitori fuori UE.
Cancella inoltre 20/a Google che NON e' autofattura (Google Cloud Italy fatt. diretta IT 22%).

Usage:
    python tools/fix_autofatture_vat.py --dry-run      # stampa solo cosa farebbe
    python tools/fix_autofatture_vat.py --only 25      # applica solo a 25/a (test)
    python tools/fix_autofatture_vat.py                # esegue tutto
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fic_client import FicClient  # noqa: E402

# id documento -> numero (per log)
EXTRA_UE_DOCS = {
    516604493: 14,   # ElevenLabs
    516604530: 18,   # Gamma
    516604546: 21,   # Myleadfox (UAE)
    516604554: 22,   # OpenAI L.L.C.
    516604603: 24,   # Josh Von Mailsupply
    516604618: 25,   # Lovable
    516604662: 28,   # Higgsfield
}
GOOGLE_DOC_ID = 516604543  # 20/a da CANCELLARE

RF18_EI_RAW = {
    "FatturaElettronicaBody": {
        "DatiGenerali": {
            "DatiGeneraliDocumento": {"TipoDocumento": "TD17"}
        }
    },
    "FatturaElettronicaHeader": {
        "CedentePrestatore": {
            "DatiAnagrafici": {"RegimeFiscale": "RF18"}
        }
    },
}


def fix_doc(c: FicClient, doc_id: int, dry: bool) -> None:
    num = EXTRA_UE_DOCS[doc_id]
    r = c._request("GET", f"/c/{c.company_id}/issued_documents/{doc_id}",
                   params={"fields": "id,number,entity,items_list,payments_list,ei_raw,ei_data"})
    d = r.get("data", {})
    items = d.get("items_list") or []
    payments = d.get("payments_list") or []
    if not items or not payments:
        print(f"  [{num}/a] SKIP: no items or payments")
        return
    item = items[0]
    payment = payments[0]
    net = float(item.get("net_price") or 0)
    current_gross = float(item.get("gross_price") or 0)
    supplier = (d.get("entity") or {}).get("name", "?")
    print(f"  [{num}/a] {supplier[:40]} | net={net} gross={current_gross} -> new_gross={net}")

    # Payload minimale: aggiorno vat, gross_price, amount pagamento, ei_raw
    new_item = copy.deepcopy(item)
    new_item["vat"] = {"id": 10}
    new_item["gross_price"] = net  # gross = net quando vat=0% non soggetta

    new_payment = copy.deepcopy(payment)
    new_payment["amount"] = net

    payload = {
        "data": {
            "items_list": [new_item],
            "payments_list": [new_payment],
            "ei_raw": RF18_EI_RAW,
        }
    }
    if dry:
        print(f"    DRY-RUN payload items[0].vat={new_item['vat']} gross={new_item['gross_price']} "
              f"payment.amount={new_payment['amount']}")
        return
    try:
        c._request("PUT", f"/c/{c.company_id}/issued_documents/{doc_id}", json=payload)
        print(f"    OK updated")
    except Exception as e:
        print(f"    ERROR: {e}")


def delete_google(c: FicClient, dry: bool) -> None:
    print(f"\n== DELETE 20/a Google (id={GOOGLE_DOC_ID}) ==")
    if dry:
        print("  DRY-RUN: non cancellato")
        return
    try:
        c._request("DELETE", f"/c/{c.company_id}/issued_documents/{GOOGLE_DOC_ID}")
        print("  OK deleted")
    except Exception as e:
        print(f"  ERROR: {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", type=int, help="Applica solo al numero specificato (es. 25)")
    ap.add_argument("--skip-delete", action="store_true", help="Non cancellare Google 20/a")
    args = ap.parse_args()

    c = FicClient()
    print("== FIX extra-UE autofatture (vat_id=10 + RF18) ==")
    for doc_id, num in EXTRA_UE_DOCS.items():
        if args.only and num != args.only:
            continue
        fix_doc(c, doc_id, args.dry_run)

    if not args.only and not args.skip_delete:
        delete_google(c, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
