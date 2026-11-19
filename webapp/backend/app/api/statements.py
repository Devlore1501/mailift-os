"""Endpoints per upload + parse + classify + preview di un estratto conto."""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.models.schemas import (
    JobStartResponse,
    ParseResponse,
    PreviewResponse,
    Transaction,
    UploadResponse,
)
from app.services import workflow
from app.services.jobs import jobs

router = APIRouter(prefix="/api/statements", tags=["statements"])
logger = logging.getLogger("app.api.statements")

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename:
        raise HTTPException(400, "filename mancante")
    suffix = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if suffix not in {"csv", "xls", "xlsx", "pdf"}:
        raise HTTPException(
            400,
            f"Formato non supportato: .{suffix}. Ammessi: csv, xls, xlsx, pdf"
        )
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(400, "File vuoto")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File oltre 20 MB")
    if suffix == "pdf" and not content.startswith(b"%PDF"):
        raise HTTPException(400, "Il file non e' un PDF valido")
    statement_id, path = workflow.save_uploaded_file(file.filename, content)
    return UploadResponse(
        statement_id=statement_id,
        filename=file.filename,
        size_bytes=len(content),
    )


@router.post("/{statement_id}/parse", response_model=ParseResponse)
def parse(statement_id: str) -> ParseResponse:
    if not workflow.get_statement_path(statement_id):
        raise HTTPException(404, f"statement {statement_id} non trovato")
    try:
        txs, balance_check = workflow.parse_statement_file(statement_id)
    except Exception as e:
        logger.exception("parse %s fallito", statement_id)
        raise HTTPException(500, f"Parse fallito: {e}")
    outflows = sum(1 for t in txs if t.get("amount", 0) < 0)
    return ParseResponse(
        statement_id=statement_id,
        transactions=[Transaction(**t) for t in txs],
        outflows_count=outflows,
        balance_check=balance_check,
    )


def _run_classify_job(job_id: str, statement_id: str) -> None:
    try:
        jobs.update(job_id, status="running", step_name="Classificazione AI in corso", progress=10)
        candidates, skipped = workflow.classify_statement(statement_id)
    except Exception as e:
        logger.exception("classify %s fallito", statement_id)
        jobs.update(job_id, status="error", step_name="Errore", error=f"Classificazione fallita: {e}")
        return

    try:
        jobs.update(job_id, progress=80, step_name="Aggregazione fornitori e controllo duplicati su FiC")
        preview = workflow.build_preview(statement_id)
        jobs.update(
            job_id,
            status="done",
            progress=100,
            step_name="Completato",
            result={
                "candidates_count": len(candidates),
                "autofatture_count": len(preview.get("autofatture", [])),
                "autofatture": preview.get("autofatture", []),
                "skipped_italian": preview.get("skipped_italian", []),
                "skipped_count": len(skipped),
                "excluded_count": len(preview.get("excluded", [])),
                "duplicate_count": sum(1 for a in preview.get("autofatture", []) if a.get("duplicate")),
            },
        )
    except Exception as e:
        jobs.update(job_id, status="error", error=str(e))


@router.post("/{statement_id}/classify", response_model=JobStartResponse)
def classify_endpoint(statement_id: str, background: BackgroundTasks) -> JobStartResponse:
    if not workflow.get_statement_path(statement_id):
        raise HTTPException(404, f"statement {statement_id} non trovato")
    job = jobs.create(kind="classify", statement_id=statement_id)
    jobs.update(job.id, step_name="In coda")
    background.add_task(_run_classify_job, job.id, statement_id)
    return JobStartResponse(job_id=job.id)


@router.post("/{statement_id}/preview", response_model=PreviewResponse)
def preview(statement_id: str) -> PreviewResponse:
    try:
        built = workflow.build_preview(statement_id)
    except Exception as e:
        raise HTTPException(500, f"Preview fallita: {e}")
    return PreviewResponse(statement_id=statement_id, **built)
