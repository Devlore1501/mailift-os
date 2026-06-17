"""GET /api/jobs/{job_id}."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import JobInfo
from app.services.jobs import jobs

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobInfo)
def get_job(job_id: str) -> JobInfo:
    j = jobs.get(job_id)
    if not j:
        raise HTTPException(404, f"job {job_id} non trovato")
    return JobInfo(
        id=j.id,
        kind=j.kind,
        status=j.status,  # type: ignore[arg-type]
        progress=j.progress,
        step_name=j.step_name,
        total=j.total,
        current=j.current,
        result=j.result,
        error=j.error,
        created_at=j.created_at,
        statement_id=j.statement_id,
    )
