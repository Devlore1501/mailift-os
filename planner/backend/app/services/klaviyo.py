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


def _paginate(
    api_key: str,
    path: str,
    param_attempts: list[dict],
    cap: int,
) -> tuple[list[dict], dict]:
    """Fetch tollerante: prova le combinazioni di parametri in ordine (dalla
    più ricca alla minima) e usa la prima che l'API accetta — ogni account
    Klaviyo espone limiti diversi su page[size], additional-fields, sort e
    filtri. Poi segue links.next fino al cap.

    Ritorna (risorse JSON:API grezze, parametri effettivamente usati).
    """
    last_err: KlaviyoError | None = None
    for params in param_attempts:
        try:
            first = _get(api_key, path, params or None)
        except KlaviyoError as e:
            if "Klaviyo 400" in str(e):
                last_err = e
                continue  # input non valido per questo account: prova la variante dopo
            raise
        out = list(first.get("data", []))
        next_url = (first.get("links") or {}).get("next")
        while next_url and len(out) < cap:
            data = _get(api_key, next_url.replace(BASE_URL, ""), None)
            out.extend(data.get("data", []))
            next_url = (data.get("links") or {}).get("next")
        return out[:cap], params
    raise last_err or KlaviyoError(f"Nessuna variante di richiesta accettata per {path}")


def list_segments(api_key: str) -> list[dict]:
    attempts = [
        {"page[size]": 10, "additional-fields[segment]": "profile_count"},
        {"additional-fields[segment]": "profile_count"},
        {"page[size]": 10},
        {},
    ]
    raw, used = _paginate(api_key, "/segments/", attempts, cap=200)
    segments = [
        {
            "klaviyo_id": seg.get("id"),
            "name": (seg.get("attributes") or {}).get("name", ""),
            "profile_count": (seg.get("attributes") or {}).get("profile_count"),
        }
        for seg in raw
    ]
    # Se la lista non includeva i conteggi, recuperali per-segmento (best effort)
    if "additional-fields[segment]" not in used:
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
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    since = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    channel = "equals(messages.channel,'email')"
    dated = f"and({channel},greater-than(scheduled_at,{since}))"
    # il filtro sul canale è obbligatorio per l'endpoint campaigns
    attempts = [
        {"filter": dated, "sort": "-scheduled_at"},
        {"filter": dated},
        {"filter": channel, "sort": "-scheduled_at"},
        {"filter": channel},
    ]
    raw, used = _paginate(api_key, "/campaigns/", attempts, cap=100)
    out = []
    for c in raw:
        attrs = c.get("attributes", {})
        out.append(
            {
                "klaviyo_id": c.get("id"),
                "name": attrs.get("name", ""),
                "sent_at": attrs.get("send_time") or attrs.get("scheduled_at"),
                "status": attrs.get("status", ""),
            }
        )
    # Se l'API non ha accettato il filtro per data, filtra e ordina lato client
    if "greater-than" not in (used.get("filter") or ""):
        out = [c for c in out if _within_days(c.get("sent_at"), days_back)] or out
    out.sort(key=lambda c: c.get("sent_at") or "", reverse=True)
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
