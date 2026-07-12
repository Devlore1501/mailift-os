from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as OrmSession, joinedload

from ..auth import any_user, editor_or_admin
from ..db import get_db
from ..enums import FORMATS, IDEA_STATUSES, PILLARS, SURFACES
from ..models import Content, Idea, User
from ..schemas import GenerateChildrenIn, IdeaCreate, IdeaOut, IdeaUpdate
from ..services.activity import log_activity

router = APIRouter(prefix="/api/ideas", tags=["ideas"])


def _validate(pillar=None, fmt=None, surface=None):
    if pillar is not None and pillar not in PILLARS:
        raise HTTPException(status_code=422, detail=f"Pillar non valido: {pillar}")
    if fmt is not None and fmt not in FORMATS:
        raise HTTPException(status_code=422, detail=f"Format non valido: {fmt}")
    if surface is not None and surface not in SURFACES:
        raise HTTPException(status_code=422, detail=f"Surface non valida: {surface}")


@router.get("", response_model=list[IdeaOut])
def list_ideas(
    status: str | None = Query(default=None),
    origin: str | None = Query(default=None),
    pillar: str | None = Query(default=None),
    user: User = Depends(any_user),
    db: OrmSession = Depends(get_db),
):
    q = db.query(Idea).options(joinedload(Idea.contents), joinedload(Idea.source_item))
    if status:
        q = q.filter(Idea.status == status)
    if origin:
        q = q.filter(Idea.origin == origin)
    if pillar:
        q = q.filter(Idea.pillar == pillar)
    # proposte in cima per rilevanza (FR-M3-04), poi le più recenti
    return q.order_by(Idea.relevance_score.desc().nullslast(), Idea.created_at.desc()).all()


@router.post("", response_model=IdeaOut, status_code=201)
def create_idea(body: IdeaCreate, user: User = Depends(any_user), db: OrmSession = Depends(get_db)):
    _validate(pillar=body.pillar, fmt=body.suggested_format)
    idea = Idea(
        title=body.title, angle=body.angle, pillar=body.pillar,
        hook_draft=body.hook_draft, suggested_format=body.suggested_format,
        status="approved", origin="manual", created_by=user.id,
    )
    db.add(idea)
    log_activity(db, user, "idea", None, f"creata idea madre: {body.title}")
    db.commit()
    db.refresh(idea)
    return idea


@router.patch("/{idea_id}", response_model=IdeaOut)
def update_idea(idea_id: int, body: IdeaUpdate, user: User = Depends(editor_or_admin),
                db: OrmSession = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea non trovata")
    _validate(pillar=body.pillar, fmt=body.suggested_format)
    if body.status is not None:
        if body.status not in IDEA_STATUSES:
            raise HTTPException(status_code=422, detail=f"Status non valido, usa uno di {IDEA_STATUSES}")
        if body.status != idea.status:
            log_activity(db, user, "idea", idea.id, f"status: {idea.status} → {body.status}")
        idea.status = body.status
    for field in ("title", "angle", "pillar", "hook_draft", "suggested_format"):
        value = getattr(body, field)
        if value is not None:
            setattr(idea, field, value)
    db.commit()
    db.refresh(idea)
    return idea


@router.post("/{idea_id}/children", response_model=IdeaOut, status_code=201)
def generate_children(idea_id: int, body: GenerateChildrenIn,
                      user: User = Depends(editor_or_admin), db: OrmSession = Depends(get_db)):
    """FR-M1-02: da una idea madre genera N contenuti figli (surface + format)."""
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea non trovata")
    if idea.status != "approved":
        raise HTTPException(status_code=422, detail="Solo un'idea approvata può generare contenuti")
    if not body.children:
        raise HTTPException(status_code=422, detail="Nessun output richiesto")
    for spec in body.children:
        _validate(fmt=spec.format, surface=spec.surface)
        db.add(Content(
            idea_id=idea.id,
            title=spec.title,
            surface=spec.surface,
            format=spec.format or idea.suggested_format,
            pillar=idea.pillar,
            hook=idea.hook_draft if spec.surface == "reel" else None,
            status="idea",
            created_by=user.id,
        ))
    log_activity(db, user, "idea", idea.id, f"generati {len(body.children)} contenuti figli")
    db.commit()
    db.refresh(idea)
    return idea
