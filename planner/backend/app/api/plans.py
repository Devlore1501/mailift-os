from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.db_models import Plan, PlanEmail
from ..models.schemas import (
    PlanDetail,
    PlanEmailOut,
    PlanEmailPatch,
    PlanGenerateIn,
    PlanPatch,
    PlanSummary,
    PublishResult,
    RegenerateIn,
)
from ..services import claude_ai
from ..services.notion_api import NotionAPIError, NotionNotConfigured, publish_plan
from ..services.planner import apply_email_payload, build_context, start_generation
from .brands import get_brand_or_404

router = APIRouter(prefix="/api", tags=["plans"])


def _summary(plan: Plan) -> PlanSummary:
    out = PlanSummary.model_validate(plan)
    out.num_emails = len(plan.emails)
    return out


def _get_plan(db: Session, plan_id: int) -> Plan:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(404, "Piano non trovato")
    return plan


def _get_email(db: Session, plan_id: int, email_id: int) -> PlanEmail:
    email = db.get(PlanEmail, email_id)
    if email is None or email.plan_id != plan_id:
        raise HTTPException(404, "Email non trovata in questo piano")
    return email


@router.get("/brands/{brand_id}/plans", response_model=list[PlanSummary])
def list_plans(brand_id: int, db: Session = Depends(get_db)):
    get_brand_or_404(db, brand_id)
    plans = (
        db.query(Plan)
        .filter(Plan.brand_id == brand_id)
        .order_by(Plan.month_start.desc())
        .all()
    )
    return [_summary(p) for p in plans]


@router.post("/brands/{brand_id}/plans/generate", response_model=PlanSummary, status_code=202)
def generate_plan(brand_id: int, payload: PlanGenerateIn, db: Session = Depends(get_db)):
    brand = get_brand_or_404(db, brand_id)
    # normalizza al primo giorno del mese
    month_start = payload.month_start[:7] + "-01"
    existing = (
        db.query(Plan)
        .filter(Plan.brand_id == brand_id, Plan.month_start == month_start)
        .first()
    )
    if existing is not None:
        raise HTTPException(409, f"Esiste già un piano per il mese {month_start[:7]}")

    num_emails = payload.num_emails or (brand.emails_per_week or 3) * 4
    num_emails = max(2, min(num_emails, 31))
    context = build_context(db, brand, month_start, num_emails, payload.notes)

    plan = Plan(
        brand_id=brand_id,
        month_start=month_start,
        status="generating",
        notes=payload.notes,
        context_snapshot=context,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    start_generation(plan.id)
    return _summary(plan)


@router.get("/plans/{plan_id}", response_model=PlanDetail)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = _get_plan(db, plan_id)
    out = PlanDetail.model_validate(plan)
    out.num_emails = len(plan.emails)
    out.emails = [PlanEmailOut.model_validate(e) for e in plan.emails]
    out.context_snapshot = plan.context_snapshot
    return out


@router.patch("/plans/{plan_id}", response_model=PlanSummary)
def patch_plan(plan_id: int, payload: PlanPatch, db: Session = Depends(get_db)):
    plan = _get_plan(db, plan_id)
    if payload.status is not None:
        allowed = {("draft", "approved"), ("approved", "draft")}
        if (plan.status, payload.status) not in allowed:
            raise HTTPException(
                409, f"Transizione di stato non valida: {plan.status} → {payload.status}"
            )
        plan.status = payload.status
    if payload.notes is not None:
        plan.notes = payload.notes
    db.commit()
    db.refresh(plan)
    return _summary(plan)


@router.delete("/plans/{plan_id}", status_code=204)
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = _get_plan(db, plan_id)
    db.delete(plan)
    db.commit()


@router.patch("/plans/{plan_id}/emails/{email_id}", response_model=PlanEmailOut)
def patch_email(
    plan_id: int, email_id: int, payload: PlanEmailPatch, db: Session = Depends(get_db)
):
    email = _get_email(db, plan_id, email_id)
    data = payload.model_dump(exclude_unset=True)
    explicit_status = data.pop("status", None)
    for key, value in data.items():
        setattr(email, key, value)
    if explicit_status is not None:
        email.status = explicit_status
    elif data:
        email.status = "edited"
    db.commit()
    db.refresh(email)
    return email


@router.post("/plans/{plan_id}/emails/{email_id}/regenerate", response_model=PlanEmailOut)
def regenerate_email(
    plan_id: int, email_id: int, payload: RegenerateIn, db: Session = Depends(get_db)
):
    plan = _get_plan(db, plan_id)
    email = _get_email(db, plan_id, email_id)
    if plan.status == "generating":
        raise HTTPException(409, "Il piano è ancora in generazione")

    context = dict(plan.context_snapshot or {})
    context["other_emails"] = [
        {
            "position": e.position,
            "send_date": e.send_date,
            "objective": e.objective,
            "theme": e.theme,
            "subject": (e.subject_variants or [""])[0],
        }
        for e in plan.emails
        if e.id != email.id
    ]
    current = {
        "position": email.position,
        "send_date": email.send_date,
        "send_day": email.send_day,
        "send_time": email.send_time,
        "objective": email.objective,
        "format": email.format,
        "theme": email.theme,
        "angle": email.angle,
        "segment": email.segment,
        "subject_variants": email.subject_variants,
        "preview_text": email.preview_text,
        "body": email.body,
        "blocks": email.blocks,
        "campaign": email.campaign,
        "products": email.products,
        "offer": email.offer,
    }
    try:
        result = claude_ai.regenerate_email(context, current, payload.instructions)
    except Exception as e:
        raise HTTPException(502, f"Rigenerazione fallita: {e}")

    apply_email_payload(db, email, result)
    email.status = "draft"
    db.commit()
    db.refresh(email)
    return email


@router.post("/plans/{plan_id}/publish", response_model=PublishResult)
def publish(plan_id: int, db: Session = Depends(get_db)):
    plan = _get_plan(db, plan_id)
    if plan.status not in ("approved", "published"):
        raise HTTPException(409, "Il piano deve essere approvato prima della pubblicazione")

    emails = [
        {
            "id": e.id,
            "position": e.position,
            "send_date": e.send_date,
            "send_day": e.send_day,
            "send_time": e.send_time,
            "objective": e.objective,
            "format": e.format,
            "theme": e.theme,
            "angle": e.angle,
            "segment": e.segment,
            "subject_variants": e.subject_variants,
            "preview_text": e.preview_text,
            "body": e.body,
            "blocks": e.blocks,
            "campaign": e.campaign,
            "products": e.products,
            "offer": e.offer,
            "canva_template": e.canva_template,
            "status": e.status,
        }
        for e in plan.emails
    ]
    try:
        result = publish_plan(db, plan.brand.name, plan.month_start, emails)
    except (NotionNotConfigured, NotionAPIError) as e:
        raise HTTPException(502, str(e))

    plan.status = "published"
    plan.notion_database_id = result.get("notion_database_id") or ""
    plan.notion_url = result.get("notion_url") or ""
    url_by_email = {p["email_id"]: p.get("notion_url", "") for p in result.get("pages", [])}
    for e in plan.emails:
        if e.id in url_by_email:
            e.notion_page_url = url_by_email[e.id]
    db.commit()
    return PublishResult(
        status="published",
        notion_database_id=plan.notion_database_id,
        notion_url=plan.notion_url,
        pages=result.get("pages", []),
    )
