"""GHL Calendars API client (LeadConnector v2) — disponibilità e booking.

Estende tools/ghl_client.py con gli endpoint Calendars, usati dal setter
vocale Vapi per proporre e fissare appuntamenti (discovery call) senza che
Lorenzo debba intervenire manualmente.

Variabili .env richieste (già presenti per ghl_client.py):
- GHL_API_KEY: Personal Integration Token (prefisso `pit-`)
- GHL_LOCATION_ID: ID della location GHL

Funzioni esposte:
- list_calendars()                                   → list[dict]
- get_calendar_by_name(name)                          → dict | None
- get_free_slots(calendar_id, start_date, end_date)   → dict[str, list[str]]
- book_appointment(calendar_id, contact_id, start,
    end, title)                                       → dict

CLI smoke test (read-only, sicuro):
    python tools/ghl_calendar_client.py test
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta

from tools.ghl_client import LOCATION_ID, GHLError, _request

# ─── Calendars ───────────────────────────────────────────────────────────────


def list_calendars() -> list[dict]:
    """Ritorna tutti i calendari della location. Read-only."""
    data = _request("GET", "/calendars/", params={"locationId": LOCATION_ID})
    return data.get("calendars", [])


def get_calendar_by_name(name: str) -> dict | None:
    """Cerca un calendario per nome esatto (case-insensitive). Read-only."""
    for cal in list_calendars():
        if cal.get("name", "").strip().lower() == name.strip().lower():
            return cal
    return None


def get_free_slots(
    calendar_id: str,
    start_date: datetime,
    end_date: datetime,
    timezone: str = "Europe/Rome",
) -> dict[str, list[str]]:
    """Ritorna gli slot liberi nel range dato. Read-only.

    L'API GHL vuole start/end come epoch millisecondi. Il risultato è un
    dict `{"YYYY-MM-DD": {"slots": [iso_datetime, ...]}}`; qui lo appiattiamo
    a `{"YYYY-MM-DD": [iso_datetime, ...]}` per comodità del chiamante.
    """
    params = {
        "startDate": int(start_date.timestamp() * 1000),
        "endDate": int(end_date.timestamp() * 1000),
        "timezone": timezone,
    }
    data = _request("GET", f"/calendars/{calendar_id}/free-slots", params=params)
    return {
        day: payload.get("slots", [])
        for day, payload in data.items()
        if isinstance(payload, dict)
    }


def get_next_free_slots(
    calendar_id: str, days_ahead: int = 7, timezone: str = "Europe/Rome", limit: int = 3
) -> list[str]:
    """Comodità: primi `limit` slot liberi nei prossimi `days_ahead` giorni."""
    now = datetime.now()
    slots_by_day = get_free_slots(calendar_id, now, now + timedelta(days=days_ahead), timezone)
    flat: list[str] = []
    for day in sorted(slots_by_day):
        flat.extend(slots_by_day[day])
    return flat[:limit]


# ─── Appointments ────────────────────────────────────────────────────────────


def book_appointment(
    calendar_id: str,
    contact_id: str,
    start_time: str,
    end_time: str,
    title: str,
    appointment_status: str = "confirmed",
) -> dict:
    """Fissa un appuntamento sul calendario GHL. AZIONE LIVE — scrive sul CRM.

    `start_time` / `end_time`: ISO 8601 con offset (es. quelli ritornati da
    `get_free_slots`). `appointment_status`: "confirmed" | "new" | "cancelled".
    """
    body = {
        "calendarId": calendar_id,
        "locationId": LOCATION_ID,
        "contactId": contact_id,
        "startTime": start_time,
        "endTime": end_time,
        "title": title,
        "appointmentStatus": appointment_status,
        "ignoreDateRange": False,
        "toNotify": True,
    }
    return _request("POST", "/calendars/events/appointments", json=body)


def cancel_appointment(appointment_id: str) -> dict:
    """Annulla un appuntamento. AZIONE LIVE."""
    return _request(
        "PUT",
        f"/calendars/events/appointments/{appointment_id}",
        json={"appointmentStatus": "cancelled"},
    )


# ─── Smoke test ──────────────────────────────────────────────────────────────


def _smoke_test() -> None:
    print("→ list_calendars()")
    calendars = list_calendars()
    if not calendars:
        print("  Nessun calendario trovato (verifica GHL_LOCATION_ID).")
        return
    for cal in calendars:
        print(f"  - {cal.get('name')} ({cal.get('id')})")

    first = calendars[0]
    print(f"\n→ get_next_free_slots('{first.get('name')}')")
    try:
        slots = get_next_free_slots(first["id"])
        for s in slots:
            print(f"  - {s}")
        if not slots:
            print("  Nessuno slot libero nei prossimi 7 giorni.")
    except GHLError as exc:
        print(f"  Errore: {exc}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        _smoke_test()
    else:
        print("Uso: python tools/ghl_calendar_client.py test")
