"""
One-shot: cancella i fornitori duplicati creati nei retry della sessione precedente.

Sicurezza:
- Cancella SOLO gli id elencati in DUPLICATE_IDS sotto.
- Stampa l'elenco e chiede conferma (default: y) prima di procedere.
- Esegue DELETE /c/{cid}/entities/suppliers/{id} con il token in .env.

Uso:
    python tools/cleanup_suppliers.py [--yes]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
if not ENV_PATH.exists():
    ENV_PATH = ROOT / ".env"  # Fallback per compatibilità
API_BASE = "https://api-v2.fattureincloud.it"

# Id verificati con GET /entities/suppliers durante la sessione 2026-04-08
DUPLICATE_IDS: list[tuple[int, str]] = [
    (51675578, "Mailsupply (Josh Von Mailsupply)"),
    (51675570, "Mailsupply (Josh Von)"),
    (51675573, "Dropbox Ireland Unlimited Company"),  # duplicato di 51675558
    (51675571, "Waalaxy (Prospectin SAS)"),  # duplicato di 51675557
    (51675556, "Lovable AB"),  # duplicato di 50070423 (Lovable Labs Incorporated)
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="Salta la conferma")
    args = ap.parse_args()

    load_dotenv(ENV_PATH)
    tok = os.environ["FIC_ACCESS_TOKEN"]
    cid = os.environ["FIC_COMPANY_ID"]

    print("Sto per cancellare i seguenti fornitori duplicati da Fatture in Cloud:")
    for did, name in DUPLICATE_IDS:
        print(f"  - id={did}  {name}")

    if not args.yes:
        ans = input("\nProcedere con la cancellazione? [Y/n] ").strip().lower()
        if ans not in {"", "y", "yes", "s", "si"}:
            print("Annullato.")
            return 0

    failures = 0
    for did, name in DUPLICATE_IDS:
        r = requests.delete(
            f"{API_BASE}/c/{cid}/entities/suppliers/{did}",
            headers={"Authorization": f"Bearer {tok}"},
            timeout=30,
        )
        if r.status_code in {200, 204}:
            print(f"  OK   delete {did} ({name})")
        else:
            failures += 1
            print(f"  FAIL delete {did} ({name}): {r.status_code} {r.text[:200]}")
    print()
    print(f"Fatto. Cancellazioni riuscite: {len(DUPLICATE_IDS) - failures}/{len(DUPLICATE_IDS)}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
