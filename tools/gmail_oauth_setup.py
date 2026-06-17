"""
OAuth2 setup per un account Gmail (un account alla volta).

Usage:
    python tools/gmail_oauth_setup.py --account personal
    python tools/gmail_oauth_setup.py --account business

Cosa fa:
    1. Carica le credenziali OAuth Desktop da credentials_gmail.json
    2. Apre il browser per il flow OAuth Google
    3. Verifica che l'email autenticata corrisponda all'address attesa
       (GMAIL_PERSONAL_ADDRESS / GMAIL_BUSINESS_ADDRESS)
    4. Salva il token nel path GMAIL_TOKEN_<account>.json

Ripetibile: se il token esiste gia', ti chiede se sovrascrivere.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# importa SCOPES e helper dallo stesso modulo client per garantire coerenza
sys.path.insert(0, str(ROOT / "tools"))
from gmail_client import SCOPES, credentials_path, token_path  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="OAuth setup per un account Gmail")
    ap.add_argument("--account", required=True, choices=["personal", "business"])
    ap.add_argument("--force", action="store_true", help="Sovrascrivi token esistente senza chiedere")
    args = ap.parse_args()

    creds_file = credentials_path()
    if not creds_file.exists():
        print(f"ERRORE: credenziali OAuth mancanti: {creds_file}")
        print("Crea un OAuth client di tipo 'Desktop' su https://console.cloud.google.com/")
        print("e scarica il JSON in quel path. Vedi .env.example per la guida.")
        return 1

    tpath = token_path(args.account)
    tpath.parent.mkdir(parents=True, exist_ok=True)
    if tpath.exists() and not args.force:
        try:
            ans = input(f"Token gia' esistente per '{args.account}' ({tpath}). Sovrascrivere? [y/N]: ").strip().lower()
        except EOFError:
            ans = "n"
        if ans != "y":
            print("Annullato.")
            return 0

    expected_address = os.environ.get(
        "GMAIL_PERSONAL_ADDRESS" if args.account == "personal" else "GMAIL_BUSINESS_ADDRESS",
        "",
    )

    print(f"Avvio flow OAuth per account '{args.account}'.")
    if expected_address:
        print(f"  Atteso: {expected_address}")
    print("  Si aprira' una finestra del browser. Accedi e autorizza.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    # Verifica che l'email autenticata sia quella attesa
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    profile = service.users().getProfile(userId="me").execute()
    actual = profile.get("emailAddress", "")
    print(f"\nEmail autenticata: {actual}")

    if expected_address and actual.lower() != expected_address.lower():
        print(f"ATTENZIONE: ti aspettavi {expected_address} ma hai autenticato {actual}.")
        try:
            ans = input("Salvo lo stesso? [y/N]: ").strip().lower()
        except EOFError:
            ans = "n"
        if ans != "y":
            print("Annullato. Riprova selezionando l'account giusto nel browser.")
            return 1

    tpath.write_text(creds.to_json())
    print(f"OK. Token salvato in {tpath}")
    print(f"Messaggi totali: {profile.get('messagesTotal')}, threads: {profile.get('threadsTotal')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
