"""Run history endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import desc, select

from app.db import session_scope
from app.models.db_models import RunHistory
from app.models.schemas import RunHistoryDetail, RunHistoryItem

router = APIRouter(prefix="/api/history", tags=["history"])


def _row_to_item(r: RunHistory) -> dict:
    return {
        "id": r.id,
        "statement_id": r.statement_id,
        "started_at": r.started_at,
        "finished_at": r.finished_at,
        "dry_run": r.dry_run,
        "total_count": r.total_count,
        "created_count": r.created_count,
        "error_count": r.error_count,
        "skipped_count": r.skipped_count,
    }


@router.get("", response_model=list[RunHistoryItem])
def list_history() -> list[RunHistoryItem]:
    with session_scope() as db:
        rows = db.execute(select(RunHistory).order_by(desc(RunHistory.started_at)).limit(50)).scalars().all()
        return [RunHistoryItem(**_row_to_item(r)) for r in rows]


@router.get("/{run_id}", response_model=RunHistoryDetail)
def get_run(run_id: int) -> RunHistoryDetail:
    with session_scope() as db:
        r = db.get(RunHistory, run_id)
        if not r:
            raise HTTPException(404, "run non trovato")
        item = _row_to_item(r)
        item["result_json"] = r.result_json
        return RunHistoryDetail(**item)
