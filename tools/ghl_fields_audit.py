#!/usr/bin/env python3
"""Audit read-only dei custom field GHL: inventario, fill-rate, valori orfani.

Perché esiste: le picklist dei campi GHL sono state modificate più volte *sotto*
i dati già raccolti. Ogni modifica lascia i valori storici orfani rispetto alle
opzioni nuove, e i segmenti costruiti su quei campi smettono silenziosamente di
funzionare. Questo tool rende l'audit ripetibile invece che una tantum: lo
rilanci dopo ogni modifica a un form o a una picklist e vedi subito se hai
rotto qualcosa.

Nessun side-effect: solo GET/POST di ricerca. Sicuro da lanciare quando vuoi.

Uso:
    python tools/ghl_fields_audit.py              # report completo
    python tools/ghl_fields_audit.py --orphans    # solo i campi con valori fuori picklist
    python tools/ghl_fields_audit.py --field <id> # dettaglio di un singolo campo
    python tools/ghl_fields_audit.py --dump       # backup JSON in .tmp/ (fare PRIMA di scrivere)

Il backup di --dump è l'unico modo di tornare indietro: GHL non ha undo sulle
scritture dei custom field.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import ghl_client as ghl  # noqa: E402

# Le cartelle non sono ritornate da GET /customFields (l'endpoint elenca solo i
# campi), ma ogni campo porta il proprio `parentId`. Vanno risolte una per una.
_FOLDER_CACHE: dict[str, str] = {}


def folder_name(parent_id: str | None) -> str:
    """Risolve l'id cartella nel suo nome. Cache: la stessa cartella torna decine di volte."""
    if not parent_id:
        return "(nessuna cartella)"
    if parent_id not in _FOLDER_CACHE:
        try:
            data = ghl._request("GET", f"/locations/{ghl.LOCATION_ID}/customFields/{parent_id}")
            _FOLDER_CACHE[parent_id] = data.get("customField", {}).get("name", parent_id)
        except ghl.GHLError:
            _FOLDER_CACHE[parent_id] = f"(cartella {parent_id})"
    return _FOLDER_CACHE[parent_id]


def fetch_all_contacts() -> list[dict]:
    """Tutti i contatti della location, con i customFields valorizzati.

    Pagina con `searchAfter` come search_contacts_by_tags in ghl_client, ma senza
    filtri: qui serve l'universo completo per calcolare i fill-rate reali.
    """
    contacts: list[dict] = []
    search_after = None
    while True:
        payload: dict = {"locationId": ghl.LOCATION_ID, "pageLimit": 100}
        if search_after:
            payload["searchAfter"] = search_after
        page = ghl._request("POST", "/contacts/search", json=payload).get("contacts", [])
        if not page:
            break
        contacts.extend(page)
        search_after = page[-1].get("searchAfter")
        if not search_after:
            break
    return contacts


def values_by_field(contacts: list[dict]) -> dict[str, collections.Counter]:
    """field_id → Counter dei valori non vuoti trovati sui contatti."""
    out: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for contact in contacts:
        for cf in contact.get("customFields") or []:
            value = cf.get("value")
            if value in (None, "", [], {}):
                continue
            # I MULTIPLE_OPTIONS arrivano come lista: ogni scelta conta a sé.
            if isinstance(value, list):
                for item in value:
                    out[cf["id"]][str(item)] += 1
            else:
                out[cf["id"]][str(value)] += 1
    return out


def report(fields: list[dict], values: dict, total_contacts: int, only_orphans: bool) -> None:
    rows = [f for f in fields if f.get("documentType") != "folder"]
    rows.sort(key=lambda f: (folder_name(f.get("parentId")), -sum(values[f["id"]].values())))

    print(f"\n{'CARTELLA':<22}|{'CAMPO':<42}|{'TIPO':<16}|{'USI':>5}|{'ORFANI':>7}| SALUTE")
    print("-" * 110)

    problemi = []
    for f in rows:
        counter = values[f["id"]]
        used = sum(counter.values())
        opts = set(f.get("picklistOptions") or [])
        # Solo i campi a picklist possono avere orfani: su TEXT/LARGE_TEXT ogni
        # valore è legittimo per definizione.
        orphans = sum(n for v, n in counter.items() if v not in opts) if opts else 0

        if only_orphans and not orphans:
            continue

        if not opts:
            salute = "-"
        elif used == 0:
            salute = "vuoto"
        else:
            pct = 100 * (used - orphans) // used
            salute = f"{pct}% in picklist"
            if pct < 95:
                problemi.append((f, used, orphans, pct))

        print(
            f"{folder_name(f.get('parentId'))[:20]:<22}|{f['name'][:40]:<42}|"
            f"{f['dataType']:<16}|{used:>5}|{orphans:>7}| {salute}"
        )

    print(f"\ncontatti analizzati: {total_contacts} · campi: {len(rows)}")

    if problemi:
        print(f"\n⚠️  {len(problemi)} campi sotto la soglia del 95%:")
        for f, used, orphans, pct in sorted(problemi, key=lambda x: x[3]):
            print(f"   {pct:>3}%  {f['name'][:50]:<52} {orphans}/{used} orfani   id={f['id']}")
        print("\n   Dettaglio: python tools/ghl_fields_audit.py --field <id>")


