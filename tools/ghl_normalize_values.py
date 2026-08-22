#!/usr/bin/env python3
"""Unifica i valori storici dei custom field GHL secondo ghl_value_mappings.json.

Due lavori distinti, selezionabili con --only:

  picklist  allinea i valori storici alle opzioni dei campi a scelta multipla
  qualifica popola il campo derivato "Qualifica fatturato" (sotto soglia / ICP /
            enterprise), su cui far girare segmenti e automazioni al posto del
            campo fatturato grezzo, che resta storicamente sporco

DRY-RUN PER DEFAULT. Senza --apply non scrive nulla: stampa il diff e si ferma.
Leggi sempre il dry-run prima di applicare.

Uso:
    python tools/ghl_normalize_values.py                    # dry-run completo
    python tools/ghl_normalize_values.py --only qualifica   # solo campo derivato
    python tools/ghl_normalize_values.py --apply            # scrive davvero

Prerequisito: backup fatto con `python tools/ghl_fields_audit.py --dump`.
GHL non ha undo sulle scritture dei custom field.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import ghl_client as ghl  # noqa: E402
from ghl_fields_audit import fetch_all_contacts  # noqa: E402

MAPPINGS_PATH = PROJECT_ROOT / "tools" / "ghl_value_mappings.json"
# GHL regge burst brevi ma non raffiche continue: una pausa breve tra le
# scritture evita i 429 su qualche centinaio di contatti.
THROTTLE_S = 0.12


def contact_values(contact: dict) -> dict[str, object]:
    """field_id → valore, solo per i campi valorizzati."""
    return {
        cf["id"]: cf.get("value")
        for cf in (contact.get("customFields") or [])
        if cf.get("value") not in (None, "", [], {})
    }


# ─── Picklist ────────────────────────────────────────────────────────────────


def plan_picklist(spec: dict, contacts: list[dict], fields: dict) -> dict:
    """Calcola le scritture necessarie per un campo, senza eseguirle."""
    fid = spec["field_id"]
    field = fields.get(fid)
    if not field:
        return {"errore": f"campo {fid} non trovato su GHL"}

    value_map = spec.get("value_map") or {}
    keep = set(spec.get("lascia_intatti") or [])
    preserve = spec.get("preserva_originale_in")

    writes, unmapped = [], collections.Counter()
    for c in contacts:
        vals = contact_values(c)
        current = vals.get(fid)
        if current is None or isinstance(current, list):
            continue
        current = str(current)
        if current in value_map:
            target = value_map[current]
            entry = {
                "contact_id": c["id"],
                "email": c.get("email") or "(senza email)",
                "da": current,
                "a": target,
            }
            # La nicchia dichiarata a mano si perderebbe collassandola su
            # "Altro": la si salva nel campo testo dedicato, ma solo se quel
            # campo e' libero — non sovrascriviamo mai un valore esistente.
            if preserve and target == preserve.get("solo_se_mappato_a"):
                if not vals.get(preserve["field_id"]):
                    entry["preserva"] = (preserve["field_id"], current)
            writes.append(entry)
        else:
            opts = set(field.get("picklistOptions") or [])
            if opts and current not in opts and current not in keep:
                unmapped[current] += 1

    # Regole che non matchano nulla: o i dati sono gia' stati migrati, o la
    # regola e' stata scritta male (spazi, en-dash). Vanno segnalate.
    matched = {w["da"] for w in writes}
    stale = [k for k in value_map if k not in matched]

    return {
        "field_id": fid,
        "nome": spec["nome"],
        "picklist_attuale": field.get("picklistOptions") or [],
        "picklist_finale": spec.get("picklist_finale"),
        "writes": writes,
        "unmapped": unmapped,
        "stale": stale,
    }


def print_picklist_plan(plan: dict) -> None:
    if "errore" in plan:
        print(f"  ❌ {plan['errore']}")
        return

    print(f"\n{'─' * 78}\n{plan['nome']}  [{plan['field_id']}]")

    finale = plan["picklist_finale"]
    if finale:
        attuale = plan["picklist_attuale"]
        aggiunte = [o for o in finale if o not in attuale]
        rimosse = [o for o in attuale if o not in finale]
        if aggiunte:
            print(f"  picklist  + {aggiunte}")
        if rimosse:
            print(f"  picklist  - {rimosse}")
        if not aggiunte and not rimosse:
            print("  picklist  invariata")
    else:
        print("  picklist  invariata (solo migrazione valori)")

    by_change = collections.Counter((w["da"], w["a"]) for w in plan["writes"])
    if by_change:
        print(f"  {len(plan['writes'])} contatti da aggiornare:")
        for (da, a), n in by_change.most_common():
            print(f"     {n:>4}  {da!r} → {a!r}")
    else:
        print("  nessun contatto da aggiornare")

    n_pres = sum(1 for w in plan["writes"] if "preserva" in w)
    if n_pres:
        print(f"  {n_pres} valori originali salvati in 'Specifica se Altro...'")

    if plan["unmapped"]:
        print(f"  ⚠️  {sum(plan['unmapped'].values())} valori orfani SENZA mappatura (restano invariati):")
        for v, n in plan["unmapped"].most_common():
            print(f"     {n:>4}  {v!r}")
    if plan["stale"]:
        print(f"  ℹ️  regole che non matchano nulla (gia' migrate o da correggere): {plan['stale']}")


def apply_picklist(plan: dict) -> int:
    """Esegue nell'ordine sicuro: aggiungi opzioni → migra valori → rimuovi vecchie."""
    fid, finale = plan["field_id"], plan["picklist_finale"]
    attuale = plan["picklist_attuale"]

    # 1. Aggiunge le nuove opzioni MANTENENDO le vecchie: durante la migrazione
    #    entrambe devono essere valide, altrimenti si crea una finestra in cui i
    #    valori non ancora migrati risultano orfani.
    if finale:
        transitoria = attuale + [o for o in finale if o not in attuale]
        if transitoria != attuale:
            ghl.update_custom_field_definition(fid, name=plan["nome"], options=transitoria)
            print(f"  ✓ picklist estesa a {len(transitoria)} opzioni")

    # 2. Migra i valori sui contatti.
    done = 0
    for w in plan["writes"]:
        ghl.update_custom_field(w["contact_id"], fid, w["a"])
        if "preserva" in w:
            pid, original = w["preserva"]
            ghl.update_custom_field(w["contact_id"], pid, original)
        done += 1
        if done % 25 == 0:
            print(f"  … {done}/{len(plan['writes'])}")
        time.sleep(THROTTLE_S)
    if done:
        print(f"  ✓ {done} contatti aggiornati")

    # 3. Solo ora si possono togliere le opzioni vecchie.
    if finale and finale != attuale:
        ghl.update_custom_field_definition(fid, name=plan["nome"], options=finale)
        print(f"  ✓ picklist finale: {len(finale)} opzioni")
    return done


