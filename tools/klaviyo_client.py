"""Klaviyo API client per la Segretaria Mailift.

Wrapper minimale sopra la Klaviyo REST API v2024-10-15. Mailift gestisce
piu' account Klaviyo (uno per cliente: EV8, HCF, Bergamo), quindi il client
e' multi-tenant via parametro `client_slug`.

Variabili .env richieste (una per cliente):
- KLAVIYO_API_KEY_EV8       (per EV8 Style)
- KLAVIYO_API_KEY_HCF       (per HCF)
- KLAVIYO_API_KEY_BERGAMO   (per Bergamo Vini)

Le API key Klaviyo si creano da: Klaviyo → Settings → API Keys → Create
Private API Key. Servono permessi: Read access su Campaigns, Flows, Lists,
Profiles, Segments, Metrics. Non serve write per i workflow attuali (solo
report).

Funzioni esposte:
- list_clients()                              → lista client_slug configurati
- get_account(client_slug)                    → info account (test auth)
- list_campaigns(client_slug, days_back)      → ultime campagne email
- get_campaign(client_slug, campaign_id)      → singola campagna + metrics
- list_flows(client_slug, active_only)        → flussi attivi
- get_flow(client_slug, flow_id)              → singolo flusso + metrics
- query_metric(client_slug, metric_name, ...) → aggregati metrici (Placed Order, Email Revenue, ...)

Usato da: workflows/weekly_klaviyo_report.md

CLI smoke test (read-only):
    python tools/klaviyo_client.py test ev8
    python tools/klaviyo_client.py campaigns ev8 7
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

BASE_URL = "https://a.klaviyo.com/api"
API_REVISION = "2024-10-15"

# Mappa client_slug → env var name
CLIENT_KEY_ENV = {
    "ev8": "KLAVIYO_API_KEY_EV8",
    "hcf": "KLAVIYO_API_KEY_HCF",
    "bergamo": "KLAVIYO_API_KEY_BERGAMO",
}


class KlaviyoError(Exception):
    """Errore generico Klaviyo API."""


def list_clients() -> list[dict]:
    """Ritorna i client configurati con stato della loro chiave (read-only)."""
    out = []
    for slug, env_var in CLIENT_KEY_ENV.items():
        key = os.environ.get(env_var)
        out.append(
            {
                "slug": slug,
                "env_var": env_var,
                "configured": bool(key),
                "key_preview": (key[:10] + "...") if key else None,
            }
        )
    return out


def _get_api_key(client_slug: str) -> str:
    if client_slug not in CLIENT_KEY_ENV:
        raise KlaviyoError(
            f"client_slug sconosciuto: {client_slug!r}. "
            f"Validi: {sorted(CLIENT_KEY_ENV.keys())}"
        )
    env_var = CLIENT_KEY_ENV[client_slug]
    key = os.environ.get(env_var)
    if not key:
        raise KlaviyoError(
            f"{env_var} non settata in .env. "
            f"Crea una Private API Key su Klaviyo (Settings → API Keys) "
            f"per l'account {client_slug.upper()} e mettila in .env."
        )
    return key


def _headers(client_slug: str) -> dict[str, str]:
    return {
        "Authorization": f"Klaviyo-API-Key {_get_api_key(client_slug)}",
        "revision": API_REVISION,
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }


def _request(
    client_slug: str,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
) -> dict:
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.request(
            method, url, headers=_headers(client_slug), params=params, json=json, timeout=30
        )
    except requests.RequestException as exc:
        raise KlaviyoError(f"network error: {exc}") from exc

    if resp.status_code >= 400:
        try:
            err_json = resp.json()
        except ValueError:
            err_json = {"raw": resp.text[:500]}
        raise KlaviyoError(
            f"HTTP {resp.status_code} on {method} {path}: {err_json}"
        )

    if not resp.content:
        return {}
    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text}


# ─── Account ─────────────────────────────────────────────────────────────────


def get_account(client_slug: str) -> dict:
    """Ritorna info dell'account. Smoke-test friendly: verifica solo che la chiave funzioni."""
    data = _request(client_slug, "GET", "/accounts/")
    accounts = data.get("data", [])
    return accounts[0] if accounts else {}


# ─── Campaigns ───────────────────────────────────────────────────────────────


