"""Google Calendar API client per la Segretaria Mailift.

Wrapper minimale sopra Google Calendar API v3. Riusa le credenziali OAuth
Desktop di Gmail (`credentials_gmail.json`), ma con un token separato
`tokens/gcal.json` perche' lo scope e' diverso.

Variabili .env (con default sensati):
- GMAIL_CREDENTIALS_FILE  (gia' presente, riusato)
- GCAL_TOKEN_FILE         default: tokens/gcal.json
- GCAL_CALENDAR_ID        default: primary
- GCAL_TIMEZONE           default: Europe/Rome

Setup iniziale (una volta):
    python tools/gcal_oauth_setup.py

Funzioni esposte:
- get_service()                          → service Google Calendar autenticato
- list_events(time_min, time_max, ...)   → eventi nel range temporale
- list_today()                            → eventi di oggi (helper)
- list_week()                             → eventi della settimana corrente
- find_free_slots(start, end, ...)        → slot liberi nella finestra
- create_event(summary, start, end, ...)  → crea un evento
- delete_event(event_id)                  → cancella un evento (USE WITH CARE)

Usato da: workflows/replan_calendar.md, workflows/discovery_call_processing.md

CLI smoke test (read-only):
    python tools/gcal_client.py today
    python tools/gcal_client.py week
    python tools/gcal_client.py free 09:00 19:00 60   # slot liberi domani 9-19, durata 60min
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

# Scope: read + write events sul calendario primario
SCOPES = ["https://www.googleapis.com/auth/calendar"]

DEFAULT_CALENDAR_ID = os.environ.get("GCAL_CALENDAR_ID", "primary")
DEFAULT_TZ = os.environ.get("GCAL_TIMEZONE", "Europe/Rome")


class GCalError(Exception):
    """Errore generico Google Calendar."""


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (PROJECT_ROOT / p)


def credentials_path() -> Path:
    return _resolve(os.environ.get("GMAIL_CREDENTIALS_FILE", "credentials_gmail.json"))


def token_path() -> Path:
    return _resolve(os.environ.get("GCAL_TOKEN_FILE", "tokens/gcal.json"))


def get_service():
    """Costruisce il service Google Calendar dal token salvato.

    Auto-refresh del token se scaduto. Solleva GCalError se il token
    non esiste o e' invalido (in quel caso lancia gcal_oauth_setup.py).
    """
    tpath = token_path()
    if not tpath.exists():
        raise GCalError(
            f"Token Google Calendar mancante: {tpath}. "
            "Lancia: python tools/gcal_oauth_setup.py"
        )

    creds = Credentials.from_authorized_user_file(str(tpath), SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            tpath.write_text(creds.to_json())
        else:
            raise GCalError(
                "Credenziali Google Calendar invalide o scadute. "
                "Rilancia: python tools/gcal_oauth_setup.py --force"
            )

    return build("calendar", "v3", credentials=creds, cache_discovery=False)


# ─── List events ─────────────────────────────────────────────────────────────


def list_events(
    time_min: datetime,
    time_max: datetime,
    calendar_id: str = DEFAULT_CALENDAR_ID,
    max_results: int = 250,
    service=None,
) -> list[dict]:
    """Lista eventi nel range [time_min, time_max). Naive datetimes interpretati come Europe/Rome."""
    if service is None:
        service = get_service()

    tz = ZoneInfo(DEFAULT_TZ)
    if time_min.tzinfo is None:
        time_min = time_min.replace(tzinfo=tz)
    if time_max.tzinfo is None:
        time_max = time_max.replace(tzinfo=tz)

    try:
        result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except HttpError as exc:
        raise GCalError(f"GCal API error: {exc}") from exc

    return result.get("items", [])


def list_today(service=None) -> list[dict]:
    """Eventi di oggi (00:00 → 23:59:59) Europe/Rome."""
    tz = ZoneInfo(DEFAULT_TZ)
    today = date.today()
    start = datetime.combine(today, time.min, tzinfo=tz)
    end = datetime.combine(today, time.max, tzinfo=tz)
    return list_events(start, end, service=service)


def list_week(service=None) -> list[dict]:
    """Eventi della settimana corrente (lun 00:00 → dom 23:59) Europe/Rome."""
    tz = ZoneInfo(DEFAULT_TZ)
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    start = datetime.combine(monday, time.min, tzinfo=tz)
    end = datetime.combine(sunday, time.max, tzinfo=tz)
    return list_events(start, end, service=service)


# ─── Find free slots ─────────────────────────────────────────────────────────


def find_free_slots(
    start: datetime,
    end: datetime,
    duration_minutes: int,
    work_start_hour: int = 9,
    work_end_hour: int = 19,
    skip_lunch: bool = True,
    skip_weekends: bool = True,
    calendar_id: str = DEFAULT_CALENDAR_ID,
    service=None,
) -> list[tuple[datetime, datetime]]:
    """Trova slot liberi nella finestra [start, end] di durata duration_minutes.

    Vincoli applicati di default:
    - Solo orario di lavoro (9-19 Europe/Rome)
    - Pranzo 13:00-14:00 escluso (skip_lunch=True)
    - Weekend esclusi (skip_weekends=True)

    Ritorna una lista di (slot_start, slot_end). Risoluzione: 15 min.
    """
    if service is None:
        service = get_service()

    tz = ZoneInfo(DEFAULT_TZ)
    if start.tzinfo is None:
        start = start.replace(tzinfo=tz)
    if end.tzinfo is None:
        end = end.replace(tzinfo=tz)

    busy = list_events(start, end, calendar_id=calendar_id, service=service)
    # Estrai (start, end) di ogni evento. Skip all-day (date only)
    busy_intervals: list[tuple[datetime, datetime]] = []
    for ev in busy:
        s = ev.get("start", {})
        e = ev.get("end", {})
        if "dateTime" not in s or "dateTime" not in e:
            # Evento all-day → blocca tutto il giorno
            try:
                d = date.fromisoformat(s.get("date", ""))
                bs = datetime.combine(d, time.min, tzinfo=tz)
                be = datetime.combine(d, time.max, tzinfo=tz)
                busy_intervals.append((bs, be))
            except (ValueError, TypeError):
                continue
            continue
        bs = datetime.fromisoformat(s["dateTime"]).astimezone(tz)
        be = datetime.fromisoformat(e["dateTime"]).astimezone(tz)
        busy_intervals.append((bs, be))

    # Genera tutti gli slot candidati
    slots: list[tuple[datetime, datetime]] = []
    duration = timedelta(minutes=duration_minutes)
    cursor = start

    while cursor + duration <= end:
        # Skip weekend
        if skip_weekends and cursor.weekday() >= 5:
            # vai al prossimo lunedi
            days_to_monday = 7 - cursor.weekday()
            cursor = (
                datetime.combine(
                    (cursor + timedelta(days=days_to_monday)).date(),
                    time(work_start_hour, 0),
                    tzinfo=tz,
                )
            )
            continue

        # Skip orari fuori work hours
        if cursor.hour < work_start_hour:
            cursor = cursor.replace(hour=work_start_hour, minute=0, second=0, microsecond=0)
            continue
        if cursor.hour >= work_end_hour:
            # vai al giorno dopo work_start
            next_day = cursor.date() + timedelta(days=1)
            cursor = datetime.combine(next_day, time(work_start_hour, 0), tzinfo=tz)
            continue

        # Skip pausa pranzo
        if skip_lunch and cursor.hour == 13:
            cursor = cursor.replace(hour=14, minute=0)
            continue

        slot_end = cursor + duration

        # Controlla che lo slot non sconfini oltre work_end
        if slot_end.hour > work_end_hour or (
            slot_end.hour == work_end_hour and slot_end.minute > 0
        ):
            next_day = cursor.date() + timedelta(days=1)
            cursor = datetime.combine(next_day, time(work_start_hour, 0), tzinfo=tz)
            continue

        # Controlla che lo slot non sconfini in pausa pranzo
        if skip_lunch and slot_end.hour == 13 and slot_end.minute > 0:
            cursor = cursor.replace(hour=14, minute=0)
            continue

        # Controlla collisioni con eventi busy
        collision = False
        for bs, be in busy_intervals:
            if cursor < be and slot_end > bs:
                collision = True
                # Salta oltre la fine dell'evento
                cursor = be
                break

        if not collision:
            slots.append((cursor, slot_end))
            cursor = slot_end

    return slots


# ─── Create / delete events ──────────────────────────────────────────────────


def create_event(
    summary: str,
    start: datetime,
    end: datetime,
    description: str = "",
    location: str = "",
    attendees: list[str] | None = None,
    calendar_id: str = DEFAULT_CALENDAR_ID,
    color_id: str | None = None,
    service=None,
) -> dict:
    """Crea un evento sul calendario. Side-effect: scrive su GCal."""
    if service is None:
        service = get_service()

    tz = ZoneInfo(DEFAULT_TZ)
    if start.tzinfo is None:
        start = start.replace(tzinfo=tz)
    if end.tzinfo is None:
        end = end.replace(tzinfo=tz)

    body: dict[str, Any] = {
        "summary": summary,
        "start": {"dateTime": start.isoformat(), "timeZone": DEFAULT_TZ},
        "end": {"dateTime": end.isoformat(), "timeZone": DEFAULT_TZ},
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees]
    if color_id:
        body["colorId"] = color_id

    try:
        return service.events().insert(calendarId=calendar_id, body=body).execute()
    except HttpError as exc:
        raise GCalError(f"create_event failed: {exc}") from exc


def delete_event(
    event_id: str,
    calendar_id: str = DEFAULT_CALENDAR_ID,
    service=None,
) -> None:
    """Cancella un evento. ATTENZIONE: irreversibile."""
    if service is None:
        service = get_service()
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except HttpError as exc:
        raise GCalError(f"delete_event failed: {exc}") from exc


# ─── CLI ─────────────────────────────────────────────────────────────────────


def _format_event_line(ev: dict) -> str:
    s = ev.get("start", {})
    if "dateTime" in s:
        dt = datetime.fromisoformat(s["dateTime"]).astimezone(ZoneInfo(DEFAULT_TZ))
        time_str = dt.strftime("%a %d/%m %H:%M")
    elif "date" in s:
        time_str = f"all-day {s['date']}"
    else:
        time_str = "?"
    return f"  {time_str}  {ev.get('summary', '(no title)')[:60]}"


def _cli() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    try:
        if cmd == "today":
            evs = list_today()
            print(f"[gcal] eventi oggi: {len(evs)}")
            for ev in evs:
                print(_format_event_line(ev))
            return

        if cmd == "week":
            evs = list_week()
            print(f"[gcal] eventi questa settimana: {len(evs)}")
            for ev in evs:
                print(_format_event_line(ev))
            return

        if cmd == "free":
            # Args: start_hour end_hour duration_minutes
            #       (default: domani 9-19, 60 min)
            tz = ZoneInfo(DEFAULT_TZ)
            tomorrow = date.today() + timedelta(days=1)
            sh = int(sys.argv[2].split(":")[0]) if len(sys.argv) > 2 else 9
            eh = int(sys.argv[3].split(":")[0]) if len(sys.argv) > 3 else 19
            dur = int(sys.argv[4]) if len(sys.argv) > 4 else 60
            start = datetime.combine(tomorrow, time(sh, 0), tzinfo=tz)
            end = datetime.combine(tomorrow + timedelta(days=4), time(eh, 0), tzinfo=tz)
            slots = find_free_slots(start, end, dur)
            print(
                f"[gcal] slot liberi prossimi 5gg "
                f"({sh:02d}:00-{eh:02d}:00, {dur}min): {len(slots)}"
            )
            for s, e in slots[:20]:
                print(f"  {s.strftime('%a %d/%m %H:%M')} - {e.strftime('%H:%M')}")
            if len(slots) > 20:
                print(f"  ... + altri {len(slots) - 20}")
            return

        if cmd == "test":
            # Solo verifica auth: lista 1 evento
            service = get_service()
            evs = list_today(service=service)
            print(f"[gcal] ✅ auth OK, {len(evs)} eventi oggi")
            return

        print(f"Comando sconosciuto: {cmd}")
        print("Comandi: today | week | free [start_h] [end_h] [dur_min] | test")
        sys.exit(2)

    except GCalError as exc:
        print(f"[gcal] ❌ {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
