"""Client Klaviyo per-brand: legge segmenti, liste e performance campagne.

Ogni brand ha la propria private API key (salvata sul Brand). Tutte le
chiamate sono read-only. Le metriche campagna arrivano dal reporting API
(campaign-values-reports); se non disponibili si degrada senza errore.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests

BASE_URL = "https://a.klaviyo.com/api"
API_REVISION = "2024-10-15"
TIMEOUT = 30


class KlaviyoError(Exception):
    pass


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Klaviyo-API-Key {api_key}",
        "revision": API_REVISION,
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }


def _get(api_key: str, path: str, params: dict | None = None) -> dict:
    resp = requests.get(
        f"{BASE_URL}{path}", headers=_headers(api_key), params=params, timeout=TIMEOUT
    )
    if resp.status_code >= 400:
        raise KlaviyoError(f"Klaviyo {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def get_account(api_key: str) -> dict:
    data = _get(api_key, "/accounts/")
    accounts = data.get("data", [])
    if not accounts:
        raise KlaviyoError("Nessun account Klaviyo per questa chiave")
    attrs = accounts[0].get("attributes", {})
    contact = attrs.get("contact_information", {}) or {}
    return {
        "id": accounts[0].get("id"),
        "name": contact.get("organization_name") or attrs.get("test_account", "Account"),
    }


def _list_segments_paginated(api_key: str, extra_params: dict | None) -> list[dict]:
    out: list[dict] = []
    # alcuni account limitano page[size] a 10: si pagina seguendo links.next
    params: dict | None = {"page[size]": 10, **(extra_params or {})}
    url_path = "/segments/"
    while True:
        data = _get(api_key, url_path, params)
        for seg in data.get("data", []):
            attrs = seg.get("attributes", {})
            out.append(
                {
                    "klaviyo_id": seg.get("id"),
                    "name": attrs.get("name", ""),
                    "profile_count": attrs.get("profile_count"),
                }
            )
        next_url = (data.get("links") or {}).get("next")
        if not next_url or len(out) >= 200:
            break
        # links.next è un URL assoluto: estraiamo il path+query
        url_path = next_url.replace(BASE_URL, "")
        params = None
    return out


def list_segments(api_key: str) -> list[dict]:
    # profile_count sulla lista non è supportato da tutte le revision/account:
    # prova, e in caso di 400 rileggi senza e recupera i conteggi per-segmento.
    try:
        return _list_segments_paginated(
            api_key, {"additional-fields[segment]": "profile_count"}
        )
    except KlaviyoError as e:
        if "400" not in str(e):
            raise
    segments = _list_segments_paginated(api_key, None)
    for seg in segments[:30]:  # cap per non esaurire i rate limit
        try:
            data = _get(
                api_key,
                f"/segments/{seg['klaviyo_id']}/",
                {"additional-fields[segment]": "profile_count"},
            )
            attrs = (data.get("data") or {}).get("attributes", {})
            seg["profile_count"] = attrs.get("profile_count")
        except KlaviyoError:
            pass  # il conteggio resta None, il resto dello snapshot è valido
    return segments


def list_recent_campaigns(api_key: str, days_back: int = 60) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    params: dict | None = {
        "filter": (
            f"and(equals(messages.channel,'email'),"
            f"greater-than(scheduled_at,{since}))"
        ),
        "sort": "-scheduled_at",
        "page[size]": 10,
    }
    out: list[dict] = []
    url_path = "/campaigns/"
    while True:
        data = _get(api_key, url_path, params)
        for c in data.get("data", []):
            attrs = c.get("attributes", {})
            out.append(
                {
                    "klaviyo_id": c.get("id"),
                    "name": attrs.get("name", ""),
                    "sent_at": attrs.get("send_time") or attrs.get("scheduled_at"),
                    "status": attrs.get("status", ""),
                }
            )
        next_url = (data.get("links") or {}).get("next")
        if not next_url or len(out) >= 25:
            break
        url_path = next_url.replace(BASE_URL, "")
        params = None
    return out[:25]


def campaign_metrics(api_key: str, campaign_ids: list[str]) -> dict[str, dict]:
    """Best-effort: usa il reporting API per open/click/revenue per campagna."""
    if not campaign_ids:
        return {}
    # serve l'id della metrica "Placed Order" per conversion_metric_id
    try:
        metrics = _get(api_key, "/metrics/", {"filter": "equals(name,'Placed Order')"})
        placed_order = next((m["id"] for m in metrics.get("data", [])), None)
    except KlaviyoError:
        placed_order = None
    if not placed_order:
        return {}
    payload = {
        "data": {
            "type": "campaign-values-report",
            "attributes": {
                "timeframe": {"key": "last_12_months"},
                "conversion_metric_id": placed_order,
                "filter": "contains-any(campaign_id,{})".format(
                    "[" + ",".join(f'"{cid}"' for cid in campaign_ids[:25]) + "]"
                ),
                "statistics": [
                    "open_rate",
                    "click_rate",
                    "recipients",
                    "conversion_value",
                ],
            },
        }
    }
    try:
        resp = requests.post(
            f"{BASE_URL}/campaign-values-reports/",
            headers=_headers(api_key),
            json=payload,
            timeout=60,
        )
        if resp.status_code >= 400:
            return {}
        results = resp.json().get("data", {}).get("attributes", {}).get("results", [])
    except requests.RequestException:
        return {}
    out: dict[str, dict] = {}
    for r in results:
        cid = (r.get("groupings") or {}).get("campaign_id")
        stats = r.get("statistics") or {}
        if cid:
            out[cid] = {
                "open_rate": stats.get("open_rate"),
                "click_rate": stats.get("click_rate"),
                "recipients": stats.get("recipients"),
                "revenue": stats.get("conversion_value"),
            }
    return out


def _engagement_health(avg_open: float | None) -> str:
    if avg_open is None:
        return "unknown"
    if avg_open >= 0.35:
        return "good"
    if avg_open >= 0.20:
        return "average"
    return "poor"


def build_snapshot(api_key: str) -> dict[str, Any]:
    """Sincronizza e costruisce lo snapshot usato dal planner."""
    account = get_account(api_key)
    segments = list_segments(api_key)
    campaigns = list_recent_campaigns(api_key)
    metrics = campaign_metrics(api_key, [c["klaviyo_id"] for c in campaigns])

    for c in campaigns:
        m = metrics.get(c["klaviyo_id"], {})
        c.update(
            {
                "recipients": m.get("recipients"),
                "open_rate": m.get("open_rate"),
                "click_rate": m.get("click_rate"),
                "revenue": m.get("revenue"),
            }
        )

    opens = [c["open_rate"] for c in campaigns if c.get("open_rate") is not None]
    clicks = [c["click_rate"] for c in campaigns if c.get("click_rate") is not None]
    revenue_30d = sum(
        c["revenue"]
        for c in campaigns
        if c.get("revenue") is not None and _within_days(c.get("sent_at"), 30)
    )
    campaigns_30d = sum(1 for c in campaigns if _within_days(c.get("sent_at"), 30))
    avg_open = round(sum(opens) / len(opens), 4) if opens else None
    avg_click = round(sum(clicks) / len(clicks), 4) if clicks else None

    total_profiles = max(
        (s["profile_count"] for s in segments if s.get("profile_count")), default=None
    )

    recommendations = []
    health = _engagement_health(avg_open)
    if health == "good":
        recommendations.append(
            f"Open rate medio {avg_open:.0%}: lista sana, la frequenza attuale regge bene."
        )
    elif health == "average":
        recommendations.append(
            f"Open rate medio {avg_open:.0%}: alternare contenuto puro e promo, "
            "evitare più di una promo aggressiva a settimana."
        )
    elif health == "poor":
        recommendations.append(
            f"Open rate medio {avg_open:.0%} basso: prevedere email di re-engagement "
            "e restringere gli invii ai segmenti engaged."
        )
    unengaged = [
        s
        for s in segments
        if s.get("profile_count")
        and any(k in s["name"].lower() for k in ("unengaged", "inactive", "inattiv", "dorm"))
    ]
    for s in unengaged[:2]:
        recommendations.append(
            f"Segmento '{s['name']}' con {s['profile_count']} profili: pianificare re-engagement."
        )

    return {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "account_name": account["name"],
        "total_profiles": total_profiles,
        "segments": segments,
        "campaigns": campaigns,
        "metrics_summary": {
            "avg_open_rate": avg_open,
            "avg_click_rate": avg_click,
            "total_revenue_30d": round(revenue_30d, 2) if revenue_30d else 0.0,
            "campaigns_last_30d": campaigns_30d,
            "engagement_health": health,
        },
        "recommendations": recommendations,
    }


def _within_days(iso: str | None, days: int) -> bool:
    if not iso:
        return False
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return False
    return dt >= datetime.now(timezone.utc) - timedelta(days=days)
