"""
Setup OAuth per Revolut Business API — metodo manuale (no server locale).

Esegui UNA VOLTA. Lo script:
    1. Stampa l'URL di autorizzazione
    2. Tu lo apri nel browser e clicchi "Abilita accesso" / "Conferma"
    3. Il browser prova a fare il redirect a localhost (andrà in errore di connessione —
       è normale). Copia l'URL COMPLETO dalla barra del browser e incollalo qui.
    4. Lo script estrae il codice, scambia per token e salva nel .env

Uso:
    python tools/revolut_oauth_setup.py
"""
from __future__ import annotations

import os
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
if not ENV_PATH.exists():
    ENV_PATH = ROOT / ".env"

PRIVATE_KEY_PATH = Path.home() / ".secrets" / "mailift" / "revolut_private_key.pem"
REDIRECT_URI = "https://httpbin.org/get"
REVOLUT_TOKEN_URL = "https://b2b.revolut.com/api/1.0/auth/token"

load_dotenv(ENV_PATH)


def _load_env(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise RuntimeError(f"{key} mancante nel .env")
    return val


def _update_env(updates: dict[str, str]) -> None:
    lines = ENV_PATH.read_text().splitlines()
    seen: set[str] = set()
    for i, line in enumerate(lines):
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            if k in updates:
                lines[i] = f"{k}={updates[k]}"
                seen.add(k)
    for k, v in updates.items():
        if k not in seen:
            lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(lines) + "\n")


def _make_jwt(client_id: str, private_key_pem: bytes) -> str:
    import base64, json as _json
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    key = load_pem_private_key(private_key_pem, password=None)
    now = int(datetime.now(timezone.utc).timestamp())

    header = {"alg": "RS256", "typ": "JWT"}
    issuer = urllib.parse.urlparse(REDIRECT_URI).hostname  # "httpbin.org"
    payload = {
        "iss": issuer,    # dominio del redirect_uri
        "sub": client_id, # client_id del certificato Revolut
        "aud": "https://revolut.com",
        "iat": now,
        "exp": now + 3600,
    }

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    h = b64url(_json.dumps(header, separators=(",", ":")).encode())
    p = b64url(_json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()
    sig = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{h}.{p}.{b64url(sig)}"


def _exchange_code(client_id: str, code: str, private_key_pem: bytes) -> dict:
    jwt = _make_jwt(client_id, private_key_pem)
    resp = requests.post(
        REVOLUT_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": jwt,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Token exchange fallito: {resp.status_code} {resp.text}")
    return resp.json()


def refresh_access_token(client_id: str, refresh_token: str, private_key_pem: bytes) -> dict:
    """Rinnova access_token. Chiamato da revolut_client.py."""
    jwt = _make_jwt(client_id, private_key_pem)
    resp = requests.post(
        REVOLUT_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": jwt,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Token refresh fallito: {resp.status_code} {resp.text}")
    return resp.json()


def main() -> None:
    client_id = _load_env("REVOLUT_CLIENT_ID")

    if not PRIVATE_KEY_PATH.exists():
        raise FileNotFoundError(f"Chiave privata non trovata: {PRIVATE_KEY_PATH}")
    private_key_pem = PRIVATE_KEY_PATH.read_bytes()

    # Costruisci URL di autorizzazione
    auth_url = (
        "https://business.revolut.com/app-confirm"
        f"?client_id={urllib.parse.quote(client_id)}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&response_type=code"
    )

    print("\n" + "="*60)
    print("STEP 1 — Apri questo URL nel browser:")
    print(f"\n  {auth_url}\n")
    print("="*60)
    print("\nSi aprirà una pagina Revolut. Clicca 'Conferma' / 'Abilita accesso'.")
    print("\nDopo la conferma, il browser apre httpbin.org e mostra un JSON.")
    print("Cerca il campo \"code\" nel JSON e incolla il suo valore qui sotto.\n")

    callback_url = input("STEP 2 — Incolla il valore del campo \"code\" dal JSON (o l'URL completo): ").strip()

    # Estrai il code dall'URL
    parsed = urllib.parse.urlparse(callback_url)
    params = dict(urllib.parse.parse_qsl(parsed.query))

    if "error" in params:
        raise RuntimeError(f"Revolut ha restituito un errore: {params}")

    code = params.get("code", "")
    if not code:
        # Forse l'utente ha incollato solo il code, non l'URL completo
        code = callback_url.strip()
        if not code:
            raise RuntimeError("Nessun codice trovato. Riprova.")

    print(f"\nCodice ricevuto: {code[:20]}... — scambio per token...")

    tokens = _exchange_code(client_id, code, private_key_pem)
    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")

    if not access_token:
        raise RuntimeError(f"Nessun access_token nella risposta: {tokens}")

    _update_env({
        "REVOLUT_ACCESS_TOKEN": access_token,
        "REVOLUT_REFRESH_TOKEN": refresh_token,
    })

    print("\n✅ Autenticazione completata! Token salvati nel .env.")
    print("\nOra puoi testare:")
    print("  python tools/monthly_autofatture.py --dry-run")


if __name__ == "__main__":
    main()