def report_field(fields: list[dict], values: dict, field_id: str) -> None:
    field = next((f for f in fields if f["id"] == field_id), None)
    if not field:
        print(f"❌ campo {field_id} non trovato", file=sys.stderr)
        sys.exit(1)

    opts = set(field.get("picklistOptions") or [])
    counter = values[field_id]
    print(f"\n{field['name']}")
    print(f"  id       : {field['id']}")
    print(f"  fieldKey : {field['fieldKey']}")
    print(f"  tipo     : {field['dataType']}   cartella: {folder_name(field.get('parentId'))}")
    print(f"  creato   : {field.get('dateAdded', '?')[:10]}")
    if opts:
        print(f"  picklist : {sorted(opts)}")
    print(f"\n  valori trovati ({sum(counter.values())} su {len(counter)} distinti):")
    for value, n in counter.most_common():
        flag = "OK " if not opts or value in opts else "ORF"
        print(f"    {flag} {n:>4}  {value}")


def key_matches_name(key: str, name: str) -> bool:
    """La chiave descrive davvero il campo, o è il residuo di un altro campo?

    Confronta le parole significative: una chiave generata dal nome ne condivide
    quasi tutte. Una ereditata da uno snapshot importato non ne condivide
    nessuna, per quanto lunga sia. Le chiavi autogenerate (`radio_2877z`) non
    condividono nulla per definizione e vanno segnalate.
    """
    def tokens(text: str) -> set[str]:
        clean = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
        return {t for t in clean.split() if len(t) > 3}

    name_tokens = tokens(name)
    if not name_tokens:
        return True
    return len(name_tokens & tokens(key)) / len(name_tokens) >= 0.4


def print_dictionary(fields: list[dict], values: dict) -> None:
    """Dizionario campi in markdown: nome ↔ fieldKey ↔ id ↔ utilizzo.

    Serve perché 5 campi hanno il `fieldKey` ereditato da uno snapshot GHL
    americano di un altro settore — es. "In quale settore operi?" ha chiave
    `contact.do_you_currently_have_the_ability_to_listen_to_recordings...`.
    La chiave non è modificabile, quindi l'unica difesa è documentarla: chi
    costruisce un merge tag o un filtro deve poter risalire alla chiave vera.
    """
    rows = [f for f in fields if f.get("documentType") != "folder"]
    rows.sort(key=lambda f: f["name"].lower())

    print("| Campo | fieldKey | id | Usi | Tipo |")
    print("|---|---|---|---|---|")
    for f in rows:
        key = f["fieldKey"].replace("contact.", "")
        sospetta = " ⚠️" if not key_matches_name(key, f["name"]) else ""
        print(
            f"| {f['name']} | `{key}`{sospetta} | `{f['id']}` | "
            f"{sum(values[f['id']].values())} | {f['dataType']} |"
        )
    print(f"\n⚠️ = chiave non allineata al nome (residuo di snapshot importato, non modificabile)")


def dump_backup(fields: list[dict], contacts: list[dict]) -> Path:
    """Snapshot completo definizioni + valori. Da fare PRIMA di ogni scrittura."""
    out_dir = PROJECT_ROOT / ".tmp"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"ghl_backup_{date.today().isoformat()}.json"

    payload = {
        "generato_il": date.today().isoformat(),
        "location_id": ghl.LOCATION_ID,
        "custom_fields": fields,
        "contatti": [
            {
                "id": c.get("id"),
                "email": c.get("email"),
                "customFields": [
                    cf for cf in (c.get("customFields") or [])
                    if cf.get("value") not in (None, "", [], {})
                ],
            }
            for c in contacts
        ],
    }
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit read-only dei custom field GHL")
    ap.add_argument("--orphans", action="store_true", help="mostra solo i campi con valori fuori picklist")
    ap.add_argument("--field", metavar="ID", help="dettaglio di un singolo campo")
    ap.add_argument("--dump", action="store_true", help="salva il backup JSON in .tmp/")
    ap.add_argument("--dictionary", action="store_true", help="dizionario campi in markdown")
    args = ap.parse_args()

    print("[audit] lettura definizioni campo...", file=sys.stderr)
    fields = ghl.list_custom_fields()
    print(f"[audit] {len(fields)} definizioni · lettura contatti...", file=sys.stderr)
    contacts = fetch_all_contacts()
    print(f"[audit] {len(contacts)} contatti", file=sys.stderr)

    values = values_by_field(contacts)

    if args.dump:
        path = dump_backup(fields, contacts)
        print(f"\n✅ backup salvato: {path.relative_to(PROJECT_ROOT)}")
        print("   Committalo prima di lanciare qualsiasi scrittura.")
        return

    if args.dictionary:
        print_dictionary(fields, values)
        return

    if args.field:
        report_field(fields, values, args.field)
        return

    report(fields, values, len(contacts), args.orphans)


if __name__ == "__main__":
    try:
        main()
    except ghl.GHLError as exc:
        print(f"[audit] ❌ errore GHL: {exc}", file=sys.stderr)
        sys.exit(1)
