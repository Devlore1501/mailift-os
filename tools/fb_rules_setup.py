#!/usr/bin/env python3
"""Crea le 3 regole automatiche Facebook Ads per l'account Mailift SLO.

Regole:
  1. Disabilita annuncio: spesa ≥ €35 e 0 acquisti negli ultimi 3 giorni
  2. Disabilita annuncio: spesa ≥ €50 e 0 acquisti negli ultimi 7 giorni
     (Meta non supporta ROAS come filtro nelle regole SCHEDULE)
  3. Notifica: spesa campagna oggi ≥ €75
     (Meta non espone budget% via API; €75 = 150% di un budget tipico da €50)

Note sull'API:
  - I filtri metrici vanno tutti in evaluation_spec.filters (non in filter_spec)
  - spent è in centesimi (35€ = 3500)
  - schedule_spec = {"schedule_type": "SEMI_HOURLY"} è richiesto
  - Operatori validi: GREATER_THAN, LESS_THAN, EQUAL, NOT_EQUAL, IN_RANGE, IN, NOT_IN, CONTAIN

Usage:
    python tools/fb_rules_setup.py          # crea le regole
    python tools/fb_rules_setup.py list     # elenca regole esistenti
    python tools/fb_rules_setup.py delete RULE_ID  # elimina una regola
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

TOKEN    = os.environ.get("FB_ACCESS_TOKEN", "")
ACCT_RAW = os.environ.get("FB_AD_ACCOUNT_ID", "")
ACCT     = f"act_{ACCT_RAW}" if ACCT_RAW and not ACCT_RAW.startswith("act_") else ACCT_RAW
API_VER  = "v21.0"
BASE     = f"https://graph.facebook.com/{API_VER}"


USER_ID = "1702400747586545"  # Lorenzo — da /me con il token

def _exec_pause() -> dict:
    return {
        "execution_type": "PAUSE",
        "execution_options": [
            {"field": "user_ids", "value": [USER_ID], "operator": "EQUAL"},
            {"field": "alert_preferences", "value": {"instant": {"trigger": "CHANGE"}}, "operator": "EQUAL"},
        ],
    }

def _exec_notify() -> dict:
    return {
        "execution_type": "NOTIFICATION",
        "execution_options": [
            {"field": "user_ids", "value": [USER_ID], "operator": "EQUAL"},
            {"field": "alert_preferences", "value": {"instant": {"trigger": "CHANGE"}}, "operator": "EQUAL"},
        ],
    }

SCHED_SPEC = json.dumps({"schedule_type": "SEMI_HOURLY"})

def _post_rule(name: str, eval_filters: list[dict], exec_spec: dict) -> dict:
    """Tutti i filtri (metriche + entity_type + time_preset) vanno in evaluation_spec.filters."""
    url = f"{BASE}/{ACCT}/adrules_library"
    payload = {
        "name":            name,
        "evaluation_spec": json.dumps({"evaluation_type": "SCHEDULE", "filters": eval_filters}),
        "execution_spec":  json.dumps(exec_spec),
        "schedule_spec":   SCHED_SPEC,
        "status":          "ENABLED",
        "access_token":    TOKEN,
    }
    r = requests.post(url, data=payload, timeout=20)
    return r.json()


def create_rules() -> None:
    if not TOKEN or not ACCT:
        print("❌ FB_ACCESS_TOKEN o FB_AD_ACCOUNT_ID mancanti nel .env")
        sys.exit(1)

    print(f"[fb-rules] Creazione regole per {ACCT}...\n")

    # ── Regola 1: spesa ≥ 35€ e 0 acquisti → disabilita (ultimi 3 giorni) ──
    # spent in centesimi: 35€ = 3500
    r1 = _post_rule(
        name="[Mailift] Disabilita: spesa ≥35€ senza acquisti (3gg)",
        eval_filters=[
            {"field": "spent",       "value": "3500", "operator": "GREATER_THAN"},
            {"field": "result",      "value": "1",    "operator": "LESS_THAN"},
            {"field": "entity_type", "value": "AD",   "operator": "EQUAL"},
            {"field": "time_preset", "value": "LAST_3D", "operator": "EQUAL"},
        ],
        exec_spec=_exec_pause(),
    )
    _print_result("Regola 1 (spesa≥35, 0 acquisti)", r1)

    # ── Regola 2: spesa ≥ 50€ e 0 acquisti negli ultimi 7 giorni → disabilita ──
    # Meta non supporta ROAS come filtro in regole SCHEDULE; questa è l'approssimazione
    # pratica: se hai speso €50 senza acquisti in 7 giorni, il ROAS è 0.
    r2 = _post_rule(
        name="[Mailift] Disabilita: spesa ≥50€ senza acquisti (7gg)",
        eval_filters=[
            {"field": "spent",       "value": "5000", "operator": "GREATER_THAN"},
            {"field": "result",      "value": "1",    "operator": "LESS_THAN"},
            {"field": "entity_type", "value": "AD",   "operator": "EQUAL"},
            {"field": "time_preset", "value": "LAST_7D", "operator": "EQUAL"},
        ],
        exec_spec=_exec_pause(),
    )
    _print_result("Regola 2 (spesa≥50, 0 acquisti 7gg)", r2)

    # ── Regola 3: spesa campagna oggi ≥ €75 → notifica ──
    # Meta non espone budget_ratio via API; €75 ≈ 150% di un budget tipico da €50/gg.
    # Aggiusta 'value' in base al tuo budget effettivo.
    r3 = _post_rule(
        name="[Mailift] Notifica: spesa campagna oggi ≥ €75",
        eval_filters=[
            {"field": "spent",       "value": "7500",    "operator": "GREATER_THAN"},
            {"field": "entity_type", "value": "CAMPAIGN", "operator": "EQUAL"},
            {"field": "time_preset", "value": "TODAY",    "operator": "EQUAL"},
        ],
        exec_spec=_exec_notify(),
    )
    _print_result("Regola 3 (spesa campagna ≥ €75 oggi)", r3)


def _print_result(label: str, resp: dict) -> None:
    if "id" in resp:
        print(f"  ✓ {label} → ID: {resp['id']}")
    else:
        err = resp.get("error", resp)
        print(f"  ✗ {label}")
        print(f"    Errore: {err.get('message', json.dumps(err))}")
        if err.get("error_user_msg"):
            print(f"    Dettaglio: {err['error_user_msg']}")
    print()


def list_rules() -> None:
    url = f"{BASE}/{ACCT}/adrules_library"
    r = requests.get(url, params={"access_token": TOKEN, "fields": "id,name,status"}, timeout=20)
    data = r.json()
    rules = data.get("data", [])
    if not rules:
        print("Nessuna regola trovata.")
        return
    print(f"{'ID':<20} {'Status':<10} Nome")
    print("-" * 70)
    for rule in rules:
        print(f"{rule['id']:<20} {rule.get('status',''):<10} {rule.get('name','')}")


def delete_rule(rule_id: str) -> None:
    url = f"{BASE}/{rule_id}"
    r = requests.delete(url, params={"access_token": TOKEN}, timeout=20)
    if r.json().get("success"):
        print(f"✓ Regola {rule_id} eliminata.")
    else:
        print(f"✗ {r.json()}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "create"
    if cmd == "list":
        list_rules()
    elif cmd == "delete" and len(sys.argv) > 2:
        delete_rule(sys.argv[2])
    else:
        create_rules()