# ─── Qualifica fatturato ─────────────────────────────────────────────────────

INF = float("inf")

# Due sole fasce, separate dalla soglia ICP dei 25k/mese. Non c'e' una fascia
# "Enterprise": nessuno dei 528 contatti dichiara oltre 300k/mese, e tenerla
# spingerebbe in "Da riconfermare" una ventina di lead palesemente qualificati
# solo perche' il loro valore e' aperto verso l'alto ("oltre 80k €/mese").
BANDS = [
    ("Sotto soglia (<25k/mese)", 0, 25000),
    ("ICP (≥25k/mese)", 25000, INF),
]


def classify(interval: list) -> str | None:
    """Classifica solo se l'intervallo e' interamente CONTENUTO in una fascia.

    Se scavalca la soglia ritorna None → 'Da riconfermare'. Meglio un dato
    dichiarato incerto che una qualifica inventata: da questo campo dipende chi
    viene chiamato e chi no.

    Il test e' di contenimento (lo >= b0 and hi <= b1), non di sovrapposizione:
    con la sovrapposizione un valore puntuale come 0 non ricadrebbe in nessuna
    fascia.
    """
    lo = interval[0]
    hi = INF if interval[1] is None else interval[1]
    for name, b0, b1 in BANDS:
        if lo >= b0 and hi <= b1:
            return name
    return None


def plan_qualifica(spec: dict, contacts: list[dict], fields: dict) -> dict:
    intervals = spec["intervalli_mensili_euro"]
    sources = spec["sorgenti"]

    target = next((f for f in fields.values() if f.get("name") == spec["nome_campo"]), None)

    writes, unknown = [], collections.Counter()
    for c in contacts:
        vals = contact_values(c)
        raw = next((str(vals[s]) for s in sources if vals.get(s)), None)
        if raw is None:
            continue
        label = classify(intervals[raw]) if raw in intervals else None
        if raw not in intervals:
            unknown[raw] += 1
        writes.append(
            {
                "contact_id": c["id"],
                "email": c.get("email") or "(senza email)",
                "da": raw,
                "a": label or "Da riconfermare",
            }
        )
    return {
        "campo_esistente": target,
        "spec": spec,
        "writes": writes,
        "unknown": unknown,
    }


