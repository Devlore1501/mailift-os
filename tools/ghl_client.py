"""GHL (GoHighLevel / LeadConnector) API client per la Segretaria Mailift.

Wrapper minimale sopra l'API LeadConnector v2. Auth via Personal Integration
Token (`pit-...`) scoped a una singola location.

Variabili .env richieste:
- GHL_API_KEY: Personal Integration Token (prefisso `pit-`)
- GHL_LOCATION_ID: ID della location GHL (es. Mailift principale)

Funzioni esposte:
- search_contacts_by_email(email)              → list[dict]
- find_or_create_contact(email, first, last,
    company, source, phone, tags)              → dict (contact)
- get_contact(contact_id)                      → dict
- add_note(contact_id, body)                   → dict
- add_tags(contact_id, tags)                   → dict
- remove_tag(contact_id, tag)                  → dict

Usato da workflows/discovery_call_processing.md (post-call: find/create lead,
classifica HOT/WARM/COLD via tag, aggiunge note briefing).

CLI smoke test (read-only, sicuro):
    python tools/ghl_client.py test
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

BASE_URL = "https://services.leadconnectorhq.com"
API_VERSION = "2021-07-28"

API_KEY = os.environ.get("GHL_API_KEY")
LOCATION_ID = os.environ.get("GHL_LOCATION_ID")


class GHLError(Exception):
    """Errore generico API GHL."""


def _check_credentials() -> None:
    if not API_KEY:
        raise GHLError("GHL_API_KEY non settata in .env")
    if not LOCATION_ID:
        raise GHLError("GHL_LOCATION_ID non settata in .env")


def _headers() -> dict[str, str]:
    _check_credentials()
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Version": API_VERSION,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, *, params: dict | None = None, json: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.request(
            method, url, headers=_headers(), params=params, json=json, timeout=20
        )
    except requests.RequestException as exc:
        raise GHLError(f"network error: {exc}") from exc

    if resp.status_code >= 400:
        try:
            err_json = resp.json()
        except ValueError:
            err_json = {"raw": resp.text[:500]}
        raise GHLError(
            f"HTTP {resp.status_code} on {method} {path}: {err_json}"
        )

    if not resp.content:
        return {}
    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text}


# ─── Location ────────────────────────────────────────────────────────────────


def get_location() -> dict:
    """Ritorna i metadata della location corrente. Smoke-test friendly (read-only)."""
    return _request("GET", f"/locations/{LOCATION_ID}").get("location", {})


# ─── Contacts ────────────────────────────────────────────────────────────────


def search_contacts_by_email(email: str, limit: int = 5) -> list[dict]:
    """Cerca contatti per email. Read-only.

    L'endpoint /contacts/ accetta `query` come search libero che matcha
    email, nome, telefono.
    """
    data = _request(
        "GET",
        "/contacts/",
        params={"locationId": LOCATION_ID, "query": email, "limit": limit},
    )
    return data.get("contacts", [])


def get_contact(contact_id: str) -> dict:
    """Ritorna il contatto completo. Read-only."""
    return _request("GET", f"/contacts/{contact_id}").get("contact", {})


def create_contact(
    email: str = "",
    first_name: str = "",
    last_name: str = "",
    company_name: str = "",
    phone: str = "",
    source: str = "",
    tags: list[str] | None = None,
) -> dict:
    """Crea un nuovo contatto. Side-effect: scrive su GHL."""
    payload: dict[str, Any] = {"locationId": LOCATION_ID}
    if email:
        payload["email"] = email
    if first_name:
        payload["firstName"] = first_name
    if last_name:
        payload["lastName"] = last_name
    if company_name:
        payload["companyName"] = company_name
    if phone:
        payload["phone"] = phone
    if source:
        payload["source"] = source
    if tags:
        payload["tags"] = tags

    return _request("POST", "/contacts/", json=payload).get("contact", {})


def search_contacts_by_name(query: str, limit: int = 5) -> list[dict]:
    """Cerca contatti per nome o azienda. Read-only."""
    data = _request(
        "GET",
        "/contacts/",
        params={"locationId": LOCATION_ID, "query": query, "limit": limit},
    )
    return data.get("contacts", [])


def update_contact(contact_id: str, **fields) -> dict:
    """Aggiorna campi di un contatto esistente. Side-effect."""
    payload = {k: v for k, v in fields.items() if v}
    return _request("PUT", f"/contacts/{contact_id}", json=payload).get("contact", {})


def find_or_create_contact(
    email: str = "",
    first_name: str = "",
    last_name: str = "",
    company_name: str = "",
    phone: str = "",
    source: str = "discovery_call",
    tags: list[str] | None = None,
) -> tuple[dict, bool]:
    """Cerca per email (o nome+azienda se email mancante); se non trovato lo crea.
    Ritorna (contact, was_created)."""
    if email:
        existing = search_contacts_by_email(email)
        for contact in existing:
            if (contact.get("email") or "").lower() == email.lower():
                return contact, False
    else:
        # fallback: cerca per nome o azienda
        query = company_name or f"{first_name} {last_name}".strip()
        if query:
            candidates = search_contacts_by_name(query)
            for contact in candidates:
                cn = (contact.get("companyName") or "").lower()
                fn = (contact.get("firstName") or "").lower()
                ln = (contact.get("lastName") or "").lower()
                if (company_name and company_name.lower() in cn) or (
                    first_name and first_name.lower() in fn and last_name and last_name.lower() in ln
                ):
                    return contact, False

    new_contact = create_contact(
        email=email,
        first_name=first_name,
        last_name=last_name,
        company_name=company_name,
        phone=phone,
        source=source,
        tags=tags,
    )
    return new_contact, True


# ─── Pipelines / Opportunities ────────────────────────────────────────────────


def list_pipelines() -> list[dict]:
    """Lista le pipeline della location. Read-only."""
    data = _request("GET", "/opportunities/pipelines", params={"locationId": LOCATION_ID})
    return data.get("pipelines", [])


def get_opportunities_for_contact(contact_id: str) -> list[dict]:
    """Opportunità associate a un contatto. Read-only."""
    data = _request(
        "GET",
        "/opportunities/search",
        params={"location_id": LOCATION_ID, "contact_id": contact_id, "limit": 10},
    )
    return data.get("opportunities", [])


def create_opportunity(
    contact_id: str,
    pipeline_id: str,
    stage_id: str,
    name: str,
    monetary_value: float = 0,
    status: str = "open",
) -> dict:
    """Crea un'opportunità nella pipeline. Side-effect."""
    payload = {
        "locationId": LOCATION_ID,
        "contactId": contact_id,
        "pipelineId": pipeline_id,
        "pipelineStageId": stage_id,
        "name": name,
        "monetaryValue": monetary_value,
        "status": status,
    }
    return _request("POST", "/opportunities/", json=payload).get("opportunity", {})


