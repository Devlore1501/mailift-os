"""Vapi API client per la Segretaria Mailift — agente vocale inbound/outbound.

Wrapper minimale sopra l'API Vapi (https://api.vapi.ai). Auth via API key
privata dell'org. Le chiamate outbound partono dal numero italiano importato
da Twilio (VAPI_PHONE_NUMBER_ID).

Variabili .env richieste:
- VAPI_API_KEY: API key privata Vapi
- VAPI_PHONE_NUMBER_ID: id del numero importato (default per outbound)
- VAPI_ASSISTANT_INBOUND_ID: assistant "Segretaria Inbound Mailift"
- VAPI_ASSISTANT_QUALIFICA_ID: assistant "Qualifica Lead" (outbound)
- VAPI_ASSISTANT_REENGAGEMENT_ID: assistant "Riattivazione Lead" (outbound)

Funzioni esposte:
- list_assistants() / get_assistant(id)            → read-only
- list_phone_numbers()                             → read-only
- create_call(numero, assistant_id, ...)           → avvia UNA chiamata (a pagamento)
- create_batch_calls(customers, assistant_id)      → avvia N chiamate (batch nativo)
- get_call(id) / list_calls(...)                   → read-only
- wait_for_call(id)                                → poll fino a status "ended"
- extract_outcome(call)                            → esito normalizzato per GHL

Usato da tools/voice_campaign.py (campagne outbound multi-chiamata) e
workflows/voice_agent.md.

CLI:
    python tools/vapi_client.py test                     # smoke test read-only
    python tools/vapi_client.py call +39333... [--assistant qualifica] [--name "Mario"]
    python tools/vapi_client.py status <call_id>
    python tools/vapi_client.py list [--assistant qualifica]
"""

from __future__ import annotations

import os
import sys
import time as _time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

BASE_URL = "https://api.vapi.ai"

API_KEY = os.environ.get("VAPI_API_KEY")
PHONE_NUMBER_ID = os.environ.get("VAPI_PHONE_NUMBER_ID")

# Registry assistant per chiave logica (usata da voice_campaign.py e CLI)
ASSISTANTS: dict[str, str | None] = {
    "inbound": os.environ.get("VAPI_ASSISTANT_INBOUND_ID"),
    "qualifica": os.environ.get("VAPI_ASSISTANT_QUALIFICA_ID"),
    "reengagement": os.environ.get("VAPI_ASSISTANT_REENGAGEMENT_ID"),
}

# endedReason Vapi che equivalgono a "non ha risposto" (esito non_risponde)
NO_ANSWER_REASONS = (
    "customer-did-not-answer",
    "customer-busy",
    "voicemail",
    "twilio-failed-to-connect-call",
)


class VapiError(Exception):
    """Errore generico API Vapi."""


def _check_credentials() -> None:
    if not API_KEY:
        raise VapiError("VAPI_API_KEY non settata in .env")


def _headers() -> dict[str, str]:
    _check_credentials()
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, *, params: dict | None = None, json: dict | None = None) -> Any:
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.request(
            method, url, headers=_headers(), params=params, json=json, timeout=30
        )
    except requests.RequestException as exc:
        raise VapiError(f"network error: {exc}") from exc

    if resp.status_code >= 400:
        try:
            err_json = resp.json()
        except ValueError:
            err_json = {"raw": resp.text[:500]}
        raise VapiError(
            f"HTTP {resp.status_code} on {method} {path}: {err_json}"
        )

    if not resp.content:
        return {}
    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text}


def resolve_assistant(key_or_id: str) -> str:
    """Risolve una chiave logica ('qualifica') o un id Vapi in assistant id."""
    if key_or_id in ASSISTANTS:
        assistant_id = ASSISTANTS[key_or_id]
        if not assistant_id:
            raise VapiError(
                f"VAPI_ASSISTANT_{key_or_id.upper()}_ID non settata in .env"
            )
        return assistant_id
    return key_or_id


# ─── Assistants / Phone numbers (read-only) ──────────────────────────────────


def list_assistants(limit: int = 20) -> list[dict]:
    """Lista gli assistant dell'org. Read-only."""
    data = _request("GET", "/assistant", params={"limit": limit})
    return data if isinstance(data, list) else data.get("results", [])


def get_assistant(assistant_id: str) -> dict:
    """Dettaglio di un assistant. Read-only."""
    return _request("GET", f"/assistant/{assistant_id}")