def list_campaigns(
    client_slug: str,
    days_back: int = 7,
    channel: str = "email",
    page_size: int = 50,
) -> list[dict]:
    """Lista le campagne degli ultimi N giorni. Default: ultime 7gg, solo email.

    Klaviyo richiede un filtro su `messages.channel` per /campaigns/.
    Aggiunge filtro su send_time se days_back > 0.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    filter_str = (
        f'and(equals(messages.channel,"{channel}"),'
        f'greater-or-equal(send_time,"{since}"))'
    )
    params = {
        "filter": filter_str,
        "page[size]": page_size,
        "sort": "-send_time",
    }
    all_campaigns: list[dict] = []
    next_url: str | None = None
    while True:
        if next_url:
            # next_url è già completo, fai il request raw
            try:
                resp = requests.get(
                    next_url, headers=_headers(client_slug), timeout=30
                )
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as exc:
                raise KlaviyoError(f"pagination error: {exc}") from exc
        else:
            data = _request(client_slug, "GET", "/campaigns/", params=params)

        all_campaigns.extend(data.get("data", []))
        next_url = (data.get("links") or {}).get("next")
        if not next_url:
            break
    return all_campaigns


def get_campaign(client_slug: str, campaign_id: str) -> dict:
    """Singola campagna con tutti i metadati."""
    data = _request(client_slug, "GET", f"/campaigns/{campaign_id}/")
    return data.get("data", {})


def get_campaign_report(client_slug: str, campaign_id: str) -> dict:
    """Report performance di una campagna (recipients, opens, clicks, revenue, ecc.).

    Endpoint: POST /campaign-values-reports/ con conversion_metric_id.
    Ritorna stats per la campagna in oggetto.
    """
    # Per ora ritorna i metadata della campagna che includono già send_options.
    # Per metriche aggregate complete servirebbe l'endpoint custom Reports →
    # da implementare quando servirà davvero.
    return get_campaign(client_slug, campaign_id)


# ─── Flows ───────────────────────────────────────────────────────────────────


def list_flows(client_slug: str, active_only: bool = True, page_size: int = 50) -> list[dict]:
    """Lista i flussi. Default: solo i `live`."""
    params: dict[str, Any] = {"page[size]": page_size}
    if active_only:
        params["filter"] = 'equals(status,"live")'
    data = _request(client_slug, "GET", "/flows/", params=params)
    return data.get("data", [])


def get_flow(client_slug: str, flow_id: str) -> dict:
    data = _request(client_slug, "GET", f"/flows/{flow_id}/")
    return data.get("data", {})


# ─── Metrics ─────────────────────────────────────────────────────────────────


def list_metrics(client_slug: str, page_size: int = 50) -> list[dict]:
    """Lista tutte le metriche dell'account (Placed Order, Opened Email, ecc.)."""
    data = _request(
        client_slug, "GET", "/metrics/", params={"page[size]": page_size}
    )
    return data.get("data", [])


def query_metric_aggregate(
    client_slug: str,
    metric_id: str,
    measurements: list[str],
    interval: str = "day",
    days_back: int = 7,
    by: list[str] | None = None,
) -> dict:
    """Query aggregato per una metrica.

    measurements es: ["count", "sum_value"]  (sum_value = revenue se la metrica e' Placed Order)
    interval: "hour" | "day" | "week" | "month"
    by: dimensioni opzionali, es ["$attributed_message"] per breakdown per campagna
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    payload = {
        "data": {
            "type": "metric-aggregate",
            "attributes": {
                "metric_id": metric_id,
                "measurements": measurements,
                "interval": interval,
                "filter": [
                    f'greater-or-equal(datetime,{start.isoformat()})',
                    f'less-than(datetime,{end.isoformat()})',
                ],
                "page_size": 500,
                "timezone": "Europe/Rome",
            },
        }
    }
    if by:
        payload["data"]["attributes"]["by"] = by
    return _request(
        client_slug, "POST", "/metric-aggregates/", json=payload
    )


# ─── CLI smoke test ──────────────────────────────────────────────────────────


def _cli() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nClient configurati:")
        for c in list_clients():
            mark = "✅" if c["configured"] else "❌"
            print(f"  {mark} {c['slug']}  ({c['env_var']})")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "clients":
        for c in list_clients():
            mark = "✅" if c["configured"] else "❌"
            preview = c["key_preview"] or "—"
            print(f"  {mark} {c['slug']}  ({c['env_var']})  {preview}")
        return

    if cmd == "test":
        slug = sys.argv[2] if len(sys.argv) > 2 else None
        if not slug:
            print("Usage: python tools/klaviyo_client.py test <slug>")
            sys.exit(2)
        print(f"[klaviyo:{slug}] GET /accounts/")
        try:
            acc = get_account(slug)
            attrs = acc.get("attributes", {})
            print(f"  ✅ id        = {acc.get('id')}")
            print(f"  ✅ company   = {attrs.get('contact_information', {}).get('organization_name', '?')}")
            print(f"  ✅ timezone  = {attrs.get('timezone')}")
            print(f"  ✅ locale    = {attrs.get('preferred_currency')}")
        except KlaviyoError as exc:
            print(f"  ❌ {exc}")
            sys.exit(1)
        return

    if cmd == "campaigns":
        slug = sys.argv[2] if len(sys.argv) > 2 else None
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 7
        if not slug:
            print("Usage: python tools/klaviyo_client.py campaigns <slug> [days_back=7]")
            sys.exit(2)
        try:
            camps = list_campaigns(slug, days_back=days)
            print(f"[klaviyo:{slug}] {len(camps)} campagne ultimi {days}gg")
            for c in camps[:10]:
                attrs = c.get("attributes", {})
                print(
                    f"  {c.get('id', '?')[:8]}... "
                    f"{attrs.get('send_time', '?')[:10]}  "
                    f"{attrs.get('name', '(no name)')[:60]}"
                )
        except KlaviyoError as exc:
            print(f"  ❌ {exc}")
            sys.exit(1)
        return

    if cmd == "flows":
        slug = sys.argv[2] if len(sys.argv) > 2 else None
        if not slug:
            print("Usage: python tools/klaviyo_client.py flows <slug>")
            sys.exit(2)
        try:
            flows = list_flows(slug, active_only=True)
            print(f"[klaviyo:{slug}] {len(flows)} flussi attivi")
            for f in flows[:20]:
                attrs = f.get("attributes", {})
                print(
                    f"  {f.get('id', '?')[:8]}... "
                    f"{attrs.get('status', '?'):10} "
                    f"{attrs.get('name', '(no name)')[:60]}"
                )
        except KlaviyoError as exc:
            print(f"  ❌ {exc}")
            sys.exit(1)
        return

    print(f"Comando sconosciuto: {cmd}")
    print("Comandi: clients | test <slug> | campaigns <slug> [days] | flows <slug>")
    sys.exit(2)


if __name__ == "__main__":
    _cli()
