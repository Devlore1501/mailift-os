"""Orchestrazione generazione piani: raccoglie il contesto brand, chiama Claude
in un thread di background e salva il risultato.
"""

from __future__ import annotations

import logging
import threading

from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models.db_models import Brand, Plan, PlanEmail, Template
from . import claude_ai

log = logging.getLogger("planner")


def build_context(db: Session, brand: Brand, month_start: str, num_emails: int, notes: str) -> dict:
    templates = [
        {
            "notion_page_id": t.notion_page_id,
            "name": t.name,
            "category": t.category,
            "tags": t.tags or [],
            "canva_url": t.canva_url,
        }
        for t in db.query(Template).all()
    ]
    return {
        "month_start": month_start,
        "country": brand.country or "IT",
        "num_emails": num_emails,
        "notes": notes,
        "brand": {
            "name": brand.name,
            "description": brand.description,
            "tone_of_voice": brand.tone_of_voice,
            "mission": brand.mission,
            "positioning": brand.positioning,
            "avatar": brand.avatar or {},
        },
        "products": [
            {
                "name": p.name,
                "category": p.category,
                "price": p.price,
                "seasonality": p.seasonality,
                "is_best_seller": p.is_best_seller,
                "notes": p.notes,
            }
            for p in brand.products
        ],
        "offers": [
            {
                "name": o.name,
                "code": o.code,
                "discount": o.discount,
                "valid_from": o.valid_from,
                "valid_to": o.valid_to,
                "active": o.active,
                "notes": o.notes,
            }
            for o in brand.offers
        ],
        "occasions": [
            {"name": oc.name, "date": oc.date, "notes": oc.notes} for oc in brand.occasions
        ],
        "launches": [
            {
                "name": l.name,
                "kind": l.kind,
                "start_date": l.start_date,
                "end_date": l.end_date,
                "subject": l.subject,
                "notes": l.notes,
            }
            for l in brand.launches
            if l.active
            and (
                # rilevante per il mese: senza date, o con inizio/fine nel mese
                not (l.start_date or l.end_date)
                or (l.start_date or l.end_date or "").startswith(month_start[:7])
                or (l.end_date or l.start_date or "").startswith(month_start[:7])
            )
        ],
        "klaviyo": brand.klaviyo_snapshot,
        "templates": templates,
    }


def _resolve_template(db: Session, notion_page_id: str | None) -> dict | None:
    if not notion_page_id:
        return None
    t = db.query(Template).filter(Template.notion_page_id == notion_page_id).first()
    if t is None:
        return None
    return {
        "template_id": t.id,
        "name": t.name,
        "category": t.category,
        "canva_url": t.canva_url,
        "preview_url": t.preview_url,
    }


def apply_email_payload(db: Session, email: PlanEmail, payload: dict) -> None:
    """Copia i campi generati da Claude su un PlanEmail."""
    email.send_date = payload.get("send_date", email.send_date)
    email.send_day = payload.get("send_day", email.send_day)
    email.send_time = payload.get("send_time", email.send_time)
    email.objective = payload.get("objective", email.objective)
    email.format = payload.get("format", email.format or "grafica")
    email.theme = payload.get("theme", email.theme)
    email.angle = payload.get("angle", email.angle)
    email.segment = payload.get("segment") or email.segment or {}
    email.subject_variants = payload.get("subject_variants") or email.subject_variants or []
    email.preview_text = payload.get("preview_text", email.preview_text)
    email.body = payload.get("body", email.body)
    email.blocks = payload.get("blocks") if payload.get("blocks") is not None else (email.blocks or [])
    email.campaign = payload.get("campaign") if "campaign" in payload else email.campaign
    email.products = payload.get("products") or []
    email.offer = payload.get("offer")
    email.canva_template = _resolve_template(db, payload.get("template_notion_page_id")) or (
        payload.get("canva_template") if isinstance(payload.get("canva_template"), dict) else None
    )


def _run_generation(plan_id: int) -> None:
    db = SessionLocal()
    try:
        plan = db.get(Plan, plan_id)
        if plan is None:
            return
        context = plan.context_snapshot or {}
        try:
            result = claude_ai.generate_plan(context)
        except Exception as e:  # errori API, JSON, rete
            log.exception("Generazione piano %s fallita", plan_id)
            plan.status = "error"
            plan.error = str(e)[:2000]
            db.commit()
            return

        for payload in result.get("emails", []):
            email = PlanEmail(plan_id=plan.id, position=payload.get("position", 1))
            db.add(email)
            apply_email_payload(db, email, payload)
        plan.campaigns = result.get("campaigns") or []
        plan.status = "draft"
        plan.error = None
        db.commit()
    finally:
        db.close()


def start_generation(plan_id: int) -> None:
    threading.Thread(target=_run_generation, args=(plan_id,), daemon=True).start()
