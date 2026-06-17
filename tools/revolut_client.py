"""
Client per Revolut Business API v1.

Scarica le transazioni di un mese e le salva come CSV compatibile con
parse_bank_statement.parse_tabular (colonne: date, description, amount, currency).

Configurazione richiesta nel .env:
    REVOLUT_API_KEY=<production token>     # Settings > APIs > Add access token

Docs: https://developer.revolut.com/docs/business/get-all-transactions
"""
from __future__ import annotations

import csv
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
if not ENV_PATH.exists():
    ENV_PATH = ROOT / ".env"

REVOLUT_API_BASE = "https://b2b.revolut.com/api/1.0"
MAX_COUNT = 1000

PRIVATE_KEY_PATH = Path.home() / ".secrets" / "mailift" / "revolut_private_key.pem"


def _load_credentials() -> tuple[str, str, str]:
    """Ritorna (client_id, access_token, refresh_token)."""
    load_dotenv(ENV_PATH)
    client_id = os.getenv("REVOLUT_CLIENT_ID", "").strip()
    access_token = os.getenv("REVOLUT_ACCESS_TOKEN", "").strip()
    refresh_token = os.getenv("REVOLUT_REFRESH_TOKEN", "").strip()
    if not client_id or not access_token:
        raise RuntimeError(
            "REVOLUT_CLIENT_ID o REVOLUT_ACCESS_TOKEN mancanti nel .env.\n"
            "Esegui prima: python tools/revolut_oauth_setup.py"
        )
    return client_id, access_token, refresh_token


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


def _refresh_token(client_id: str, refresh_token: str) -> str:
    """Rinnova l'access_token e aggiorna il .env. Ritorna il nuovo access_token."""
    from tools.revolut_oauth_setup import refresh_access_token
    private_key_pem = PRIVATE_KEY_PATH.read_bytes()
    tokens = refresh_access_token(client_id, refresh_token, private_key_pem)
    new_access = tokens.get("access_token", "")
    new_refresh = tokens.get("refresh_token", refresh_token)
    if not new_access:
        raise RuntimeError(f"Refresh fallito: {tokens}")
    _update_env({"REVOLUT_ACCESS_TOKEN": new_access, "REVOLUT_REFRESH_TOKEN": new_refresh})
    return new_access


def get_transactions(
    from_dt: datetime,
    to_dt: datetime,
    tx_type: str | None = None,
    state: str = "completed",
) -> list[dict[str, Any]]:
    """Scarica le transazioni da Revolut Business API.

    Returns:
        Lista di transazioni normalizzate pronte per parse_bank_statement:
        [{"date": "2026-05-01", "amount": -49.99, "currency": "EUR",
          "description": "Google Ireland Limited", "id": "..."}]
    """
    client_id, access_token, refresh_token = _load_credentials()

    params: dict[str, Any] = {
        "from": from_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "to": to_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "count": MAX_COUNT,
    }
    if tx_type:
        params["type"] = tx_type

    def _do_request(token: str):
        return requests.get(
            f"{REVOLUT_API_BASE}/transactions",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params=params,
            timeout=30,
        )

    resp = _do_request(access_token)
    if resp.status_code == 401 and refresh_token:
        # Token scaduto: rinnova e riprova una volta
        access_token = _refresh_token(client_id, refresh_token)
        resp = _do_request(access_token)
    if resp.status_code == 401:
        raise RuntimeError(
            "Revolut API: 401 Unauthorized. Riesegui: python tools/revolut_oauth_setup.py"
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"Revolut API: {resp.status_code} {resp.text}")

    raw_transactions: list[dict] = resp.json()

    normalized: list[dict[str, Any]] = []
    for tx in raw_transactions:
        # Filtra per stato
        if state and tx.get("state") != state:
            continue

        # Data: usa completed_at se disponibile, altrimenti created_at
        raw_date = tx.get("completed_at") or tx.get("created_at") or ""
        try:
            tx_date = datetime.fromisoformat(
                raw_date.replace("Z", "+00:00")
            ).date().isoformat()
        except (ValueError, AttributeError):
            continue

        amount = tx.get("amount")
        if amount is None:
            continue
        amount = float(amount)

        # Descrizione: preferisci merchant.name se card_payment, altrimenti description
        merchant = tx.get("merchant") or {}
        description = (
            merchant.get("name")
            or tx.get("description")
            or tx.get("counterparty", {}).get("name")
            or ""
        ).strip()
        # Aggiungi paese merchant se disponibile (aiuta il classificatore)
        merchant_country = merchant.get("country", "")
        if merchant_country:
            description = f"{description} [{merchant_country}]"

        normalized.append({
            "id": tx.get("id", ""),
            "date": tx_date,
            "amount": amount,
            "currency": (tx.get("currency") or "EUR").upper()[:3],
            "description": description,
            "type": tx.get("type", ""),
        })

    return normalized


def get_previous_month_range() -> tuple[datetime, datetime]:
    """Ritorna (from_dt, to_dt) per il mese precedente, 00:00-23:59:59 UTC."""
    today = date.today()
    # Primo giorno del mese corrente
    first_of_current = today.replace(day=1)
    # Ultimo giorno del mese precedente
    last_of_prev = first_of_current - __import__("datetime").timedelta(days=1)
    first_of_prev = last_of_prev.replace(day=1)

    from_dt = datetime(first_of_prev.year, first_of_prev.month, 1, 0, 0, 0, tzinfo=timezone.utc)
    to_dt = datetime(last_of_prev.year, last_of_prev.month, last_of_prev.day, 23, 59, 59, tzinfo=timezone.utc)
    return from_dt, to_dt


def save_to_csv(transactions: list[dict[str, Any]], path: Path) -> Path:
    """Salva le transazioni come CSV nel formato atteso da parse_bank_statement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date", "description", "amount", "currency"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(transactions)
    return path


def download_previous_month(inbox_dir: Path | None = None) -> tuple[Path, str]:
    """Entry point principale: scarica il mese scorso e salva il CSV in inbox/.

    Returns:
        (path_csv, month_label) — es. (Path("inbox/revolut_2026-05.csv"), "maggio 2026")
    """
    if inbox_dir is None:
        inbox_dir = ROOT / "inbox"

    from_dt, to_dt = get_previous_month_range()
    month_label = from_dt.strftime("%B %Y")  # es. "maggio 2026"
    filename = f"revolut_{from_dt.strftime('%Y-%m')}.csv"
    csv_path = inbox_dir / filename

    print(f"[revolut] Scaricando transazioni {from_dt.date()} → {to_dt.date()}...")
    txs = get_transactions(from_dt, to_dt)
    outflows = [t for t in txs if t["amount"] < 0]
    print(f"[revolut] {len(txs)} transazioni totali, {len(outflows)} in uscita.")

    save_to_csv(txs, csv_path)
    print(f"[revolut] Salvato: {csv_path}")
    return csv_path, month_label


if __name__ == "__main__":
    import sys

    try:
        path, label = download_previous_month()
        print(f"OK — {label} → {path}")
    except RuntimeError as e:
        print(f"ERRORE: {e}", file=sys.stderr)
        sys.exit(1)
