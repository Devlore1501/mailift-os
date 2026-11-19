"""Archivio notturno: PDF di fatture e ricevute da Gmail a Google Drive.

Per ogni casella (personal, business):
  1. cerca le email recenti con allegato PDF;
  2. tiene solo quelle che sembrano fatture o ricevute (parole chiave);
  3. salva il PDF in Contabilita/AAAA/MM/Fornitore (anno e mese della mail);
  4. registra l'hash del file, cosi' lo stesso PDF non viene caricato due volte.

Gli estratti conto Revolut (casella business) vanno invece nella cartella del
commercialista come "Revolut AAAA-MM.pdf", con controllo del mese gia' presente.

Con dry_run=True non scrive nulla su Drive ne' nel registro: elenca solo cosa
farebbe.
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
import re
import threading
from datetime import datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db import SessionLocal, utcnow
from app.models.db_models import ArchivedFile, ArchiveRun, ProcessedMessage

log = logging.getLogger("app.archive")

TZ = ZoneInfo("Europe/Rome")
ACCOUNTS = ("personal", "business")
ROOT_FOLDER_NAME = "Contabilita"
DEFAULT_ACCOUNTANT_FOLDER = "1XeHd5VJyYq-3AiZZvcrpfZ6NTkKgoLv_"

DOC_KEYWORDS = (
    "fattura", "fatture", "invoice", "receipt", "ricevuta", "scontrino",
    "payment", "pagamento", "nota di credito", "credit note", "billing",
)
STATEMENT_KEYWORDS = ("statement", "estratto", "extrait", "kontoauszug")

_MONTHS = {
    "gen": 1, "jan": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "may": 5,
    "giu": 6, "jun": 6, "lug": 7, "jul": 7, "ago": 8, "aug": 8, "set": 9,
    "sep": 9, "ott": 10, "oct": 10, "nov": 11, "dic": 12, "dec": 12,
}
_run_lock = threading.Lock()


# ---------------------------------------------------------------- impostazioni

def drive_account() -> str:
    return os.getenv("ARCHIVE_DRIVE_ACCOUNT", "business")


def accountant_folder_id() -> str:
    return os.getenv("ARCHIVE_ACCOUNTANT_FOLDER_ID", DEFAULT_ACCOUNTANT_FOLDER)


def revolut_sender() -> str:
    """Parte del mittente che identifica Revolut. Da stringere al primo estratto reale."""
    return os.getenv("REVOLUT_SENDER_FILTER", "revolut").lower()


def default_dry_run() -> bool:
    return os.getenv("ARCHIVE_DRY_RUN", "true").lower() in {"1", "true", "yes"}


# --------------------------------------------------------------------- helpers

def sender_domain(from_header: str) -> str:
    m = re.search(r"@([A-Za-z0-9.-]+)", from_header or "")
    return m.group(1).lower() if m else ""


def supplier_name(from_header: str) -> str:
    """'billing@mail.openai.com' -> 'Openai'. Euristica sul dominio."""
    dom = sender_domain(from_header)
    if not dom:
        return "Sconosciuto"
    labels = dom.split(".")
    if len(labels) >= 3 and labels[-2] in {"co", "com", "org", "net"}:
        core = labels[-3]
    elif len(labels) >= 2:
        core = labels[-2]
    else:
        core = labels[0]
    return core.capitalize()


def safe_name(value: str) -> str:
    return re.sub(r'[\\/:*?"<>|\r\n]+', "_", value).strip() or "file"


def looks_like_document(meta: dict, filename: str) -> bool:
    hay = f"{meta.get('subject', '')} {filename} {meta.get('snippet', '')}".lower()
    return any(k in hay for k in DOC_KEYWORDS)


def is_revolut_statement(meta: dict, filename: str) -> bool:
    if revolut_sender() not in (meta.get("from") or "").lower():
        return False
    hay = f"{meta.get('subject', '')} {filename}".lower()
    return any(k in hay for k in STATEMENT_KEYWORDS)


def detect_statement_period(pdf: bytes, email_date: datetime) -> str:
    """Mese dell'estratto (AAAA-MM): dalla data finale scritta nel PDF, se leggibile.

    Se il testo non si legge, usa il mese precedente alla data dell'email
    (gli estratti mensili arrivano a inizio mese successivo).
    """
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(pdf)) as doc:
            text = " ".join((p.extract_text() or "") for p in doc.pages[:2])
        dates: list[tuple[int, int]] = []
        for d, mon, y in re.findall(r"\b(\d{1,2})\s+([A-Za-z]{3})[a-z]*\.?\s+(20\d{2})\b", text):
            if mon.lower() in _MONTHS:
                dates.append((int(y), _MONTHS[mon.lower()]))
        for d, mth, y in re.findall(r"\b(\d{1,2})[/.](\d{1,2})[/.](20\d{2})\b", text):
            if 1 <= int(mth) <= 12:
                dates.append((int(y), int(mth)))
        if dates:
            y, m = max(dates)
            return f"{y}-{m:02d}"
    except Exception as exc:  # PDF illeggibile: si usa il ripiego
        log.warning("periodo estratto non letto dal PDF: %s", exc)
    local = email_date.astimezone(TZ)
    first = local.replace(day=1) - timedelta(days=1)
    return f"{first.year}-{first.month:02d}"


# ------------------------------------------------------------------- esecuzione

def _new_stats() -> dict:
    return {"accounts": {}, "items": []}


def _acc_stats() -> dict:
    return {
        "messages": 0, "already_seen": 0, "no_pdf": 0, "not_invoice": 0,
        "uploaded": 0, "duplicates": 0, "revolut_uploaded": 0, "revolut_existing": 0,
        "errors": [],
    }


def run_archive(
    dry_run: bool | None = None,
    days: int = 2,
    trigger: str = "manual",
    gmail_factory: Callable | None = None,
    drive_factory: Callable | None = None,
) -> dict:
    """Esegue un giro completo. Un solo giro alla volta."""
    if dry_run is None:
        dry_run = default_dry_run()
    if not _run_lock.acquire(blocking=False):
        raise RuntimeError("Archivio gia' in esecuzione")
    try:
        return _run(dry_run, days, trigger, gmail_factory, drive_factory)
    finally:
        _run_lock.release()


def _run(dry_run, days, trigger, gmail_factory, drive_factory) -> dict:
    from app.services.drive import DriveStore
    from app.services.gmail_source import GmailSource

    gmail_factory = gmail_factory or GmailSource.for_account
    drive_factory = drive_factory or DriveStore.for_account

    with SessionLocal() as db:
        run = ArchiveRun(dry_run=dry_run, trigger=trigger, stats={})
        db.add(run)
        db.commit()
        run_id = run.id

    stats = _new_stats()
    drive = None
    error = None
    try:
        if not dry_run:
            drive = drive_factory(drive_account())
        for account in ACCOUNTS:
            acc = _acc_stats()
            stats["accounts"][account] = acc
            try:
                gmail = gmail_factory(account)
            except Exception as exc:
                acc["errors"].append(f"Gmail non disponibile: {exc}")
                continue
            try:
                _process_account(account, gmail, drive, dry_run, days, acc, stats["items"])
            except Exception as exc:
                log.exception("archivio %s fallito", account)
                acc["errors"].append(str(exc))
    except Exception as exc:
        log.exception("archivio fallito")
        error = str(exc)

    with SessionLocal() as db:
        run = db.get(ArchiveRun, run_id)
        run.finished_at = utcnow()
        run.stats = stats
        run.error = error
        db.commit()
    stats["run_id"] = run_id
    stats["dry_run"] = dry_run
    stats["error"] = error
    return stats


def _root_id(drive) -> str:
    fixed = os.getenv("ARCHIVE_ROOT_FOLDER_ID")
    return fixed or drive.ensure_folder(ROOT_FOLDER_NAME, "root")


def _process_account(account, gmail, drive, dry_run, days, acc, items) -> None:
    query = f"has:attachment filename:pdf newer_than:{max(1, days)}d -in:trash -in:spam"
    ids = gmail.search(query)
    acc["messages"] = len(ids)

    with SessionLocal() as db:
        seen = set(db.scalars(
            select(ProcessedMessage.message_id).where(ProcessedMessage.account == account)
        ))

    for msg_id in ids:
        if msg_id in seen:
            acc["already_seen"] += 1
            continue
        try:
            outcome = _process_message(account, gmail, drive, dry_run, msg_id, acc, items)
        except Exception as exc:
            log.exception("messaggio %s: errore", msg_id)
            acc["errors"].append(f"{msg_id}: {exc}")
            continue  # non lo segno come visto: riprova al prossimo giro
        if not dry_run:
            with SessionLocal() as db:
                db.add(ProcessedMessage(account=account, message_id=msg_id, outcome=outcome))
                db.commit()


def _process_message(account, gmail, drive, dry_run, msg_id, acc, items) -> str:
    meta = gmail.get(msg_id)
    if not meta["pdfs"]:
        acc["no_pdf"] += 1
        return "no_pdf"
    handled = False
    for att in meta["pdfs"]:
        fn = att["filename"]
        statement = account == "business" and is_revolut_statement(meta, fn)
        if not statement and not looks_like_document(meta, fn):
            acc["not_invoice"] += 1
            continue
        data = gmail.download(msg_id, att["attachment_id"])
        sha = hashlib.sha256(data).hexdigest()
        with SessionLocal() as db:
            existing = db.scalar(select(ArchivedFile).where(ArchivedFile.sha256 == sha))
        if existing:
            acc["duplicates"] += 1
            handled = True
            continue
        if statement:
            _save_revolut(account, drive, dry_run, meta, fn, data, sha, acc, items)
        else:
            _save_document(account, drive, dry_run, meta, fn, data, sha, acc, items)
        handled = True
    return "saved" if handled else "not_invoice"


def _save_document(account, drive, dry_run, meta, fn, data, sha, acc, items) -> None:
    when = meta["date"].astimezone(TZ)
    supplier = supplier_name(meta["from"])
    parts = [ROOT_FOLDER_NAME, f"{when.year}", f"{when.month:02d}", supplier]
    name = safe_name(f"{when:%Y-%m-%d} {fn}")
    item = {"kind": "document", "account": account, "path": "/".join(parts), "name": name,
            "from": meta["from"], "subject": meta["subject"]}
    if dry_run:
        items.append({**item, "action": "would_upload"})
        return
    folder = drive.ensure_path(parts[1:], _root_id(drive))
    file_id, url = drive.upload_pdf(name, data, folder)
    _register(sha, "document", f"{when.year}-{when.month:02d}", account, meta, fn, name, supplier, file_id, url)
    acc["uploaded"] += 1
    items.append({**item, "action": "uploaded", "url": url})


def _save_revolut(account, drive, dry_run, meta, fn, data, sha, acc, items) -> None:
    period = detect_statement_period(data, meta["date"])
    name = f"Revolut {period}.pdf"
    item = {"kind": "revolut", "account": account, "path": "cartella commercialista",
            "name": name, "from": meta["from"], "subject": meta["subject"]}
    with SessionLocal() as db:
        known = db.scalar(select(ArchivedFile).where(
            ArchivedFile.kind == "revolut", ArchivedFile.period == period))
    if known:
        acc["revolut_existing"] += 1
        items.append({**item, "action": "month_already_registered"})
        return
    if dry_run:
        items.append({**item, "action": "would_upload"})
        return
    folder = accountant_folder_id()
    if drive.find(name, folder):
        acc["revolut_existing"] += 1
        items.append({**item, "action": "month_already_in_drive"})
        _register(sha, "revolut", period, account, meta, fn, name, "Revolut", "", "")
        return
    file_id, url = drive.upload_pdf(name, data, folder)
    _register(sha, "revolut", period, account, meta, fn, name, "Revolut", file_id, url)
    acc["revolut_uploaded"] += 1
    items.append({**item, "action": "uploaded", "url": url})


def _register(sha, kind, period, account, meta, fn, name, supplier, file_id, url) -> None:
    with SessionLocal() as db:
        db.add(ArchivedFile(
            sha256=sha, kind=kind, period=period, account=account,
            gmail_message_id=meta["id"], original_filename=fn, drive_name=name,
            supplier=supplier, drive_file_id=file_id, drive_url=url,
        ))
        db.commit()