def print_qualifica_plan(plan: dict) -> None:
    spec = plan["spec"]
    print(f"\n{'─' * 78}\n{spec['nome_campo']}  (campo derivato)")
    if plan["campo_esistente"]:
        print(f"  campo gia' esistente: {plan['campo_esistente']['id']}")
    else:
        print(f"  DA CREARE · {spec['tipo']} · {len(spec['opzioni'])} opzioni")

    dist = collections.Counter(w["a"] for w in plan["writes"])
    print(f"  {len(plan['writes'])} contatti coperti:")
    for label, n in dist.most_common():
        print(f"     {n:>4}  {label}")

    risolti = len(plan["writes"]) - dist.get("Da riconfermare", 0)
    if plan["writes"]:
        pct = 100 * risolti // len(plan["writes"])
        print(f"  risolti in automatico: {risolti}/{len(plan['writes'])} ({pct}%)")

    da_ric = collections.Counter(w["da"] for w in plan["writes"] if w["a"] == "Da riconfermare")
    if da_ric:
        print("  da riconfermare a mano:")
        for v, n in da_ric.most_common():
            print(f"     {n:>4}  {v!r}")
    if plan["unknown"]:
        print(f"  ⚠️  valori senza intervallo definito: {dict(plan['unknown'])}")


def apply_qualifica(plan: dict) -> int:
    spec = plan["spec"]
    field = plan["campo_esistente"]
    if not field:
        field = ghl.create_custom_field(spec["nome_campo"], spec["tipo"], spec["opzioni"])
        print(f"  ✓ campo creato: {field.get('id')}")
    fid = field["id"]

    done = 0
    for w in plan["writes"]:
        ghl.update_custom_field(w["contact_id"], fid, w["a"])
        done += 1
        if done % 25 == 0:
            print(f"  … {done}/{len(plan['writes'])}")
        time.sleep(THROTTLE_S)
    print(f"  ✓ {done} contatti aggiornati")
    return done


# ─── Main ────────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(description="Unifica i valori dei custom field GHL")
    ap.add_argument("--apply", action="store_true", help="scrive davvero (senza: dry-run)")
    ap.add_argument("--only", choices=["picklist", "qualifica"], help="esegue solo una delle due parti")
    args = ap.parse_args()

    mappings = json.loads(MAPPINGS_PATH.read_text(encoding="utf-8"))

    print("[normalize] lettura GHL...", file=sys.stderr)
    fields = {f["id"]: f for f in ghl.list_custom_fields()}
    contacts = fetch_all_contacts()
    print(f"[normalize] {len(fields)} campi · {len(contacts)} contatti", file=sys.stderr)

    mode = "APPLY — scrittura reale" if args.apply else "DRY-RUN — nessuna scrittura"
    print(f"\n{'═' * 78}\n  {mode}\n{'═' * 78}")

    totale = 0

    if args.only != "qualifica":
        print("\n### PICKLIST")
        for spec in mappings["campi"]:
            plan = plan_picklist(spec, contacts, fields)
            print_picklist_plan(plan)
            if args.apply and "errore" not in plan:
                totale += apply_picklist(plan)

    if args.only != "picklist":
        print("\n### QUALIFICA FATTURATO")
        plan = plan_qualifica(mappings["qualifica_fatturato"], contacts, fields)
        print_qualifica_plan(plan)
        if args.apply:
            totale += apply_qualifica(plan)

    print(f"\n{'═' * 78}")
    if args.apply:
        print(f"✅ {totale} scritture eseguite.")
        print("   Verifica: python tools/ghl_fields_audit.py")
        print("   Resta da fare a mano: allineare i form GHL (vedi form_da_aggiornare).")
    else:
        print("Nessuna scrittura. Per applicare: --apply")


if __name__ == "__main__":
    try:
        main()
    except ghl.GHLError as exc:
        print(f"[normalize] ❌ errore GHL: {exc}", file=sys.stderr)
        sys.exit(1)
