"""Webhook server per l'agente vocale Vapi — appointment setter Mailift.

Espone gli endpoint che l'assistant Vapi chiama durante/dopo la chiamata:

- POST /vapi/tool-calls     → tool custom in tempo reale durante la call
                              (check_availability, book_appointment)
- POST /vapi/server-events  → eventi di fine chiamata (end-of-call-report)
                              per loggare esito/trascrizione su GHL

Deve essere raggiungibile via HTTPS pubblico da Vapi. Per test locali usa
ngrok (`ngrok http 8000`) e incolla l'URL come Server URL dell'assistant
su Vapi. Per produzione va deployato (Render/Railway/Fly.io) — non è
automatizzabile da qui, richiede un account di hosting.

Variabili .env richieste:
- GHL_API_KEY, GHL_LOCATION_ID     (tools/ghl_client.py, ghl_calendar_client.py)
- GHL_CALENDAR_ID                  ID del calendario "Discovery Call"
- VAPI_SERVER_SECRET (opzionale)   se impostato, valida l'header
                                    X-Vapi-Secret sulle richieste in arrivo

Avvio locale:
    uvicorn tools.vapi_webhook_server:app --reload --port 8000

NOTA implementativa: lo schema esatto di `message.analysis` nel payload
end-of-call-report (summary/structuredData/successEvaluation) non è
completamente documentato pubblicamente da Vapi — verificare il payload
reale alla prima chiamata di test (loggarlo, vedi `_log_raw_payload`) e
aggiustare `_extract_outcome` di conseguenza.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request

from tools.ghl_calendar_client import book_appointment, get_free_slots
from tools.ghl_client import GHLError, add_note, add_tags, find_or_create_contact

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vapi_webhook")

app = FastAPI(title="Mailift Vapi Webhook")

GHL_CALENDAR_ID = os.environ.get("GHL_CALENDAR_ID")
VAPI_SERVER_SECRET = os.environ.get("VAPI_SERVER_SECRET")

RAW_LOG_DIR = Path(".tmp/vapi_raw_payloads")
RAW_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _check_secret(x_vapi_secret: str | None) -> None:
    if VAPI_SERVER_SECRET and x_vapi_secret != VAPI_SERVER_SECRET:
        raise HTTPException(status_code=401, detail="invalid server secret")


def _log_raw_payload(name: str, payload: dict) -> None:
    """Salva il payload grezzo per ispezione manuale (debug schema Vapi)."""
    import json

    path = RAW_LOG_DIR / f"{name}_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


# ─── Tool calls (durante la chiamata) ───────────────────────────────────────


def _handle_check_availability(args: dict) -> str:
    days_ahead = int(args.get("days_ahead", 5))
    now = datetime.now()
    try:
        slots_by_day = get_free_slots(GHL_CALENDAR_ID, now, now + timedelta(days=days_ahead))
    except GHLError as exc:
        logger.error("check_availability GHL error: %s", exc)
        return "Al momento non riesco a leggere il calendario, proponi di richiamare più tardi."

    flat = [s for day in sorted(slots_by_day) for s in slots_by_day[day]][:3]
    if not flat:
        return "Nessuno slot libero nei prossimi giorni, proponi al lead una richiamata da parte di Lorenzo."
    return "Slot disponibili: " + "; ".join(flat)


def _handle_book_appointment(args: dict) -> str:
    required = ["contact_phone", "start_time", "end_time", "lead_name"]
    missing = [k for k in required if not args.get(k)]
    if missing:
        return f"Mancano informazioni per fissare l'appuntamento: {', '.join(missing)}"

    try:
        contact, _created = find_or_create_contact(
            phone=args["contact_phone"],
            first_name=args.get("lead_name", ""),
            source="vapi-outbound-setter",
        )
        appointment = book_appointment(
            calendar_id=GHL_CALENDAR_ID,
            contact_id=contact["id"],
            start_time=args["start_time"],
            end_time=args["end_time"],
            title=f"Discovery call — {args.get('lead_name', 'Lead')} (via Vapi)",
        )
        add_tags(contact_id=contact["id"], tags=["setter-booked"])
    except GHLError as exc:
        logger.error("book_appointment GHL error: %s", exc)
        return "Non sono riuscito a confermare la prenotazione sul calendario, proponi una richiamata manuale."

    return f"Appuntamento confermato per {args['start_time']} (id: {appointment.get('id', 'n/d')})"


TOOL_HANDLERS = {
    "check_availability": _handle_check_availability,
    "book_appointment": _handle_book_appointment,
}


@app.post("/vapi/tool-calls")
async def tool_calls(request: Request, x_vapi_secret: str | None = Header(default=None)):
    _check_secret(x_vapi_secret)
    payload = await request.json()
    _log_raw_payload("tool_calls", payload)

    tool_call_list = payload.get("message", {}).get("toolCallList", [])
    results = []
    for call in tool_call_list:
        name = call.get("name")
        args = call.get("arguments", {})
        handler = TOOL_HANDLERS.get(name)
        result = handler(args) if handler else f"Tool sconosciuto: {name}"
        results.append({"toolCallId": call.get("id"), "result": result})

    return {"results": results}


# ─── Server events (fine chiamata) ──────────────────────────────────────────


def _extract_outcome(message: dict) -> str:
    """Deduce un tag esito dalla fine-chiamata. Verificare/estendere dopo
    aver ispezionato i payload reali salvati in .tmp/vapi_raw_payloads/."""
    ended_reason = (message.get("endedReason") or "").lower()
    analysis = message.get("analysis", {}) or {}
    success = analysis.get("successEvaluation")

    if "voicemail" in ended_reason:
        return "setter-voicemail"
    if "no-answer" in ended_reason or "busy" in ended_reason:
        return "setter-no-answer"
    if success is False:
        return "setter-not-interested"
    if success is True:
        return "setter-booked"
    return "setter-da-rivedere"


@app.post("/vapi/server-events")
async def server_events(request: Request, x_vapi_secret: str | None = Header(default=None)):
    _check_secret(x_vapi_secret)
    payload = await request.json()
    message = payload.get("message", {})

    if message.get("type") != "end-of-call-report":
        return {"status": "ignored"}

    _log_raw_payload("end_of_call_report", payload)

    call = message.get("call", {})
    customer_number = call.get("customer", {}).get("number")
    metadata = call.get("metadata", {}) or {}
    transcript = message.get("artifact", {}).get("transcript", "")
    summary = (message.get("analysis", {}) or {}).get("summary", "")
    outcome_tag = _extract_outcome(message)

    if not customer_number:
        logger.warning("end-of-call-report senza numero cliente, skip GHL sync")
        return {"status": "no_customer_number"}

    try:
        contact, _created = find_or_create_contact(
            phone=customer_number,
            first_name=metadata.get("lead_name", ""),
            source="vapi-outbound-setter",
        )
        note_body = (
            f"## Chiamata outbound AI — {datetime.now():%Y-%m-%d %H:%M}\n\n"
            f"**Esito:** {outcome_tag}\n\n"
            f"**Riepilogo:** {summary or 'non disponibile'}\n\n"
            f"**Trascrizione:**\n{transcript}"
        )
        add_note(contact_id=contact["id"], body=note_body)
        add_tags(contact_id=contact["id"], tags=[outcome_tag])
    except GHLError as exc:
        logger.error("server_events GHL sync error: %s", exc)
        return {"status": "ghl_error", "detail": str(exc)}

    return {"status": "ok", "contact_id": contact["id"], "outcome": outcome_tag}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
