"""
OAuth2 setup per Google Calendar (una volta sola).

Usage:
    python tools/gcal_oauth_setup.py            # interattivo
    python tools/gcal_oauth_setup.py --force    # sovrascrivi token esistente

Cosa fa:
    1. Carica le credenziali OAuth Desktop da credentials_gmail.json
       (sì, le stesse che usi per Gmail — sono OAuth client generiche Google)
    2. Apre il browser per il flow OAuth con scope `calendar`
    3. Salva il token in tokens/gcal.json (o GCAL_TOKEN_FILE da .env)
    4. Test rapido: lista i calendari e stampa il primario

Prerequisito:
    - Aver gia' configurato Gmail (`tools/gmail_oauth_setup.py`) almeno una volta:
      le credenziali OAuth Desktop devono esistere a credentials_gmail.json
    - Sul progetto Google Cloud devi aver abilitato anche **Google Calendar API**
      (oltre a Gmail API). Se non l'hai fatto, vai su
      https://console.cloud.google.com → APIs & Services → Library →
      cerca "Google Calendar API" → Enable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT / "tools"))
from gcal_client import SCOPES, credentials_path, token_path  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="OAuth setup per Google Calendar")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Sovrascrivi token esistente senza chiedere",
    )
    args = ap.parse_args()

    creds_file = credentials_path()
    if not creds_file.exists():
        print(f"ERRORE: credenziali OAuth mancanti: {creds_file}")
        print("Devi prima configurare Gmail OAuth (le credenziali sono le stesse).")
        print("Vedi: tools/gmail_oauth_setup.py + .env.example per la guida")
        return 1

    tpath = token_path()
    tpath.parent.mkdir(parents=True, exist_ok=True)
    if tpath.exists() and not args.force:
        try:
            ans = input(
                f"Token gia' esistente ({tpath}). Sovrascrivere? [y/N]: "
            ).strip().lower()
        except EOFError:
            ans = "n"
        if ans != "y":
            print("Annullato.")
            return 0

    print("Avvio flow OAuth Google Calendar.")
    print("  Scope richiesti: calendar (read + write events)")
    print("  Si aprira' una finestra del browser. Accedi e autorizza.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    # Salva il token SUBITO, prima di testare. Cosi' se il test fallisce per
    # un motivo qualunque (API non abilitata, network, ecc.) il token resta
    # comunque sul disco e non serve rifare il consent del browser.
    tpath.write_text(creds.to_json())
    print(f"\n✅ Token salvato in {tpath}")

    # Test: verifica che la API sia abilitata e accessibile
    print("\nTest accesso Google Calendar API...")
    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        cal_list = service.calendarList().list().execute()
        primary = next(
            (c for c in cal_list.get("items", []) if c.get("primary")), None
        )
        print("✅ API accessibile")
        if primary:
            print(f"  Calendario primario: {primary.get('summary')} ({primary.get('id')})")
            print(f"  Timezone: {primary.get('timeZone')}")
        else:
            print(f"  Calendari trovati: {len(cal_list.get('items', []))}")
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  Test fallito ma il token e' salvato: {exc}")
        print(
            "   Probabilmente la Google Calendar API non e' ancora abilitata "
            "sul progetto. Vai su:"
        )
        print(
            "   https://console.developers.google.com/apis/api/"
            "calendar-json.googleapis.com/overview"
        )
        print("   → Enable, aspetta ~30s, poi riprova: python tools/gcal_client.py today")
        return 0
    print(
        "\nTesta con:\n"
        "  python tools/gcal_client.py today\n"
        "  python tools/gcal_client.py week\n"
        "  python tools/gcal_client.py free 09 19 60"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
