"""Suppliers endpoints: verify via email, rejects, invoices, overrides."""
from __future__ import annotations

import logging
import traceback

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger("app.api.suppliers")

from app.models.schemas import (
    JobStartResponse,
    SupplierOverrideCreate,
    SupplierOverridePayload,
    VerifyRejectItem,
    VerifyResultsResponse,
    VerifySupplierResult,
)
from app.services import overrides as overrides_svc
from app.services import suppliers as suppliers_svc
from app.services import workflow
from app.services.jobs import jobs

router = APIRouter(prefix="/api", tags=["suppliers"])


# ---------------------------------------------------------- verify job

def _run_verify_job(job_id: str, statement_id: str) -> None:
    logger.info("verify job %s starting (statement=%s)", job_id, statement_id)
    try:
        jobs.update(job_id, status="running", step_name="Avvio verifica fornitori", progress=2)

        def cb(current: int, total: int, name: str) -> None:
            progress = int(2 + (current - 1) * 96 / max(total, 1))
            jobs.update(
                job_id,
                step_name=f"[{current}/{total}] {name}",
                current=current,
                total=total,
                progress=progress,
            )

        results = suppliers_svc.run_verify_for_preview(statement_id, progress_cb=cb)
        jobs.update(
            job_id,
            status="done",
            progress=100,
            step_name="Completato",
            result={"results": results, "count": len(results)},
        )
        logger.info("verify job %s done (count=%d)", job_id, len(results))
    except Exception as e:
        tb = traceback.format_exc()
        logger.error("verify job %s failed: %s\n%s", job_id, e, tb)
        jobs.update(
            job_id,
            status="error",
            error=f"{type(e).__name__}: {e}\n{tb}",
            step_name="Errore",
        )


@router.post("/statements/{statement_id}/verify-suppliers", response_model=JobStartResponse)
def verify_suppliers(statement_id: str, background: BackgroundTasks) -> JobStartResponse:
    if not workflow.get_statement_path(statement_id):
        raise HTTPException(404, f"statement {statement_id} non trovato")
    job = jobs.create(kind="verify", statement_id=statement_id)
    jobs.update(job.id, step_name="In coda")
    background.add_task(_run_verify_job, job.id, statement_id)
    return JobStartResponse(job_id=job.id)


@router.get("/statements/{statement_id}/verify-suppliers/results", response_model=VerifyResultsResponse)
def verify_results(statement_id: str) -> VerifyResultsResponse:
    data = suppliers_svc.get_verify_results(statement_id)
    results = [VerifySupplierResult(**v) for v in data.values()]
    return VerifyResultsResponse(statement_id=statement_id, results=results)


# ------------------------------------------------------- quarantine PDFs

@router.get("/suppliers/verify-rejects", response_model=list[VerifyRejectItem])
def list_rejects() -> list[VerifyRejectItem]:
    return [VerifyRejectItem(**r) for r in suppliers_svc.list_rejects()]


@router.get("/suppliers/verify-rejects/{relpath:path}")
def get_reject(relpath: str):
    p = suppliers_svc.get_reject_path(relpath)
    if not p:
        raise HTTPException(404, "PDF non trovato")
    return FileResponse(str(p), media_type="application/pdf", filename=p.name)


# ---------------------------------------------------- downloaded invoices

@router.get("/suppliers/invoices/{supplier_key}")
def list_supplier_invoices(supplier_key: str) -> dict:
    files = suppliers_svc.list_invoices_for_supplier(supplier_key)
    return {"supplier_key": supplier_key, "files": files}


@router.get("/suppliers/invoices/{supplier_key}/{filename}")
def get_supplier_invoice(supplier_key: str, filename: str):
    p = suppliers_svc.get_invoice_path(supplier_key, filename)
    if not p:
        raise HTTPException(404, "PDF non trovato")
    return FileResponse(str(p), media_type="application/pdf", filename=p.name)


# --------------------------------------------------------------- overrides

@router.get("/suppliers/overrides", response_model=list[SupplierOverridePayload])
def overrides_list() -> list[SupplierOverridePayload]:
    return [SupplierOverridePayload(**o) for o in overrides_svc.list_all()]


@router.post("/suppliers/overrides", response_model=SupplierOverridePayload)
def overrides_upsert(payload: SupplierOverrideCreate) -> SupplierOverridePayload:
    try:
        saved = overrides_svc.upsert(payload.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))
    return SupplierOverridePayload(**saved)


@router.delete("/suppliers/overrides/{override_id}")
def overrides_delete(override_id: int) -> dict:
    ok = overrides_svc.delete(override_id)
    if not ok:
        raise HTTPException(404, "Override non trovato")
    return {"deleted": True}
