from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.db_models import Template
from ..models.schemas import CanvaSetIn, CanvaSetOut, TemplateOut
from ..services.canva_set import CanvaSetInvalid, apply_set, get_config
from ..services.notion_api import NotionAPIError, NotionNotConfigured, sync_templates

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[TemplateOut])
def list_templates(
    category: str | None = None, q: str | None = None, db: Session = Depends(get_db)
):
    query = db.query(Template)
    if category:
        query = query.filter(Template.category == category.lower())
    if q:
        query = query.filter(Template.name.ilike(f"%{q}%"))
    # id segue l'ordine di inserimento: per il set Canva è l'ordine numerico
    # dei template, per la sync Notion l'ordine del database.
    return query.order_by(Template.category, Template.id).all()


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    rows = (
        db.query(Template.category, func.count(Template.id))
        .group_by(Template.category)
        .order_by(func.count(Template.id).desc())
        .all()
    )
    return [{"category": cat or "senza categoria", "count": count} for cat, count in rows]


@router.post("/sync")
def sync(db: Session = Depends(get_db)):
    try:
        return sync_templates(db)
    except (NotionNotConfigured, NotionAPIError) as e:
        raise HTTPException(502, str(e))


@router.get("/set", response_model=CanvaSetOut)
def get_canva_set(db: Session = Depends(get_db)):
    return get_config(db)


@router.put("/set", response_model=CanvaSetOut)
def save_canva_set(payload: CanvaSetIn, db: Session = Depends(get_db)):
    try:
        return apply_set(
            db, payload.canva_file_url, [r.model_dump() for r in payload.ranges]
        )
    except CanvaSetInvalid as e:
        raise HTTPException(422, str(e))
