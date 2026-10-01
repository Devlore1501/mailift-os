"""Crea in GHL i custom field del questionario di onboarding lead gen.

Specifica: clients/_mailift-team/ghl-questionario-onboarding-lead-gen.md
Idempotente: salta i campi la cui fieldKey (contact.<chiave>) esiste già (l'API antepone da sola "contact.").

Variabili richieste (ambiente o .env): GHL_API_KEY, GHL_LOCATION_ID.

Uso:
    python tools/ghl_setup_onboarding_fields.py --dry-run   # elenca cosa creerebbe
    python tools/ghl_setup_onboarding_fields.py             # crea i campi mancanti
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

BASE_URL = "https://services.leadconnectorhq.com"
API_VERSION = "2021-07-28"
API_KEY = os.environ.get("GHL_API_KEY")
LOCATION_ID = os.environ.get("GHL_LOCATION_ID")

CRITERIO = ["Obbligatorio", "Desiderabile", "Eliminatorio", "Non rilevante"]

# (chiave, etichetta, dataType, opzioni)
FIELDS: list[tuple[str, str, str, list[str] | None]] = [
    # Passo 1
    ("ob_ragione_sociale", "OB Ragione sociale", "TEXT", None),
    ("ob_ref_commerciale", "OB Referente commerciale", "TEXT", None),
    ("ob_tel_commerciale", "OB Telefono referente commerciale", "PHONE", None),
    ("ob_ref_amministrativo", "OB Referente amministrativo", "TEXT", None),
    ("ob_email_alert", "OB Email per avviso nuovo lead", "TEXT", None),
    ("ob_whatsapp_alert", "OB WhatsApp per avviso nuovo lead", "TEXT", None),
    ("ob_decisore_messaggio", "OB Chi decide sul messaggio degli annunci", "TEXT", None),
    # Passo 2
    ("ob_formula", "OB Formula con cui chiudete", "CHECKBOX",
     ["Noleggio operativo", "Acquisto diretto", "Finanziamento", "Bandi e incentivi", "Altro"]),
    ("ob_formula_altro", "OB Formula, altro", "TEXT", None),
    ("ob_formula_frase", "OB Formula spiegata in una frase", "LARGE_TEXT", None),
    ("ob_numero_trattativa", "OB Numero concreto in trattativa", "LARGE_TEXT", None),
    ("ob_no_promesse", "OB Promesse da NON fare negli annunci", "LARGE_TEXT", None),
    ("ob_lead_altra_formula", "OB Lead che preferisce un'altra formula", "RADIO",
     ["Sì", "No", "Solo se..."]),
    ("ob_lead_altra_formula_cond", "OB Condizioni per altra formula", "TEXT", None),
    # Passo 3
    ("ob_diretti", "OB Installatori diretti o intermediari", "RADIO",
     ["Diretti", "Intermediari", "Entrambi"]),
    ("ob_numeri_fiducia", "OB Numeri verificabili", "LARGE_TEXT", None),
    ("ob_link_prove", "OB Link a recensioni e casi", "LARGE_TEXT", None),
    ("ob_foto_lavori", "OB Foto di lavori reali", "FILE_UPLOAD", None),
    ("ob_logo", "OB Logo alta risoluzione", "FILE_UPLOAD", None),
    ("ob_esperienze_negative", "OB Esperienze negative con agenzie o concorrenti", "LARGE_TEXT", None),
    # Passo 4
    ("ob_target_ideale", "OB Cliente ideale", "LARGE_TEXT", None),
    ("ob_soglia_minima", "OB Soglia minima di consumo o spesa", "TEXT", None),
    ("ob_zone_priorita", "OB Zone prioritarie", "LARGE_TEXT", None),
    ("ob_zone_limitrofe", "OB Zone limitrofe accettabili", "LARGE_TEXT", None),
    ("ob_zone_escluse", "OB Zone escluse", "TEXT", None),
    ("ob_target_escluso", "OB Chi NON volete", "LARGE_TEXT", None),
    ("ob_decisore_tipo", "OB Chi decide in azienda", "CHECKBOX",
     ["Amministratore", "Titolare", "Energy manager", "Responsabile acquisti", "Varia"]),
    ("ob_min_appuntamenti_zona", "OB Minimo appuntamenti per zona", "NUMERICAL", None),
    # Passo 5
    ("ob_q_soglia", "OB Qualifica, soglia di spesa", "RADIO", CRITERIO),
    ("ob_q_sito", "OB Qualifica, condizione del sito", "RADIO", CRITERIO),
    ("ob_q_esclusione", "OB Qualifica, elemento di esclusione", "RADIO", CRITERIO),
    ("ob_q_solvibilita", "OB Qualifica, solvibilità", "RADIO", CRITERIO),
    ("ob_q_decisore", "OB Qualifica, decisore coinvolto", "RADIO", CRITERIO),
    ("ob_q_documento", "OB Qualifica, copia documento", "RADIO", CRITERIO),
    ("ob_q_appuntamento", "OB Qualifica, disponibilità all'appuntamento", "RADIO", CRITERIO),
    ("ob_q_altri", "OB Altri criteri eliminatori", "LARGE_TEXT", None),
    ("ob_chi_solvibilita", "OB Chi verifica la solvibilità", "RADIO", ["Voi", "Noi", "Entrambi"]),
    ("ob_lead_vietati", "OB Lead da non ricevere mai", "LARGE_TEXT", None),
    ("ob_esempio_lead_buono", "OB Esempio di lead buono", "LARGE_TEXT", None),
    ("ob_esempio_lead_cattivo", "OB Esempio di lead che ha fatto perdere tempo", "LARGE_TEXT", None),
    # Passo 6
    ("ob_obiezioni", "OB Obiezioni più frequenti", "LARGE_TEXT", None),
    ("ob_perche_non_comprano", "OB Perché chi non ha comprato non l'ha fatto", "LARGE_TEXT", None),
    ("ob_motivazioni_acquisto", "OB Motivazioni all'acquisto", "LARGE_TEXT", None),
    ("ob_argomento_chiusura", "OB Argomento di chiusura", "LARGE_TEXT", None),
    # Passo 7
    ("ob_formato_consegna", "OB Formato di consegna dei lead", "RADIO",
     ["Foglio Excel/Google Sheets condiviso", "CRM", "Solo email", "Altro"]),
    ("ob_formato_dettaglio", "OB Dettaglio CRM o altro", "TEXT", None),
    ("ob_email_foglio", "OB Email Google per accesso al foglio", "TEXT", None),
    ("ob_campi_extra", "OB Campi extra nel foglio", "LARGE_TEXT", None),
    ("ob_sla_ricontatto", "OB Tempo di ricontatto lead", "RADIO",
     ["Entro 1 ora", "Entro 4 ore", "Entro 24 ore", "Non c'è una regola"]),
    ("ob_chi_fissa", "OB Chi fissa l'appuntamento", "RADIO",
     ["Il vostro commerciale", "Noi per conto vostro"]),
    ("ob_contestazioni", "OB Gestione lead non validi", "LARGE_TEXT", None),
    # Passo 8
    ("ob_volume_max", "OB Lead al mese gestibili", "NUMERICAL", None),
    ("ob_volume_target", "OB Lead desiderati primo mese", "NUMERICAL", None),
    ("ob_data_inizio", "OB Data di inizio", "DATE", None),
    ("ob_dati_fattura", "OB Dati per fattura", "LARGE_TEXT", None),
    ("ob_pagato", "OB Pagamento effettuato", "RADIO", ["Sì", "No", "In corso"]),
    ("ob_contabile", "OB Contabile pagamento", "FILE_UPLOAD", None),
    ("ob_note_finali", "OB Note finali", "LARGE_TEXT", None),
    ("ob_conferma_criteri", "OB Conferma criteri di valutazione lead", "CHECKBOX",
     ["Confermo"]),
]


def headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Version": API_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def existing_keys() -> set[str]:
    r = requests.get(
        f"{BASE_URL}/locations/{LOCATION_ID}/customFields",
        params={"model": "contact"},
        headers=headers(),
        timeout=30,
    )
    r.raise_for_status()
    return {c.get("fieldKey", "") for c in r.json().get("customFields", [])}


FOLDER_NAME = "Onboarding lead gen"


def get_or_create_folder() -> str:
    """Cartella custom field del contatto (l'API la crea con documentType=folder)."""
    r = requests.get(
        f"{BASE_URL}/locations/{LOCATION_ID}/customFields",
        params={"model": "contact"},
        headers=headers(),
        timeout=30,
    )
    r.raise_for_status()
    for c in r.json().get("customFields", []):
        if c.get("documentType") == "folder" and c.get("name") == FOLDER_NAME:
            return c["id"]
    r = requests.post(
        f"{BASE_URL}/locations/{LOCATION_ID}/customFields",
        json={"name": FOLDER_NAME, "model": "contact", "documentType": "folder"},
        headers=headers(),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["customFieldFolder"]["id"]


def create(key: str, name: str, data_type: str, options: list[str] | None, folder_id: str) -> requests.Response:
    body: dict = {
        "name": name,
        "dataType": data_type,
        "model": "contact",
        "fieldKey": key,
        "parentId": folder_id,
    }
    if options:
        body["options"] = options
    return requests.post(
        f"{BASE_URL}/locations/{LOCATION_ID}/customFields",
        json=body,
        headers=headers(),
        timeout=30,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not API_KEY or not LOCATION_ID:
        print("GHL_API_KEY e GHL_LOCATION_ID devono essere impostate", file=sys.stderr)
        return 1

    have = existing_keys()
    todo = [f for f in FIELDS if f"contact.{f[0]}" not in have]
    print(f"{len(FIELDS)} campi in specifica, {len(FIELDS) - len(todo)} già presenti, {len(todo)} da creare")

    folder_id = "" if args.dry_run or not todo else get_or_create_folder()
    failed = 0
    for key, name, dtype, opts in todo:
        if args.dry_run:
            print(f"  [dry-run] {key} ({dtype})")
            continue
        r = create(key, name, dtype, opts, folder_id)
        if r.ok:
            print(f"  creato  {key} ({dtype})")
        else:
            failed += 1
            print(f"  ERRORE  {key} ({dtype}): HTTP {r.status_code} {r.text[:200]}")
        time.sleep(0.15)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
