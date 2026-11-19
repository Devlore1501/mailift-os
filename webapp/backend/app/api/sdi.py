"""Verifica formale e invio al SDI delle autofatture gia' create su FiC.

Stessa logica di tools/send_autofatture_sdi.py. L'invio e' IRREVERSIBILE (per
annullare un documento consegnato serve una nota di variazione), quindi:

  - l'invio richiede `confirm == "INVIA"` digitato dall'utente
  - prima di ogni invio si rifa' la verifica formale; chi non la supera non parte
  - i documenti gia' inviati vengono saltati
"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.models.schemas import (
    JobStartResponse,
    SdiDocument,
    SdiDocumentsResponse,
    SdiRequest,
    SdiSendRequest,
)
from app.services import workflow
from app.services.jobs import jobs

import send_autofatture_sdi as sdi_tool  # type: ignore  (tools/, via settings)

router = APIRouter(prefix="/api/sdi", tags=["sdi"])
logger = logging.getLogger("app.api.sdi")

CONFIRM_WORD = "INVIA"


def _to_payload(c, d: dict) -> SdiDocument:
    st = d.get("ei_status")
    return SdiDocument(
        id=d["id"],
        number=sdi_tool.doc_label(d),
        date=d.get("date") or "",
        supplier=(d.get("entity") or {}).get("name") or "",
        amount_gross=float(d.get("amount_gross") or 0),
        ei_status=st,
        rejection_reason=sdi_tool.rejection_reason(c, d["id"]) if st == "rejected" else None,
    )


def _docs_by_id(c, doc_ids: list[int]) -> list[dict]:
    wanted = set(doc_ids)
    docs = [d for d in c.list_self_supplier_invoices(fieldset="detailed") if d["id"] in wanted]
    missing = wanted - {d["id"] for d in docs}
    if missing:
        raise HTTPException(404, f"Documenti non trovati su FiC: {sorted(missing)}")
    return sorted(docs, key=lambda d: d["number"])


@router.get("/documents", response_model=SdiDocumentsResponse)
def documents(
    date: str | None = Query(None, description="Data documento YYYY-MM-DD (default: ultimo batch)"),
    ids: str | None = Query(None, description="Id FiC separati da virgola"),
) -> SdiDocumentsResponse:
    c = workflow.make_fic_client()
    docs = c.list_self_supplier_invoices(fieldset="detailed")
    if ids:
        wanted = {int(x) for x in ids.split(",") if x.strip().isdigit()}
        docs = [d for d in docs if d["id"] in wanted]
    else:
        date = date or max((d.get("date") or "" for d in docs), default="")
        docs = [d for d in docs if d.get("date") == date]
    docs.sort(key=lambda d: d["number"])
    return SdiDocumentsResponse(date=date or "", documents=[_to_payload(c, d) for d in docs])


def _run_verify(job_id: str, doc_ids: list[int]) -> None:
    try:
        c = workflow.make_fic_client()
        docs = _docs_by_id(c, doc_ids)
        items = []
        for i, d in enumerate(docs, 1):
            jobs.update(job_id, status="running", current=i, total=len(docs),
                        progress=int(i * 100 / len(docs)), step_name=f"Verifica {sdi_tool.doc_label(d)}")
            if d.get("ei_status") in sdi_tool.ALREADY_SENT:
                items.append({"id": d["id"], "number": sdi_tool.doc_label(d), "status": "already_sent",
                              "detail": d.get("ei_status")})
                continue
            ok, detail = sdi_tool.verify_doc(c, d)
            items.append({"id": d["id"], "number": sdi_tool.doc_label(d),
                          "status": "ok" if ok else "invalid", "detail": detail})
        jobs.update(job_id, status="done", progress=100, step_name="Completato", result={
            "items": items,
            "ok": sum(1 for x in items if x["status"] == "ok"),
            "invalid": sum(1 for x in items if x["status"] == "invalid"),
            "already_sent": sum(1 for x in items if x["status"] == "already_sent"),
        })
    except Exception as e:
        logger.exception("verifica SDI %s fallita", job_id)
        jobs.update(job_id, status="error", step_name="Errore", error=str(getattr(e, "detail", e)))


def _run_send(job_id: str, doc_ids: list[int]) -> None:
    try:
        c = workflow.make_fic_client()
        docs = _docs_by_id(c, doc_ids)
        items = []
        for i, d in enumerate(docs, 1):
            label = sdi_tool.doc_label(d)
            jobs.update(job_id, status="running", current=i, total=len(docs),
                        progress=int(i * 100 / len(docs)), step_name=f"Invio {label}")
            if d.get("ei_status") in sdi_tool.ALREADY_SENT:
                items.append({"id": d["id"], "number": label, "status": "already_sent",
                              "detail": d.get("ei_status")})
                continue
            ok, detail = sdi_tool.verify_doc(c, d)
            if not ok:
                items.append({"id": d["id"], "number": label, "status": "invalid", "detail": detail})
                continue
            ok, detail = sdi_tool.send_doc(c, d)
            logger.info("SDI invio %s (fic id %s): %s %s", label, d["id"], "ok" if ok else "ERRORE", detail)
            items.append({"id": d["id"], "number": label, "status": "sent" if ok else "error",
                          "detail": detail})
            time.sleep(1)
        jobs.update(job_id, status="done", progress=100, step_name="Completato", result={
            "items": items,
            "sent": sum(1 for x in items if x["status"] == "sent"),
            "errors": sum(1 for x in items if x["status"] in {"error", "invalid"}),
            "already_sent": sum(1 for x in items if x["status"] == "already_sent"),
        })
    except Exception as e:
        logger.exception("invio SDI %s fallito", job_id)
        jobs.update(job_id, status="error", step_name="Errore", error=str(getattr(e, "detail", e)))


@router.post("/verify", response_model=JobStartResponse)
def verify(req: SdiRequest, background: BackgroundTasks) -> JobStartResponse:
    if not req.doc_ids:
        raise HTTPException(400, "Nessun documento selezionato")
    job = jobs.create(kind="sdi_verify")
    background.add_task(_run_verify, job.id, req.doc_ids)
    return JobStartResponse(job_id=job.id)


@router.post("/send", response_model=JobStartResponse)
def send(req: SdiSendRequest, background: BackgroundTasks) -> JobStartResponse:
    if req.confirm.strip() != CONFIRM_WORD:
        raise HTTPException(400, f"Per inviare al SDI scrivi {CONFIRM_WORD}")
    if not req.doc_ids:
        raise HTTPException(400, "Nessun documento selezionato")
    job = jobs.create(kind="sdi_send")
    logger.warning("SDI: richiesto invio di %d documenti %s", len(req.doc_ids), req.doc_ids)
    background.add_task(_run_send, job.id, req.doc_ids)
    return JobStartResponse(job_id=job.id)
