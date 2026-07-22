"""Endpoints per upload + parse + classify + preview di un estratto conto."""
from __future__ import annotations

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
    content = await file.read()
    if not content:
        raise HTTPException(400, "File vuoto")
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
        txs = workflow.parse_statement_file(statement_id)
    except Exception as e:
        raise HTTPException(500, f"Parse fallito: {e}")
    outflows = sum(1 for t in txs if t.get("amount", 0) < 0)
    return ParseResponse(
        statement_id=statement_id,
        transactions=[Transaction(**t) for t in txs],
        outflows_count=outflows,
    )


def _run_classify_job(job_id: str, statement_id: str) -> None:
    try:
        jobs.update(job_id, status="running", step_name="Classificazione AI in corso", progress=10)
        candidates, skipped = workflow.classify_statement(statement_id)
    except Exception as e:
        # Fallback: se Anthropic fallisce (credit insufficienti, errore API, ecc), usiamo seed deterministici
        jobs.update(job_id, step_name="Fallback a candidati predefiniti", progress=30)
        import logging
        logging.getLogger(__name__).warning(f"classify_statement fallito, usando fallback: {e}")
        candidates, skipped = workflow.classify_statement_with_fallback(statement_id)

    try:
        jobs.update(job_id, progress=80, step_name="Aggregazione fornitori")
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
    return PreviewResponse(
        statement_id=statement_id,
        autofatture=built.get("autofatture", []),
        skipped_italian=built.get("skipped_italian", []),
    )
