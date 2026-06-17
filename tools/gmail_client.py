"""
Wrapper minimale Gmail API per il workflow Daily Inbox Triage.

Funzioni esposte:
    list_recent(service, hours)        -> lista messaggi inbox ricevuti nelle ultime N ore
    get_message(service, msg_id)       -> dettaglio messaggio (headers, body, label, list-unsubscribe)
    archive_message(service, msg_id)   -> rimuove la label INBOX (sposta in "All Mail")
    send_email(service, to, subject, body_html)
                                       -> invia un'email dall'account autenticato

Token: ogni account ha il suo file JSON salvato da gmail_oauth_setup.py.
Le credenziali OAuth (Desktop type) sono in GMAIL_CREDENTIALS_FILE.

Scopes richiesti: gmail.modify (read + archive) + gmail.send.
"""
from __future__ import annotations

import base64
import os
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ROOT = Path(__file__).resolve().parent.parent

# gmail.modify copre read + archive (rimuovere label INBOX). gmail.send per inviare il report.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (ROOT / p)


def credentials_path() -> Path:
    env_path = os.environ.get("GMAIL_CREDENTIALS_FILE")
    if env_path:
        return _resolve(env_path)
    secrets_path = Path.home() / ".secrets" / "mailift" / "credentials_gmail.json"
    return secrets_path if secrets_path.exists() else _resolve("credentials_gmail.json")


def token_path(account: str) -> Path:
    """account = 'personal' | 'business'"""
    if account == "personal":
        return _resolve(os.environ.get("GMAIL_TOKEN_PERSONAL", "tokens/gmail_personal.json"))
    if account == "business":
        return _resolve(os.environ.get("GMAIL_TOKEN_BUSINESS", "tokens/gmail_business.json"))
    raise ValueError(f"account deve essere 'personal' o 'business', non '{account}'")


