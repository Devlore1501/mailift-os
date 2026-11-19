"""Google Drive: cartelle, ricerca per nome, upload di PDF.

Usa lo stesso file token degli account Gmail (lo scope drive e' in
tools/gmail_client.SCOPES). Un solo account ospita l'archivio, scelto con
ARCHIVE_DRIVE_ACCOUNT (default "business").
"""
from __future__ import annotations

import io
import logging

from app import settings  # noqa: F401  (inietta tools/ in sys.path)

log = logging.getLogger("app.drive")

FOLDER_MIME = "application/vnd.google-apps.folder"


def _q(value: str) -> str:
    """Escape per le stringhe nelle query Drive."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


class DriveStore:
    def __init__(self, service):
        self.svc = service
        self._cache: dict[tuple[str, str], str] = {}

    @classmethod
    def for_account(cls, account: str) -> "DriveStore":
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from gmail_client import SCOPES, token_path  # type: ignore

        tpath = token_path(account)
        if not tpath.exists():
            raise FileNotFoundError(f"Token mancante per '{account}': {tpath}")
        creds = Credentials.from_authorized_user_file(str(tpath), SCOPES)
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                tpath.write_text(creds.to_json())
            else:
                raise RuntimeError(f"Credenziali non valide per '{account}', rifai il login")
        if "https://www.googleapis.com/auth/drive" not in (creds.scopes or SCOPES):
            raise RuntimeError(f"Il token '{account}' non ha lo scope Drive: rifai il login")
        return cls(build("drive", "v3", credentials=creds, cache_discovery=False))

    def find(self, name: str, parent_id: str, folder: bool = False) -> str | None:
        q = f"name = '{_q(name)}' and '{parent_id}' in parents and trashed = false"
        if folder:
            q += f" and mimeType = '{FOLDER_MIME}'"
        resp = self.svc.files().list(
            q=q, fields="files(id, name)", pageSize=5,
            supportsAllDrives=True, includeItemsFromAllDrives=True,
        ).execute()
        files = resp.get("files", [])
        return files[0]["id"] if files else None

    def ensure_folder(self, name: str, parent_id: str) -> str:
        key = (parent_id, name)
        if key in self._cache:
            return self._cache[key]
        fid = self.find(name, parent_id, folder=True)
        if not fid:
            fid = self.svc.files().create(
                body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]},
                fields="id", supportsAllDrives=True,
            ).execute()["id"]
            log.info("cartella creata: %s", name)
        self._cache[key] = fid
        return fid

    def ensure_path(self, parts: list[str], root_id: str = "root") -> str:
        parent = root_id
        for part in parts:
            parent = self.ensure_folder(part, parent)
        return parent

    def upload_pdf(self, name: str, data: bytes, parent_id: str) -> tuple[str, str]:
        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(io.BytesIO(data), mimetype="application/pdf", resumable=False)
        meta = self.svc.files().create(
            body={"name": name, "parents": [parent_id]},
            media_body=media, fields="id, webViewLink", supportsAllDrives=True,
        ).execute()
        return meta["id"], meta.get("webViewLink", "")
