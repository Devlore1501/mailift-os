from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from pydantic import BaseModel

from ..auth import admin_only, any_user, editor_or_admin
from ..db import get_db
from ..enums import SOURCE_TYPES
from ..models import Source, SourceItem, User
from ..schemas import SourceCreate, SourceOut, SourceUpdate
from ..services.activity import log_activity
from ..services.idea_engine import fetch_sources, generate_evergreen, run_job, synthesize_proposals
from ..source_catalog import CATALOG

router = APIRouter(prefix="/api", tags=["idea-engine"])


@router.get("/sources/catalog")
def sources_catalog(user: User = Depends(any_user), db: OrmSession = Depends(get_db)):
    """Fonti consigliate (Reddit, Google News/Trends, blog) con stato di installazione."""
    installed = {url for (url,) in db.query(Source.url).all()}
    return [{**entry, "installed": entry["url"] in installed} for entry in CATALOG]


class CatalogAddIn(BaseModel):
    urls: list[str] | None = None  # None = tutte le mancanti


@router.post("/sources/catalog/add")
def add_from_catalog(body: CatalogAddIn, user: User = Depends(admin_only),
                     db: OrmSession = Depends(get_db)):
    installed = {url for (url,) in db.query(Source.url).all()}
    wanted = set(body.urls) if body.urls else None
    added = []
    for entry in CATALOG:
        if entry["url"] in installed:
            continue
        if wanted is not None and entry["url"] not in wanted:
            continue
        db.add(Source(type=entry["type"], url=entry["url"], label=entry["label"], active=True))
        added.append(entry["label"])
    if added:
        log_activity(db, user, "source", None, f"aggiunte {len(added)} fonti dal catalogo")
    db.commit()
    return {"added": added}


@router.get("/sources", response_model=list[SourceOut])
def list_sources(user: User = Depends(any_user), db: OrmSession = Depends(get_db)):
    return db.query(Source).order_by(Source.id).all()


@router.post("/sources", response_model=SourceOut, status_code=201)
def create_source(body: SourceCreate, user: User = Depends(admin_only),
                  db: OrmSession = Depends(get_db)):
    """FR-M3-01 (Admin): CRUD fonti."""
    if body.type not in SOURCE_TYPES:
        raise HTTPException(status_code=422, detail=f"Tipo non valido, usa uno di {SOURCE_TYPES}")
    source = Source(**body.model_dump())
    db.add(source)
    log_activity(db, user, "source", None, f"creata fonte {body.label}")
    db.commit()
    db.refresh(source)
    return source


@router.patch("/sources/{source_id}", response_model=SourceOut)
def update_source(source_id: int, body: SourceUpdate, user: User = Depends(admin_only),
                  db: OrmSession = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Fonte non trovata")
    changed = body.model_dump(exclude_unset=True)
    if "type" in changed and changed["type"] not in SOURCE_TYPES:
        raise HTTPException(status_code=422, detail=f"Tipo non valido, usa uno di {SOURCE_TYPES}")
    for field, value in changed.items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/sources/{source_id}", status_code=204)
def delete_source(source_id: int, user: User = Depends(admin_only),
                  db: OrmSession = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Fonte non trovata")
    db.query(SourceItem).filter(SourceItem.source_id == source_id).delete()
    log_activity(db, user, "source", source_id, f"eliminata fonte {source.label}")
    db.delete(source)
    db.commit()


@router.get("/source-items")
def list_source_items(processed: bool | None = None, limit: int = 100,
                      user: User = Depends(any_user), db: OrmSession = Depends(get_db)):
    q = db.query(SourceItem).order_by(SourceItem.fetched_at.desc())
    if processed is not None:
        q = q.filter(SourceItem.processed.is_(processed))
    return [
        {"id": it.id, "source_id": it.source_id, "title": it.title, "url": it.url,
         "snippet": it.snippet, "fetched_at": it.fetched_at, "processed": it.processed}
        for it in q.limit(min(limit, 500)).all()
    ]


@router.post("/idea-engine/run")
def run_idea_engine(user: User = Depends(editor_or_admin), db: OrmSession = Depends(get_db)):
    """Trigger manuale del job fetch + sintesi AI (oltre allo scheduler giornaliero)."""
    result = run_job(db)
    log_activity(db, user, "source", None,
                 f"run Idea Engine: {result['fetch']['total_added']} item, "
                 f"{result['synthesis'].get('proposals_created', 0)} proposte")
    db.commit()
    return result


@router.post("/idea-engine/fetch")
def run_fetch_only(user: User = Depends(editor_or_admin), db: OrmSession = Depends(get_db)):
    return fetch_sources(db)


@router.post("/idea-engine/synthesize")
def run_synthesis_only(user: User = Depends(editor_or_admin), db: OrmSession = Depends(get_db)):
    return synthesize_proposals(db)


@router.post("/idea-engine/brainstorm")
def run_brainstorm(n: int = 6, user: User = Depends(editor_or_admin),
                   db: OrmSession = Depends(get_db)):
    """Spunti evergreen (argomenti interessanti non legati a notizie) in coda review."""
    result = generate_evergreen(db, n=max(1, min(12, n)))
    if result.get("proposals_created"):
        log_activity(db, user, "idea", None,
                     f"brainstorm evergreen: {result['proposals_created']} spunti proposti")
        db.commit()
    return result