def load_service(account: str):
    """Carica le credenziali per l'account, fa refresh se serve, restituisce il client Gmail."""
    tpath = token_path(account)
    if not tpath.exists():
        raise FileNotFoundError(
            f"Token mancante per account '{account}': {tpath}. "
            f"Esegui prima: python tools/gmail_oauth_setup.py --account {account}"
        )
    creds = Credentials.from_authorized_user_file(str(tpath), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            tpath.write_text(creds.to_json())
        else:
            raise RuntimeError(
                f"Credenziali non valide per '{account}'. Riautentica con "
                f"python tools/gmail_oauth_setup.py --account {account}"
            )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def list_recent(service, hours: int = 24, max_results: int = 200) -> list[dict]:
    """Lista messaggi in inbox ricevuti nelle ultime `hours`. Ritorna lista di {id, threadId}."""
    # Gmail accetta solo newer_than:Nd / Nh / Nm. Per coprire frazioni convertiamo a stringa.
    if hours <= 24:
        q = f"in:inbox newer_than:{hours}h"
    else:
        days = max(1, hours // 24)
        q = f"in:inbox newer_than:{days}d"
    out: list[dict] = []
    page_token: str | None = None
    while True:
        kwargs: dict[str, Any] = {"userId": "me", "q": q, "maxResults": min(500, max_results - len(out))}
        if page_token:
            kwargs["pageToken"] = page_token
        resp = service.users().messages().list(**kwargs).execute()
        for m in resp.get("messages", []) or []:
            out.append({"id": m["id"], "threadId": m["threadId"]})
            if len(out) >= max_results:
                return out
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return out


def _decode_body(payload: dict) -> str:
    """Estrae il corpo (text/plain preferito, fallback text/html stripped)."""
    def walk(part: dict) -> tuple[str | None, str | None]:
        plain, html = None, None
        mime = part.get("mimeType", "")
        body = part.get("body", {}) or {}
        data = body.get("data")
        if data:
            try:
                decoded = base64.urlsafe_b64decode(data + "===").decode("utf-8", errors="replace")
            except Exception:
                decoded = ""
            if mime == "text/plain":
                plain = decoded
            elif mime == "text/html":
                html = decoded
        for sub in part.get("parts", []) or []:
            sp, sh = walk(sub)
            plain = plain or sp
            html = html or sh
        return plain, html

    plain, html = walk(payload)
    if plain:
        return plain.strip()
    if html:
        # Rimozione tag basilare; per il classificatore va benissimo
        import re
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    return ""


def get_message(service, msg_id: str, body_max_chars: int = 4000) -> dict:
    """Dettaglio messaggio: id, threadId, mittente, oggetto, data, labels, snippet, body, list_unsubscribe, has_attachments, permalink."""
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", []) or []}
    body = _decode_body(msg.get("payload", {}) or {})
    if len(body) > body_max_chars:
        body = body[:body_max_chars] + "\n…[truncated]"
    has_attach = False
    def _scan(part: dict):
        nonlocal has_attach
        if part.get("filename"):
            has_attach = True
        for sub in part.get("parts", []) or []:
            _scan(sub)
    _scan(msg.get("payload", {}) or {})
    return {
        "id": msg["id"],
        "threadId": msg["threadId"],
        "labelIds": msg.get("labelIds", []) or [],
        "snippet": msg.get("snippet", ""),
        "internalDate": msg.get("internalDate"),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "list_unsubscribe": headers.get("list-unsubscribe", ""),
        "has_attachments": has_attach,
        "body": body,
        "permalink": f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
    }


def search_messages(service, query: str, max_results: int = 20) -> list[dict]:
    """Ricerca libera con query Gmail (es. 'from:openai.com has:attachment filename:pdf').
    Ritorna lista di {id, threadId}."""
    out: list[dict] = []
    page_token: str | None = None
    while True:
        kwargs: dict[str, Any] = {"userId": "me", "q": query, "maxResults": min(500, max_results - len(out))}
        if page_token:
            kwargs["pageToken"] = page_token
        resp = service.users().messages().list(**kwargs).execute()
        for m in resp.get("messages", []) or []:
            out.append({"id": m["id"], "threadId": m["threadId"]})
            if len(out) >= max_results:
                return out
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return out


def download_attachments(service, msg_id: str, out_dir: Path, only_pdf: bool = True) -> list[Path]:
    """Scarica gli allegati del messaggio in out_dir. Ritorna lista di path salvati."""
    out_dir.mkdir(parents=True, exist_ok=True)
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    saved: list[Path] = []

    def walk(part: dict) -> None:
        filename = part.get("filename") or ""
        body = part.get("body", {}) or {}
        att_id = body.get("attachmentId")
        if filename and att_id:
            if only_pdf and not filename.lower().endswith(".pdf"):
                pass
            else:
                att = service.users().messages().attachments().get(
                    userId="me", messageId=msg_id, id=att_id
                ).execute()
                data = att.get("data", "")
                if data:
                    raw = base64.urlsafe_b64decode(data + "===")
                    # prefix with msg_id to avoid collisions
                    safe = filename.replace("/", "_").replace("\\", "_")
                    path = out_dir / f"{msg_id}_{safe}"
                    path.write_bytes(raw)
                    saved.append(path)
        for sub in part.get("parts", []) or []:
            walk(sub)

    walk(msg.get("payload", {}) or {})
    return saved


def archive_message(service, msg_id: str) -> None:
    """Rimuove la label INBOX (= archivia, conserva in All Mail)."""
    service.users().messages().modify(
        userId="me", id=msg_id, body={"removeLabelIds": ["INBOX"]}
    ).execute()


def send_email(service, to: str, subject: str, body: str, content_type: str = "text/plain") -> str:
    """Invia un'email dall'account autenticato. Ritorna il messageId."""
    msg = MIMEText(body, "plain" if content_type == "text/plain" else "html", "utf-8")
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return sent.get("id", "")
