"""lod_review_apply.py — Anteprima e scrittura su GHL dei risultati della review call LOD.

Legge un file JSON con un record per contatto (vedi workflows/lod_weekly_call_review.md).
Il file contiene dati dei prospect: tenerlo fuori dal repository.

Per impostazione predefinita mostra solo l'anteprima. Con --apply scrive esclusivamente
i record con "approved": true, e solo dopo la conferma esplicita di Lorenzo.

Usage:
    python tools/lod_review_apply.py review.json
    python tools/lod_review_apply.py review.json --apply [--only CONTACT_ID]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ghl_client as ghl
import lod_ghl_schema as schema

# chiave del record -> nome del campo GHL
FIELD_MAP = {
    "esito": "LOD Esito",
    "stato_firma": "LOD Stato firma",
    "stato_pagamento": "LOD Stato pagamento",
    "motivo_primario": "LOD Motivo primario",
    "motivo_secondario": "LOD Motivo secondario",
    "obiezione": "LOD Obiezione",
    "voto_discovery": "LOD Voto discovery",
    "voto_obiezione": "LOD Voto obiezione",
    "voto_next_step": "LOD Voto next step",
    "passi_prequal": "LOD Passi prequalifica",
    "pacchetto": "LOD Pacchetto",
    "zona": "LOD Zona",
    "data_ricontatto": "LOD Data ricontatto",
    "tipo_ricontatto": "LOD Tipo ricontatto",
    "ultima_call_data": "LOD Ultima call data",
    "ultima_call_tipo": "LOD Ultima call tipo",
    "link": "LOD Link registrazione",
    "affidabilita": "LOD Affidabilita analisi",
}


def build_tags(rec: dict) -> list[str]:
    f = rec["fields"]
    tags = []
    if f.get("esito"):
        tags.append(schema.TAG_PREFIXES["esito"] + f["esito"])
    for key in ("motivo_primario", "motivo_secondario"):
        if f.get(key):
            tags.append(schema.TAG_PREFIXES["motivo"] + f[key])
    if rec.get("created"):
        tags.append(schema.TAG_PREFIXES["cohort"] + rec["created"][:7])
    if f.get("promesse"):
        tags.append(schema.TAG_PROMESSE)
    if rec.get("task"):
        tags.append(schema.TAG_DA_RICONTATTARE)
    return list(dict.fromkeys(tags))


def build_note(rec: dict) -> str:
    f = rec["fields"]
    lines = [f"LOD review {rec['review_date']}", ""]
    lines.append(f"Fonte: {rec.get('fonte', 'n/d')} | Affidabilita: {f.get('affidabilita', 'n/d')}")
    if rec.get("riassunto"):
        lines += ["", rec["riassunto"]]
    if f.get("motivo_primario"):
        sec = f" / {f['motivo_secondario']}" if f.get("motivo_secondario") else ""
        lines += ["", f"Motivo: {f['motivo_primario']}{sec}"]
    if f.get("obiezione"):
        lines.append(f"Obiezione: {f['obiezione']}")
    if f.get("promesse"):
        lines += ["", "Promesse da controllare:"] + [f"- {p}" for p in f["promesse"]]
    if rec.get("da_verificare"):
        lines += ["", "Da verificare:"] + [f"- {p}" for p in rec["da_verificare"]]
    return "\n".join(lines)


def field_values(rec: dict, ids: dict[str, str]) -> dict[str, object]:
    f = rec["fields"]
    values: dict[str, object] = {}
    for key, name in FIELD_MAP.items():
        v = f.get(key)
        if v in (None, ""):
            continue
        if name not in ids:
            raise SystemExit(f"Campo mancante in GHL: {name}. Esegui prima lod_ghl_schema.py --apply")
        values[ids[name]] = v
    if f.get("promesse"):
        values[ids["LOD Promesse a rischio"]] = "\n".join(f["promesse"])
    return values


def preview(rec: dict) -> None:
    f = rec["fields"]
    print(f"\n== {rec['name']} | {rec.get('stage_now')}/{rec.get('status_now')} | abbinamento: {rec['match']} | approvato: {rec.get('approved', False)}")
    for key, name in FIELD_MAP.items():
        if f.get(key) not in (None, ""):
            print(f"   {name}: {f[key]}")
    print(f"   Tag: {', '.join(build_tags(rec))}")
    if rec.get("task"):
        t = rec["task"]
        print(f"   Task: {t['title']} | scadenza: {t.get('due') or 'da scegliere'}")


def apply(rec: dict, ids: dict[str, str]) -> None:
    cid = rec["contactId"]
    ghl.set_custom_fields(cid, field_values(rec, ids))
    ghl.add_tags(cid, build_tags(rec))
    marker = f"LOD review {rec['review_date']}"
    if not any(marker in (n.get("body") or "") for n in ghl.list_notes(cid)):
        ghl.add_note(cid, build_note(rec))
    task = rec.get("task")
    if task and task.get("due"):
        if not any(t.get("title") == task["title"] for t in ghl.list_tasks(cid)):
            ghl.create_task(cid, task["title"], task["due"])
    print(f"   scritto: {rec['name']}")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    records = json.load(open(sys.argv[1], encoding="utf-8"))
    do_apply = "--apply" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    if not do_apply:
        for rec in records:
            preview(rec)
        print(f"\nAnteprima di {len(records)} record. Nessuna scrittura.")
        return
    ids = schema.field_ids_by_name()
    todo = [r for r in records if r.get("approved") and (not only or r["contactId"] == only)]
    for rec in todo:
        apply(rec, ids)
    print(f"Scritti {len(todo)} record su {len(records)}.")


if __name__ == "__main__":
    main()