def list_phone_numbers() -> list[dict]:
    """Lista i numeri di telefono collegati all'org. Read-only."""
    data = _request("GET", "/phone-number")
    return data if isinstance(data, list) else data.get("results", [])


# ─── Calls ───────────────────────────────────────────────────────────────────


def create_call(
    customer_number: str,
    assistant_id: str,
    *,
    customer_name: str = "",
    phone_number_id: str | None = None,
    metadata: dict | None = None,
    assistant_overrides: dict | None = None,
) -> dict:
    """Avvia UNA chiamata outbound. Side-effect: chiamata reale a pagamento.

    customer_number: formato E.164, es. '+393331234567'
    metadata: dati passanti (es. {"ghl_contact_id": ...}) che ritornano in get_call
    """
    pn_id = phone_number_id or PHONE_NUMBER_ID
    if not pn_id:
        raise VapiError("VAPI_PHONE_NUMBER_ID non settata in .env")

    customer: dict[str, Any] = {"number": customer_number}
    if customer_name:
        customer["name"] = customer_name

    payload: dict[str, Any] = {
        "phoneNumberId": pn_id,
        "assistantId": resolve_assistant(assistant_id),
        "customer": customer,
    }
    if metadata:
        payload["metadata"] = metadata
    if assistant_overrides:
        payload["assistantOverrides"] = assistant_overrides

    return _request("POST", "/call", json=payload)


def create_batch_calls(
    customers: list[dict],
    assistant_id: str,
    *,
    phone_number_id: str | None = None,
    assistant_overrides: dict | None = None,
) -> list[dict]:
    """Avvia N chiamate in un colpo (batch nativo Vapi via array `customers`).

    customers: [{"number": "+39...", "name": "..."}, ...]
    Side-effect: chiamate reali a pagamento. Vapi gestisce la concorrenza
    lato piattaforma (le chiamate oltre il limite vengono accodate).
    """
    pn_id = phone_number_id or PHONE_NUMBER_ID
    if not pn_id:
        raise VapiError("VAPI_PHONE_NUMBER_ID non settata in .env")
    if not customers:
        return []

    payload: dict[str, Any] = {
        "phoneNumberId": pn_id,
        "assistantId": resolve_assistant(assistant_id),
        "customers": customers,
    }
    if assistant_overrides:
        payload["assistantOverrides"] = assistant_overrides

    data = _request("POST", "/call", json=payload)
    # Con `customers` multipli Vapi ritorna {"results": [...]}; con uno solo un dict
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return [data] if isinstance(data, dict) else data


def get_call(call_id: str) -> dict:
    """Dettaglio chiamata (status, transcript, analysis). Read-only."""
    return _request("GET", f"/call/{call_id}")


def list_calls(
    assistant_id: str | None = None,
    limit: int = 20,
    created_at_gt: str | None = None,
) -> list[dict]:
    """Lista chiamate recenti. Read-only.

    created_at_gt: ISO 8601, es. '2026-07-12T00:00:00Z' (solo chiamate dopo).
    """
    params: dict[str, Any] = {"limit": limit}
    if assistant_id:
        params["assistantId"] = resolve_assistant(assistant_id)
    if created_at_gt:
        params["createdAtGt"] = created_at_gt
    data = _request("GET", "/call", params=params)
    return data if isinstance(data, list) else data.get("results", [])


def wait_for_call(call_id: str, timeout: int = 900, poll_every: int = 15) -> dict:
    """Polla get_call finché la chiamata non è terminata (status 'ended').

    Ritorna il dict finale della chiamata; solleva VapiError su timeout.
    """
    deadline = _time.monotonic() + timeout
    while _time.monotonic() < deadline:
        call = get_call(call_id)
        if call.get("status") == "ended":
            return call
        _time.sleep(poll_every)
    raise VapiError(f"timeout ({timeout}s) in attesa di fine chiamata {call_id}")


# ─── Esito normalizzato ──────────────────────────────────────────────────────


