#!/usr/bin/env python3
"""Riorganizza le cartelle dei custom field GHL secondo ghl_folder_layout.json.

Le cartelle GHL nascono nominate per FONTE del dato (`Survey | Survey 0`,
`Form | LMF i segreti`, `GPT SETTER`) e i campi finiscono in `Additional Info`
per default: aprendo una scheda contatto non c'e' modo di capire quale campo
serve in quale momento del processo. Questo tool le rinomina per FASE DI VENDITA
e ci sposta dentro i campi, nell'ordine in cui li usi davvero.

Vincoli API verificati il 01/08/2026:
- rinominare una cartella custom: SI (PUT con name)
- spostare un campo tra cartelle: SI (PUT con parentId)
- creare una cartella nuova: NO — per questo si riusano le 7 custom esistenti
- toccare le cartelle standard: NO (Contact, General Info, Additional Info)
  restano visibili ma vuote, perche' i loro campi vengono spostati altrove.

DRY-RUN PER DEFAULT. Senza --apply non scrive nulla.

Uso:
    python tools/ghl_reorganize_folders.py            # dry-run
    python tools/ghl_reorganize_folders.py --apply    # esegue
    python tools/ghl_reorganize_folders.py --revert <backup.json>
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import ghl_client as ghl  # noqa: E402

LAYOUT_PATH = PROJECT_ROOT / "tools" / "ghl_folder_layout.json"
THROTTLE_S = 0.12


def snapshot(fields: dict) -> Path:
    """Salva cartella, nome e posizione attuali di ogni campo. È il --revert."""
    out_dir = PROJECT_ROOT / ".tmp"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"ghl_folders_backup_{date.today().isoformat()}.json"
    path.write_text(
        json.dumps(
            {
                fid: {
                    "name": f.get("name"),
                    "parentId": f.get("parentId"),
                    "position": f.get("position"),
                    "documentType": f.get("documentType"),
                }
                for fid, f in fields.items()
            },
            indent=1,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def build_plan(layout: dict, fields: dict) -> dict:
    renames, moves, errori = [], [], []

    for folder_id, new_name in layout["rinomina_cartelle"].items():
        folder = fields.get(folder_id)
        if not folder:
            errori.append(f"cartella {folder_id} non trovata")
            continue
        if folder.get("name") != new_name:
            renames.append((folder_id, folder.get("name"), new_name))

    for folder_id, field_ids in layout["campi_per_cartella"].items():
        for i, fid in enumerate(field_ids):
            f = fields.get(fid)
            if not f:
                errori.append(f"campo {fid} non trovato")
                continue
            # position controlla l'ordine dentro la cartella: passo a step di 10
            # per poter inserire campi in mezzo in futuro senza rinumerare tutto.
            # Si parte da 10, non da 0: GHL ignora position=0 e lascia il campo
            # alla posizione che aveva: il primo campo di ogni cartella finirebbe
            # in fondo, che è esattamente il contrario di quel che serve.
            want_pos = (i + 1) * 10
            if f.get("parentId") != folder_id or f.get("position") != want_pos:
                moves.append(
                    {
                        "field_id": fid,
                        "nome": f.get("name"),
                        "da": fields.get(f.get("parentId"), {}).get("name", "(nessuna)"),
                        "a": folder_id,
                        "position": want_pos,
                    }
                )

    # Un campo dimenticato resta dov'e': va segnalato, non ignorato in silenzio.
    assegnati = {i for ids in layout["campi_per_cartella"].values() for i in ids}
    orfani = [
        f.get("name")
        for fid, f in fields.items()
        if f.get("documentType") != "folder" and fid not in assegnati
    ]
    return {"renames": renames, "moves": moves, "errori": errori, "non_assegnati": orfani}


def print_plan(plan: dict, layout: dict, fields: dict) -> None:
    print(f"\n{'─' * 70}\nRINOMINA CARTELLE ({len(plan['renames'])})")
    for _, old, new in plan["renames"]:
        print(f"  {old!r}\n     → {new!r}")

    print(f"\n{'─' * 70}\nSPOSTAMENTI CAMPI ({len(plan['moves'])})")
    for folder_id, new_name in layout["rinomina_cartelle"].items():
        in_folder = [m for m in plan["moves"] if m["a"] == folder_id]
        totale = len(layout["campi_per_cartella"].get(folder_id, []))
        print(f"\n  {new_name}  ({totale} campi, {len(in_folder)} da spostare)")
        for m in in_folder:
            print(f"     {m['nome'][:52]:<54} ← {m['da']}")

    if plan["non_assegnati"]:
        print(f"\n⚠️  campi non assegnati a nessuna cartella: {plan['non_assegnati']}")
    if plan["errori"]:
        print(f"\n❌ {plan['errori']}")


def apply_plan(plan: dict) -> int:
    done = 0
    # Prima i rinomini: cosi' se qualcosa si interrompe a meta' degli
    # spostamenti, le cartelle hanno gia' i nomi giusti e il piano e' rilanciabile.
    for folder_id, _, new_name in plan["renames"]:
        ghl.update_custom_field_definition(folder_id, name=new_name)
        print(f"  ✓ cartella → {new_name}")
        done += 1
        time.sleep(THROTTLE_S)

    for m in plan["moves"]:
        ghl.update_custom_field_definition(
            m["field_id"], name=m["nome"], parentId=m["a"], position=m["position"]
        )
        done += 1
        if done % 15 == 0:
            print(f"  … {done}")
        time.sleep(THROTTLE_S)
    print(f"  ✓ {len(plan['moves'])} campi spostati")
    return done


def revert(path: Path) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    n = 0
    for fid, snap in data.items():
        if snap.get("documentType") == "folder":
            ghl.update_custom_field_definition(fid, name=snap["name"])
        else:
            ghl.update_custom_field_definition(
                fid, name=snap["name"], parentId=snap["parentId"], position=snap["position"]
            )
        n += 1
        time.sleep(THROTTLE_S)
    print(f"✅ ripristinati {n} elementi da {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Riorganizza le cartelle custom field GHL")
    ap.add_argument("--apply", action="store_true", help="esegue (senza: dry-run)")
    ap.add_argument("--revert", metavar="BACKUP", help="ripristina da un backup cartelle")
    args = ap.parse_args()

    if args.revert:
        revert(Path(args.revert))
        return

    layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in ghl.list_custom_fields()}
    # list_custom_fields non ritorna le cartelle, solo i campi. Vanno recuperate
    # una a una: sia le 7 da rinominare, sia le standard da cui provengono i
    # campi — senza queste il dry-run mostrerebbe "(nessuna)" come provenienza
    # e sarebbe illeggibile proprio dove serve verificarlo.
    referenced = set(layout["rinomina_cartelle"])
    referenced |= {f.get("parentId") for f in list(fields.values()) if f.get("parentId")}
    for folder_id in referenced:
        if folder_id and folder_id not in fields:
            fields[folder_id] = ghl.get_custom_field(folder_id)

    plan = build_plan(layout, fields)
    mode = "APPLY — scrittura reale" if args.apply else "DRY-RUN — nessuna scrittura"
    print(f"\n{'═' * 70}\n  {mode}\n{'═' * 70}")
    print_plan(plan, layout, fields)

    if plan["errori"]:
        print("\n❌ errori nel layout: interrompo.")
        sys.exit(1)

    if args.apply:
        path = snapshot(fields)
        print(f"\n💾 backup cartelle: {path.relative_to(PROJECT_ROOT)}")
        print(f"   revert: python tools/ghl_reorganize_folders.py --revert {path}\n")
        apply_plan(plan)
        print("\n✅ fatto. Verifica: python tools/ghl_fields_audit.py")
    else:
        print(f"\n{'═' * 70}\nNessuna scrittura. Per applicare: --apply")


if __name__ == "__main__":
    try:
        main()
    except ghl.GHLError as exc:
        print(f"[folders] ❌ errore GHL: {exc}", file=sys.stderr)
        sys.exit(1)
