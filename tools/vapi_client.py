"""Vapi API client — creazione assistant e lancio chiamate outbound.

Usato dal setter vocale AI (workflows/voice_ai_appointment_setter.md) per:
1. Creare/aggiornare l'assistant (prompt, voce, tool custom verso GHL)
2. Lanciare chiamate outbound verso lead qualificati
3. Leggere lo stato di una call

Variabili .env richieste:
- VAPI_API_KEY: Private API Key dalla dashboard Vapi (Settings → API Keys)

Setup manuale richiesto PRIMA di usare questo client (non automatizzabile
da qui — serve account + pagamento):
1. Crea account su https://vapi.ai
2. Importa il numero italiano Twilio in Vapi (Phone Numbers → Import) →
   annota il `phoneNumberId` ritornato
3. Copia la Private API Key in VAPI_API_KEY

Funzioni esposte:
- list_phone_numbers()                                → list[dict]
- create_assistant(config)                             → dict
- update_assistant(assistant_id, config)               → dict
- create_outbound_call(assistant_id, phone_number_id,
    customer_number, metadata)                         → dict
- get_call(call_id)                                    → dict

CLI smoke test (read-only, sicuro):
    python tools/vapi_client.py test
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

BASE_URL = "https://api.vapi.ai"
API_KEY = os.environ.get("VAPI_API_KEY")


class VapiError(Exception):
    """Errore generico API Vapi."""


def _headers() -> dict[str, str]:
    if not API_KEY:
        raise VapiError("VAPI_API_KEY non settata in .env")
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def _request(method: str, path: str, *, params: dict | None = None, json: dict | None = None) -> Any:
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.request(method, url, headers=_headers(), params=params, json=json, timeout=30)
    except requests.RequestException as exc:
        raise VapiError(f"network error: {exc}") from exc

    if resp.status_code >= 400:
        try:
            err_json = resp.json()
        except ValueError:
            err_json = {"raw": resp.text[:500]}
        raise VapiError(f"HTTP {resp.status_code} on {method} {path}: {err_json}")

    if not resp.content:
        return {}
    return resp.json()


# ─── Phone numbers ───────────────────────────────────────────────────────────


def list_phone_numbers() -> list[dict]:
    """Ritorna i numeri importati/posseduti su Vapi. Read-only."""
    return _request("GET", "/phone-number")


# ─── Assistants ──────────────────────────────────────────────────────────────


def create_assistant(config: dict) -> dict:
    """Crea un assistant Vapi. AZIONE LIVE.

    `config` segue lo schema Vapi Assistant (model, voice, firstMessage,
    serverUrl, serverUrlSecret, ecc). Vedi
    workflows/voice_ai_appointment_setter.md per il config di riferimento.
    """
    return _request("POST", "/assistant", json=config)


def update_assistant(assistant_id: str, config: dict) -> dict:
    """Aggiorna un assistant esistente. AZIONE LIVE."""
    return _request("PATCH", f"/assistant/{assistant_id}", json=config)


def get_assistant(assistant_id: str) -> dict:
    """Legge la config di un assistant. Read-only."""
    return _request("GET", f"/assistant/{assistant_id}")


# ─── Calls ───────────────────────────────────────────────────────────────────


def create_outbound_call(
    assistant_id: str,
    phone_number_id: str,
    customer_number: str,
    metadata: dict | None = None,
) -> dict:
    """Lancia una chiamata outbound. AZIONE LIVE — chiama un numero reale.

    `customer_number` in formato E.164 (es. "+393401234567").
    `metadata` viene passato al webhook end-of-call-report per correlare
    la call al contatto/lead GHL (es. {"ghl_contact_id": "..."}).
    """
    body = {
        "assistantId": assistant_id,
        "phoneNumberId": phone_number_id,
        "customer": {"number": customer_number},
    }
    if metadata:
        body["metadata"] = metadata
    return _request("POST", "/call", json=body)


def get_call(call_id: str) -> dict:
    """Legge stato/esito di una call. Read-only."""
    return _request("GET", f"/call/{call_id}")


# ─── Smoke test ──────────────────────────────────────────────────────────────


def _smoke_test() -> None:
    print("→ list_phone_numbers()")
    try:
        numbers = list_phone_numbers()
    except VapiError as exc:
        print(f"  Errore: {exc}")
        return
    if not numbers:
        print("  Nessun numero importato su Vapi.")
        return
    for n in numbers:
        print(f"  - {n.get('number')} ({n.get('id')}) — provider: {n.get('provider')}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        _smoke_test()
    else:
        print("Uso: python tools/vapi_client.py test")