def extract_outcome(call: dict) -> dict:
    """Normalizza una chiamata Vapi in un esito pronto per GHL.

    Ritorna:
    {
      "status": "ended" | ...,
      "ended_reason": str,
      "duration_s": int,
      "summary": str,           # analysis.summary (italiano, da summaryPrompt)
      "transcript": str,
      "structured": dict,       # analysis.structuredData (schema analysisPlan)
      "success": Any,           # analysis.successEvaluation
      "esito": "interessato" | "richiamare" | "non_interessato"
               | "segreteria" | "non_risponde" | "sconosciuto",
    }
    """
    analysis = call.get("analysis") or {}
    structured = analysis.get("structuredData") or {}
    ended_reason = call.get("endedReason") or ""

    esito = (structured.get("esito") or "").strip().lower() or "sconosciuto"
    # No-answer/voicemail dal carrier vince sull'analysis (spesso assente)
    if any(reason in ended_reason for reason in NO_ANSWER_REASONS):
        esito = "non_risponde"

    started = call.get("startedAt")
    ended = call.get("endedAt")
    duration_s = 0
    if started and ended:
        try:
            from datetime import datetime

            fmt = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
            duration_s = int((fmt(ended) - fmt(started)).total_seconds())
        except ValueError:
            pass

    return {
        "status": call.get("status", ""),
        "ended_reason": ended_reason,
        "duration_s": duration_s,
        "summary": analysis.get("summary", ""),
        "transcript": call.get("transcript", ""),
        "structured": structured,
        "success": analysis.get("successEvaluation"),
        "esito": esito,
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────


def _smoke_test() -> None:
    print("[vapi] smoke test (read-only)")
    print(f"[vapi] API_KEY          = {API_KEY[:8] if API_KEY else None}...")
    print(f"[vapi] PHONE_NUMBER_ID  = {PHONE_NUMBER_ID}")
    print()

    print("[vapi] GET /phone-number ...")
    numbers = list_phone_numbers()
    print(f"  ✓ {len(numbers)} numeri collegati")
    for n in numbers:
        flag = " ← default outbound" if n.get("id") == PHONE_NUMBER_ID else ""
        print(f"    - {n.get('number', '?')} [{n.get('id', '?')[:8]}...] provider={n.get('provider', '?')}{flag}")
    print()

    print("[vapi] GET /assistant ...")
    assistants = list_assistants()
    print(f"  ✓ {len(assistants)} assistant nell'org")
    by_id = {a.get("id"): a for a in assistants}
    for key, aid in ASSISTANTS.items():
        if not aid:
            print(f"    ⚠️  {key}: VAPI_ASSISTANT_{key.upper()}_ID non settata")
        elif aid in by_id:
            print(f"    ✓ {key}: {by_id[aid].get('name', '?')} [{aid[:8]}...]")
        else:
            print(f"    ❌ {key}: id {aid[:8]}... non trovato nell'org")
    print()
    print("[vapi] ✅ smoke test ok")


def _cli_flag_value(args: list[str], flag: str, default: str = "") -> str:
    if flag in args:
        i = args.index(flag)
        if i + 1 < len(args):
            return args[i + 1]
    return default


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__.split("CLI:")[1].strip())
        sys.exit(2)

    cmd = args[0]
    try:
        if cmd == "test":
            _smoke_test()

        elif cmd == "call":
            if len(args) < 2:
                print("Usage: python tools/vapi_client.py call +39... [--assistant qualifica] [--name X]")
                sys.exit(2)
            number = args[1]
            assistant = _cli_flag_value(args, "--assistant", "qualifica")
            name = _cli_flag_value(args, "--name")
            print(f"⚠️  Sto per avviare una chiamata REALE (a pagamento) a {number}")
            print(f"    assistant: {assistant}")
            call = create_call(number, assistant, customer_name=name)
            print(f"✓ chiamata avviata: id={call.get('id')} status={call.get('status')}")
            print(f"  esito: python tools/vapi_client.py status {call.get('id')}")

        elif cmd == "status":
            if len(args) < 2:
                print("Usage: python tools/vapi_client.py status <call_id>")
                sys.exit(2)
            call = get_call(args[1])
            outcome = extract_outcome(call)
            print(f"status       : {outcome['status']}")
            print(f"ended_reason : {outcome['ended_reason']}")
            print(f"durata       : {outcome['duration_s']}s")
            print(f"esito        : {outcome['esito']}")
            print(f"structured   : {outcome['structured']}")
            print(f"summary      :\n{outcome['summary']}")

        elif cmd == "list":
            assistant = _cli_flag_value(args, "--assistant")
            calls = list_calls(assistant_id=assistant or None)
            print(f"{len(calls)} chiamate recenti:")
            for c in calls:
                num = (c.get("customer") or {}).get("number", "?")
                print(
                    f"  - {c.get('id', '?')[:8]}... {c.get('createdAt', '')[:16]} "
                    f"{num} status={c.get('status')} reason={c.get('endedReason', '')}"
                )

        else:
            print(f"Comando sconosciuto: {cmd}")
            sys.exit(2)

    except VapiError as exc:
        print(f"[vapi] ❌ errore: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
