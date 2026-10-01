"""lod_ghl_schema.py — Campi personalizzati e tag GHL per la review call di Lead on Demand.

Definisce lo schema (workflows/lod_weekly_call_review.md) e lo confronta con quello
presente in GHL. Per impostazione predefinita non scrive nulla.

Usage:
    python tools/lod_ghl_schema.py            # mostra cosa manca (sola lettura)
    python tools/lod_ghl_schema.py --apply    # crea i campi mancanti su GHL
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ghl_client as ghl

MOTIVI_PERDITA = [
    "prezzo", "pagamento-anticipato", "fiducia-prova", "zona-esclusiva", "capacita",
    "decisore", "timing", "esperienza-passata", "garanzia-risultati", "organico-pieno",
    "silenzio-post-call", "fuori-target", "concorrente", "non-determinabile",
]
MOTIVI_CHIUSURA = [
    "test-basso-rischio", "esclusiva", "prequalifica-telefonica", "fiducia-persona",
    "urgenza-reale", "prova-documentata",
]
MOTIVI = MOTIVI_PERDITA + MOTIVI_CHIUSURA

ESITI = [
    "call-fissata", "proposta-inviata", "firmato-attesa-pagamento", "pagato",
    "rinviato", "non-chiuso", "perso", "non-raggiunto", "no-show", "da-verificare",
]

# (nome campo, tipo GHL, opzioni)
FIELDS: list[tuple[str, str, list[str] | None]] = [
    ("LOD Esito", "SINGLE_OPTIONS", ESITI),
    ("LOD Stato firma", "SINGLE_OPTIONS", ["nessuna", "proposta", "firmato"]),
    ("LOD Stato pagamento", "SINGLE_OPTIONS", ["nessuno", "atteso", "ricevuto"]),
    ("LOD Motivo primario", "SINGLE_OPTIONS", MOTIVI),
    ("LOD Motivo secondario", "SINGLE_OPTIONS", MOTIVI),
    ("LOD Obiezione", "LARGE_TEXT", None),
    ("LOD Voto discovery", "NUMERICAL", None),
    ("LOD Voto obiezione", "NUMERICAL", None),
    ("LOD Voto next step", "NUMERICAL", None),
    ("LOD Passi prequalifica", "TEXT", None),
    ("LOD Promesse a rischio", "LARGE_TEXT", None),
    ("LOD Pacchetto", "TEXT", None),
    ("LOD Zona", "TEXT", None),
    ("LOD Data ricontatto", "DATE", None),
    ("LOD Tipo ricontatto", "SINGLE_OPTIONS",
     ["telefonata", "email", "sms", "whatsapp-manuale", "nessuno"]),
    ("LOD Ultima call data", "DATE", None),
    ("LOD Ultima call tipo", "SINGLE_OPTIONS",
     ["prequalifica", "discovery-vendita", "follow-up", "onboarding"]),
    ("LOD Link registrazione", "TEXT", None),
    ("LOD Affidabilita analisi", "SINGLE_OPTIONS", ["alta", "media", "bassa"]),
]

# Convenzione tag
TAG_PREFIXES = {
    "esito": "lod-esito-",
    "motivo": "lod-motivo-",
    "cohort": "lod-cohort-",       # lod-cohort-YYYY-MM, dal mese di creazione
}
TAG_PROMESSE = "lod-promesse-da-controllare"
TAG_DA_RICONTATTARE = "lod-da-ricontattare"


def field_ids_by_name() -> dict[str, str]:
    return {f["name"]: f["id"] for f in ghl.list_custom_fields()}


def plan() -> list[tuple[str, str, list[str] | None]]:
    existing = {f["name"] for f in ghl.list_custom_fields()}
    return [f for f in FIELDS if f[0] not in existing]


def main() -> None:
    missing = plan()
    print(f"Campi definiti: {len(FIELDS)} | gia presenti: {len(FIELDS) - len(missing)} | da creare: {len(missing)}")
    for name, dtype, opts in missing:
        extra = f" ({len(opts)} opzioni)" if opts else ""
        print(f"  - {name}: {dtype}{extra}")
    if "--apply" not in sys.argv:
        print("\nSola lettura. Per creare i campi: --apply")
        return
    for name, dtype, opts in missing:
        created = ghl.create_custom_field(name, dtype, opts)
        print(f"  creato {name} -> {created.get('id')}")


if __name__ == "__main__":
    main()