def update_opportunity(opportunity_id: str, **fields) -> dict:
    """Aggiorna un'opportunità esistente. Side-effect."""
    return _request("PUT", f"/opportunities/{opportunity_id}", json=fields).get("opportunity", {})


# ─── Notes ───────────────────────────────────────────────────────────────────


def add_note(contact_id: str, body: str) -> dict:
    """Aggiunge una nota a un contatto. Side-effect."""
    return _request(
        "POST",
        f"/contacts/{contact_id}/notes",
        json={"body": body},
    ).get("note", {})


def list_notes(contact_id: str) -> list[dict]:
    """Lista le note di un contatto. Read-only."""
    return _request("GET", f"/contacts/{contact_id}/notes").get("notes", [])


# ─── Automations (Workflows/Flussi) ──────────────────────────────────────────


def list_workflows() -> list[dict]:
    """Lista tutti i flussi/workflow della location. Read-only.

    Nota: l'API GHL non espone i dettagli (step, email, trigger) — solo metadati.
    Per la struttura completa, accedi via UI: https://app.leadconnectorhq.com
    L'endpoint rifiuta parametri extra (es. `limit` → HTTP 422): solo locationId.
    """
    data = _request(
        "GET",
        "/workflows/",
        params={"locationId": LOCATION_ID},
    )
    return data.get("workflows", [])


def find_workflow_by_name(name: str) -> dict | None:
    """Cerca un workflow per nome (case-insensitive). Ritorna il primo match."""
    workflows = list_workflows()
    name_lower = name.lower()
    for wf in workflows:
        if name_lower in wf.get("name", "").lower():
            return wf
    return None


# ─── Tags ────────────────────────────────────────────────────────────────────


def add_tags(contact_id: str, tags: list[str]) -> dict:
    """Aggiunge tag a un contatto (additivo, non sovrascrive). Side-effect."""
    return _request(
        "POST",
        f"/contacts/{contact_id}/tags",
        json={"tags": tags},
    )


def remove_tag(contact_id: str, tag: str) -> dict:
    """Rimuove un singolo tag da un contatto. Side-effect."""
    return _request(
        "DELETE",
        f"/contacts/{contact_id}/tags",
        json={"tags": [tag]},
    )


# ─── CLI smoke test (read-only) ──────────────────────────────────────────────


def _smoke_test() -> None:
    print("[ghl] smoke test (read-only)")
    print(f"[ghl] LOCATION_ID = {LOCATION_ID}")
    print(f"[ghl] API_KEY     = {API_KEY[:10] if API_KEY else None}...")
    print()

    print("[ghl] GET /locations/{id} ...")
    loc = get_location()
    print(f"  ✓ name        = {loc.get('name')}")
    print(f"  ✓ email       = {loc.get('email')}")
    print(f"  ✓ timezone    = {loc.get('timezone')}")
    print()

    print("[ghl] GET /contacts/?query=info@mailift.com (search test) ...")
    results = search_contacts_by_email("info@mailift.com", limit=3)
    print(f"  ✓ trovati {len(results)} contatti")
    for c in results[:3]:
        print(
            f"    - {c.get('id', '?')[:8]}... "
            f"{c.get('firstName', '')} {c.get('lastName', '')} "
            f"<{c.get('email', '')}>"
        )
    print()
    print("[ghl] ✅ smoke test ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        try:
            _smoke_test()
        except GHLError as exc:
            print(f"[ghl] ❌ errore: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Usage: python tools/ghl_client.py test")
        sys.exit(2)
