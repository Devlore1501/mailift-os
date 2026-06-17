"""
OAuth2 Device Code flow per Fatture in Cloud.

Alternativa ad Authorization Code se quest'ultimo è bloccato da una grant
"stuck" lato server. Non richiede client_secret né redirect_uri.

Usage:
    python tools/fic_device_setup.py

Cosa fa:
    1. Richiede un device_code via SDK ufficiale
    2. Stampa l'URL di verifica + user_code da inserire nel browser
    3. Polla fetch_token(device_code) finché l'utente non autorizza
    4. Salva access/refresh token e company_id in .env
"""
from __future__ import annotations

import os
import sys
import time
import webbrowser
from pathlib import Path

import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

import requests
from dotenv import load_dotenv
from fattureincloud_python_sdk.oauth2.oauth2 import (
    OAuth2DeviceCodeManager,
    OAuth2Error,
    Scope,
)

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
API_BASE = "https://api-v2.fattureincloud.it"


def update_env(updates: dict[str, str]) -> None:
    if not ENV_PATH.exists():
        ENV_PATH.write_text("")
    lines = ENV_PATH.read_text().splitlines()
    seen: set[str] = set()
    for i, line in enumerate(lines):
        if "=" not in line or line.strip().startswith("#"):
            continue
        key = line.split("=", 1)[0].strip()
        if key in updates:
            lines[i] = f"{key}={updates[key]}"
            seen.add(key)
    for k, v in updates.items():
        if k not in seen:
            lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(lines) + "\n")


def main() -> int:
    load_dotenv(ENV_PATH)
    client_id = os.getenv("FIC_CLIENT_ID")
    if not client_id:
        print("ERRORE: FIC_CLIENT_ID mancante in .env")
        return 1

    scope_names = (os.getenv("FIC_SCOPES") or "").split()
    scopes: list[Scope] = []
    for name in scope_names:
        try:
            scopes.append(Scope[name])
        except KeyError:
            print(f"  WARN: scope sconosciuto '{name}'")
    if not scopes:
        print("ERRORE: nessuno scope risolto da FIC_SCOPES")
        return 1

    manager = OAuth2DeviceCodeManager(client_id=client_id)

    print("Richiedo device code a Fatture in Cloud...")
    try:
        dc = manager.get_device_code(scopes)
    except OAuth2Error as e:
        print(f"ERRORE OAuth2 SDK: {e}")
        return 1
    except Exception as e:
        print(f"ERRORE imprevisto: {type(e).__name__}: {e}")
        return 1

    print()
    print("=" * 60)
    print(f"  Apri questo URL nel browser:  {dc.verification_uri}")
    print(f"  Inserisci questo codice:      {dc.user_code}")
    print(f"  Scade tra:                    {dc.expires_in}s")
    print("=" * 60)
    print()
    try:
        webbrowser.open(dc.verification_uri)
    except Exception:
        pass

    deadline = time.time() + dc.expires_in
    interval = max(dc.interval, 3)
    print(f"Polling ogni {interval}s in attesa dell'autorizzazione...")
    token = None
    while time.time() < deadline:
        time.sleep(interval)
        try:
            token = manager.fetch_token(dc.device_code)
            break
        except OAuth2Error as e:
            msg = str(e).lower()
            if "authorization_pending" in msg or "pending" in msg:
                print("  ...non ancora autorizzato, riprovo")
                continue
            if "slow_down" in msg:
                interval += 2
                continue
            print(f"ERRORE OAuth: {e}")
            return 1
        except Exception as e:
            print(f"ERRORE imprevisto in fetch_token: {type(e).__name__}: {e}")
            return 1

    if token is None:
        print("Tempo scaduto senza autorizzazione.")
        return 1

    print(f"\nToken ottenuto (expires_in={token.expires_in}s). Recupero le company...")
    me = requests.get(
        f"{API_BASE}/user/companies",
        headers={"Authorization": f"Bearer {token.access_token}"},
        timeout=30,
    )
    if me.status_code != 200:
        print(f"ERRORE GET /user/companies: {me.status_code} {me.text}")
        return 1
    companies = me.json().get("data", {}).get("companies", [])
    if not companies:
        print("Nessuna company trovata.")
        return 1
    print("\nCompany disponibili:")
    for i, c in enumerate(companies):
        print(f"  [{i}] id={c.get('id')}  name={c.get('name')}  type={c.get('type')}")
    if len(companies) == 1:
        company = companies[0]
        print(f"\nUna sola company, auto-selezionata: {company.get('name')}")
    else:
        try:
            choice = input("\nScegli l'indice della company: ").strip()
            company = companies[int(choice)]
        except (ValueError, IndexError, EOFError):
            print("Scelta non valida. Rilancia in un terminale.")
            return 1

    update_env({
        "FIC_ACCESS_TOKEN": token.access_token,
        "FIC_REFRESH_TOKEN": token.refresh_token or "",
        "FIC_COMPANY_ID": str(company["id"]),
    })
    print(f"\nOK. Company '{company.get('name')}' (id={company['id']}) salvata in .env")
    return 0


if __name__ == "__main__":
    sys.exit(main())
