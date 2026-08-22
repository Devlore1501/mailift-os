"""Microsoft Clarity — Data Export API client per la Segretaria Mailift.

Wrapper minimale sopra l'API "Project Live Insights" di Microsoft Clarity.
Auth via token JWT (scope `Data.Export`, read-only, dati AGGREGATI).

Cosa fa Clarity: MISURA il comportamento reale degli utenti su una pagina
(scroll depth, engagement, dead/rage/error click, quick-back, errori JS,
browser/OS/device, sorgenti). NON simula e NON fa A/B test: è misurazione.

Limiti dell'API (imposti da Microsoft):
- max 3 giorni di storico (`num_of_days` = 1..3)
- max 10 richieste per progetto al giorno
- max 3 dimensioni per chiamata (es. Browser, Device, Country/Region,
  OS, Source, Medium, Campaign, Channel, URL, Referrer, Page Title)
- dati AGGREGATI (niente sessioni singole via API: heatmap e recording
  restano solo nella dashboard clarity.microsoft.com)

Variabile .env richiesta:
- CLARITY_API_TOKEN: token JWT generato in Clarity → Settings → Data Export

Funzioni esposte:
- live_insights(num_of_days=1, dimensions=None)  → list[dict] (raw metrics)
- summary(num_of_days=1, dimensions=None)         → dict (metriche appiattite)

CLI smoke test (read-only, consuma 1 delle 10 richieste/giorno):
    python tools/clarity_client.py                 # summary ultimi 1 giorno
    python tools/clarity_client.py 3 Source Device # 3 giorni, per sorgente+device
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_URL = "https://www.clarity.ms/export-data/api/v1/project-live-insights"

# Dimensioni valide accettate dall'API (per validazione lato client).
VALID_DIMENSIONS = {
    "Browser", "Device", "Country/Region", "OS", "Source", "Medium",
    "Campaign", "Channel", "URL", "Referrer", "PageTitle",
}


def _token() -> str:
    token = os.getenv("CLARITY_API_TOKEN")
    if not token:
        raise RuntimeError(
            "CLARITY_API_TOKEN mancante in .env. "
            "Generalo in Clarity → Settings → Data Export."
        )
    return token


def live_insights(
    num_of_days: int = 1,
    dimensions: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Ritorna le metriche aggregate grezze (lista di metricName)."""
    if num_of_days not in (1, 2, 3):
        raise ValueError("num_of_days deve essere 1, 2 o 3 (limite API Clarity).")

    dimensions = dimensions or []
    if len(dimensions) > 3:
        raise ValueError("Max 3 dimensioni per chiamata (limite API Clarity).")

    params: dict[str, str] = {"numOfDays": str(num_of_days)}
    for i, dim in enumerate(dimensions, start=1):
        if dim not in VALID_DIMENSIONS:
            raise ValueError(
                f"Dimensione '{dim}' non valida. Valide: {sorted(VALID_DIMENSIONS)}"
            )
        params[f"dimension{i}"] = dim

    resp = requests.get(
        API_URL,
        headers={"Authorization": f"Bearer {_token()}"},
        params=params,
        timeout=30,
    )
    if resp.status_code == 401:
        raise RuntimeError("401: token Clarity non valido o scaduto.")
    if resp.status_code == 403:
        raise RuntimeError(
            "403: limite di 10 richieste/giorno superato, oppure scope errato."
        )
    resp.raise_for_status()
    return resp.json()


def summary(
    num_of_days: int = 1,
    dimensions: list[str] | None = None,
) -> dict[str, Any]:
    """Appiattisce le metriche chiave in un dict leggibile (senza dimensioni).

    Se `dimensions` è passato, ritorna comunque il raw sotto la chiave `raw`.
    """
    data = live_insights(num_of_days, dimensions)
    out: dict[str, Any] = {"num_of_days": num_of_days, "raw": data}

    by_name = {m.get("metricName"): m.get("information", []) for m in data}

    traffic = (by_name.get("Traffic") or [{}])[0]
    engagement = (by_name.get("EngagementTime") or [{}])[0]
    scroll = (by_name.get("ScrollDepth") or [{}])[0]

    def pct(metric: str) -> float | None:
        info = by_name.get(metric) or [{}]
        return info[0].get("sessionsWithMetricPercentage")

    out["kpi"] = {
        "sessions": traffic.get("totalSessionCount"),
        "bot_sessions": traffic.get("totalBotSessionCount"),
        "distinct_users": traffic.get("distinctUserCount"),
        "pages_per_session": traffic.get("pagesPerSessionPercentage"),
        "avg_scroll_depth_pct": scroll.get("averageScrollDepth"),
        "total_time_s": engagement.get("totalTime"),
        "active_time_s": engagement.get("activeTime"),
        "dead_click_pct": pct("DeadClickCount"),
        "rage_click_pct": pct("RageClickCount"),
        "error_click_pct": pct("ErrorClickCount"),
        "quickback_pct": pct("QuickbackClick"),
        "excessive_scroll_pct": pct("ExcessiveScroll"),
        "script_error_pct": pct("ScriptErrorCount"),
    }
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    days = int(args[0]) if args and args[0].isdigit() else 1
    dims = [a for a in args if not a.isdigit()] or None
    result = summary(days, dims)
    print(json.dumps(result["kpi"], indent=2, ensure_ascii=False))
    if dims:
        print("\n--- raw (con dimensioni) ---")
        print(json.dumps(result["raw"], indent=2, ensure_ascii=False))
