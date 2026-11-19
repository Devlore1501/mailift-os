"""Archivio PDF Gmail -> Drive: stato e avvio manuale."""
from __future__ import annotations

import threading

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models.db_models import ArchivedFile, ArchiveRun
from app.services import archive as svc

router = APIRouter(prefix="/api/archive", tags=["archive"])


class RunRequest(BaseModel):
    dry_run: bool | None = Field(default=None, description="Se omesso vale ARCHIVE_DRY_RUN (default true)")
    days: int = Field(default=2, ge=1, le=365)


@router.get("/status")
def status() -> dict:
    with SessionLocal() as db:
        runs = db.scalars(select(ArchiveRun).order_by(ArchiveRun.id.desc()).limit(10)).all()
        total = db.scalar(select(func.count(ArchivedFile.id))) or 0
        revolut = db.scalars(
            select(ArchivedFile).where(ArchivedFile.kind == "revolut").order_by(ArchivedFile.period)
        ).all()
        return {
            "default_dry_run": svc.default_dry_run(),
            "drive_account": svc.drive_account(),
            "revolut_sender_filter": svc.revolut_sender(),
            "archived_files": total,
            "revolut_periods": [r.period for r in revolut],
            "runs": [
                {"id": r.id, "started_at": r.started_at, "finished_at": r.finished_at,
                 "dry_run": r.dry_run, "trigger": r.trigger, "error": r.error,
                 "accounts": {a: {k: v for k, v in s.items() if k != "errors"} | {"errors": len(s["errors"])}
                              for a, s in (r.stats or {}).get("accounts", {}).items()}}
                for r in runs
            ],
        }


@router.post("/run")
def run(req: RunRequest) -> dict:
    """Esegue subito un giro (sincrono: con days piccoli ci mette pochi secondi)."""
    try:
        return svc.run_archive(dry_run=req.dry_run, days=req.days, trigger="manual")
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
