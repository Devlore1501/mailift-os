#!/usr/bin/env python3
"""GHL API endpoint discovery — probe per trovare il percorso corretto ai workflows."""

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


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Version": API_VERSION,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def probe_endpoint(method: str, path: str, params: dict | None = None) -> dict:
    """Test un endpoint e riporta il risultato."""
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.request(
            method, url, headers=_headers(), params=params, timeout=10
        )
        return {
            "status": resp.status_code,
            "ok": resp.status_code < 400,
            "path": path,
            "method": method,
            "response": resp.json() if resp.content else {},
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "ok": False,
            "path": path,
            "method": method,
            "error": str(e),
        }


# Endpoints da testare
endpoints = [
    # Workflows / Automazioni
    ("GET", "/workflows/", {}),
    ("GET", f"/workflows/?locationId={LOCATION_ID}", {}),
    ("GET", "/automations/", {"locationId": LOCATION_ID}),
    ("GET", "/campaigns/", {"locationId": LOCATION_ID}),
    ("GET", "/funnels/", {"locationId": LOCATION_ID}),
    ("GET", "/templates/", {"locationId": LOCATION_ID}),
    # Varianti con locationId nel path
    (
        "GET",
        f"/locations/{LOCATION_ID}/automations",
        {},
    ),
    ("GET", f"/locations/{LOCATION_ID}/workflows", {}),
    ("GET", f"/locations/{LOCATION_ID}/campaigns", {}),
    # Tentativi di listare tutto
    ("GET", "/", {}),
    ("GET", f"/locations/{LOCATION_ID}/", {}),
    # V3 API
    ("GET", "/v3/automations/", {}),
    ("GET", "/v3/workflows/", {}),
    # GHL v2 standard
    ("GET", "/automations/", {}),
    ("GET", "/templates/email/", {"locationId": LOCATION_ID}),
]

print(f"[ghl-probe] Testing {len(endpoints)} endpoints")
print(f"[ghl-probe] API_KEY: {API_KEY[:10] if API_KEY else None}...")
print(f"[ghl-probe] LOCATION_ID: {LOCATION_ID}")
print()

results = []
for method, path, params in endpoints:
    result = probe_endpoint(method, path, params)
    results.append(result)
    status_str = f"✓ {result['status']}" if result["ok"] else f"✗ {result['status']}"
    print(f"{status_str:12} | {method:6} {path}")
    if result.get("response"):
        # Mostra chiavi principali della response
        keys = list(result["response"].keys())[:3]
        print(f"             | Response keys: {keys}")
    if result.get("error"):
        print(f"             | Error: {result['error'][:60]}")

print()
print("[ghl-probe] Summary:")
ok = [r for r in results if r["ok"]]
print(f"  Working endpoints: {len(ok)}")
for r in ok:
    print(f"    ✓ {r['method']} {r['path']}")
