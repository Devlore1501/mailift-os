"""Endpoint per la creazione delle autofatture su Fatture in Cloud."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app import settings
from app.db import session_scope
from app.models.db_models import RunHistory
from app.models.schemas import CreateRequest, JobStartResponse
from app.services import workflow
from app.services.jobs import jobs

router = APIRouter(prefix="/api/autofatture", tags=["autofatture"])


def _write_run_history(
    statement_id: str | None,
    dry_run: bool,
    started_at: datetime,
    report: list[dict],
) -> None:
    try:
        with session_scope() as db:
            run = RunHistory(
                statement_id=statement_id,
                started_at=started_at,
                finished_at=datetime.utcnow(),
                dry_run=dry_run,
                total_count=len(report),
                created_count=sum(1 for r in report if r["status"] == "ok"),
                error_count=sum(1 for r in report if r["status"] == "error"),
                skipped_count=sum(1 for r in report if r["status"] == "skipped"),
                result_json=report,
            )
            db.add(run)
    except Exception as e:
        print(f"[autofatture] RunHistory write failed: {e}")


def _run_create_job(job_id: str, payload: dict) -> None:
    started_at = datetime.utcnow()
    statement_id = payload.get("statement_id")
    try:
        items = payload.get("autofatture") or []
        dry_run = bool(payload.get("dry_run") or settings.DRY_RUN_DEFAULT)
        active = [a for a in items if not a.get("excluded")]
        total = len(active)
        jobs.update(
            job_id,
            status="running",
            step_name="Inizializzazione FiC client" if not dry_run else "Dry-run: nessuna chiamata a FiC",
            progress=2,
            total=total,
            current=0,
        )

        client = None
        company_id = ""
        if not dry_run:
            client = workflow.make_fic_client()
            company_id = client.company_id

        report = []
        for i, p in enumerate(active, 1):
            af = workflow.payload_to_autofattura(p)
            jobs.update(
                job_id,
                step_name=f"[{i}/{total}] {af.supplier_name}",
                current=i,
                progress=int(2 + (i - 1) * 96 / max(total, 1)),
            )
            try:
                if dry_run:
                    report.append({
                        "status": "skipped",
                        "supplier": af.supplier_name,
                        "type_doc": af.type_doc,
                        "total_net": af.total_net,
                        "fic_id": None,
                        "fic_number": None,
                        "fic_numeration": None,
                        "fic_url": None,
                        "error": None,
                    })
                else:
                    created = client.create_self_supplier_invoice(af)  # type: ignore[union-attr]
                    report.append({
                        "status": "ok",
                        "supplier": af.supplier_name,
                        "type_doc": af.type_doc,
                        "total_net": af.total_net,
                        "fic_id": created.get("id"),
                        "fic_number": created.get("number"),
                        "fic_numeration": created.get("numeration"),
                        "fic_url": workflow.fic_invoice_url(company_id, created.get("id")),
                        "error": None,
                    })
            except Exception as e:
                report.append({
                    "status": "error",
                    "supplier": af.supplier_name,
                    "type_doc": af.type_doc,
                    "total_net": af.total_net,
                    "error": str(e),
                })

        jobs.update(
            job_id,
            status="done",
            progress=100,
            step_name="Completato",
            current=total,
            result={
                "dry_run": dry_run,
                "items": report,
                "ok": sum(1 for r in report if r["status"] == "ok"),
                "errors": sum(1 for r in report if r["status"] == "error"),
                "skipped": sum(1 for r in report if r["status"] == "skipped"),
            },
        )
        _write_run_history(statement_id, dry_run, started_at, report)
    except Exception as e:
        jobs.update(job_id, status="error", error=str(e))
        _write_run_history(statement_id, bool(payload.get("dry_run")), started_at, [])


@router.post("/create", response_model=JobStartResponse)
def create(req: CreateRequest, background: BackgroundTasks) -> JobStartResponse:
    if not req.autofatture:
        raise HTTPException(400, "Lista autofatture vuota")
    job = jobs.create(kind="create", statement_id=req.statement_id)
    payload = {
        "autofatture": [a.model_dump(mode="json") for a in req.autofatture],
        "dry_run": req.dry_run,
        "statement_id": req.statement_id,
    }
    jobs.update(job.id, step_name="In coda")
    background.add_task(_run_create_job, job.id, payload)
    return JobStartResponse(job_id=job.id)
