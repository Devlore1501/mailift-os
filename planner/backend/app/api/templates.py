from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.db_models import Template
from ..models.schemas import CanvaSetIn, CanvaSetOut, TemplateOut
from ..services.canva_set import (
    CanvaSetInvalid,
    apply_set,
    find_preview_file,
    get_config,
    parse_entries_text,
    save_previews,
)
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
    entries = [e.model_dump() for e in payload.entries]
    if not entries and payload.entries_text.strip():
        entries = parse_entries_text(payload.entries_text)
    try:
        return apply_set(db, payload.canva_file_url, entries)
    except CanvaSetInvalid as e:
        raise HTTPException(422, str(e))


@router.post("/previews")
async def upload_previews(
    files: list[UploadFile] = File(...), db: Session = Depends(get_db)
):
    """Carica le anteprime dei template: export PNG/JPG del file Canva
    (immagini singole numerate o uno zip). L'abbinamento è per numero di
    pagina ricavato dal nome del file."""
    if not files:
        raise HTTPException(400, "Nessun file caricato")
    payload: list[tuple[str, bytes]] = []
    total = 0
    for f in files:
        data = await f.read()
        total += len(data)
        if total > 300 * 1024 * 1024:
            raise HTTPException(413, "Upload troppo grande (max 300 MB)")
        payload.append((f.filename or "", data))
    result = save_previews(db, payload)
    if result["saved"] == 0:
        raise HTTPException(
            422,
            "Nessuna immagine valida trovata: servono PNG/JPG numerati "
            "(es. 'Design - 12.png') o uno zip che li contiene.",
        )
    return result


@router.get("/previews/{page}")
def get_preview(page: int):
    f = find_preview_file(page)
    if f is None:
        raise HTTPException(404, "Anteprima non trovata")
    return FileResponse(f)
