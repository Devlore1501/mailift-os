"""Lettura Gmail per l'archivio: ricerca, intestazioni, allegati PDF in memoria."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from app import settings  # noqa: F401


class GmailSource:
    def __init__(self, service):
        self.svc = service

    @classmethod
    def for_account(cls, account: str) -> "GmailSource":
        from gmail_client import load_service  # type: ignore

        return cls(load_service(account))

    def search(self, query: str, max_results: int = 300) -> list[str]:
        ids: list[str] = []
        token = None
        while len(ids) < max_results:
            kw = {"userId": "me", "q": query, "maxResults": min(100, max_results - len(ids))}
            if token:
                kw["pageToken"] = token
            resp = self.svc.users().messages().list(**kw).execute()
            ids += [m["id"] for m in resp.get("messages", []) or []]
            token = resp.get("nextPageToken")
            if not token:
                break
        return ids

    def get(self, msg_id: str) -> dict:
        """Intestazioni + elenco allegati PDF (senza scaricarli)."""
        msg = self.svc.users().messages().get(userId="me", id=msg_id, format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", []) or []}
        pdfs: list[dict] = []

        def walk(part: dict) -> None:
            fn = part.get("filename") or ""
            body = part.get("body", {}) or {}
            if fn and body.get("attachmentId") and (
                fn.lower().endswith(".pdf") or part.get("mimeType") == "application/pdf"
            ):
                pdfs.append({"filename": fn, "attachment_id": body["attachmentId"]})
            for sub in part.get("parts", []) or []:
                walk(sub)

        walk(msg.get("payload", {}) or {})
        try:
            when = parsedate_to_datetime(headers.get("date", ""))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
        except Exception:
            when = datetime.fromtimestamp(int(msg.get("internalDate", 0)) / 1000, tz=timezone.utc)
        return {
            "id": msg["id"],
            "from": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "date": when,
            "snippet": msg.get("snippet", ""),
            "pdfs": pdfs,
        }

    def download(self, msg_id: str, attachment_id: str) -> bytes:
        att = self.svc.users().messages().attachments().get(
            userId="me", messageId=msg_id, id=attachment_id
        ).execute()
        return base64.urlsafe_b64decode(att.get("data", "") + "===")
