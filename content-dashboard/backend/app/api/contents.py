import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as OrmSession, joinedload

from ..auth import any_user, editor_or_admin
from ..db import get_db
from ..enums import CONTENT_STATUS_LABELS, CONTENT_STATUSES, FORMATS, PILLARS, PLATFORMS, SURFACES
from ..models import Content, Idea, User, utcnow
from ..util import naive_utc
from ..schemas import ContentCreate, ContentOut, ContentUpdate, MetricOut, StatusChangeIn
from ..services.activity import log_activity
from ..services.idea_engine import generate_script
from ..services.kpi import compute_winner_ids, get_settings_map, latest_metric

router = APIRouter(prefix="/api/contents", tags=["contents"])

# Campi che un Contributor può modificare (FR-M1-09: script, hook, cta, note, asset)
CONTRIBUTOR_FIELDS = {"script", "hook", "cta_keyword", "notes", "asset_links", "title"}
# Stati raggiungibili da un Contributor (produzione, non programmazione/pubblicazione)
CONTRIBUTOR_STATUSES = {"idea", "script", "production", "critic"}


def _metric_out(m):
    if not m:
        return None
    data = MetricOut.model_validate(m).model_dump()
    data.update(save_rate=m.save_rate, share_rate=m.share_rate,
                icp_ratio=m.icp_ratio, dm_fhs_rate=m.dm_fhs_rate)
    return data


def serialize(content: Content, winner_ids: set[int] | None = None) -> dict:
    return {
        **{f: getattr(content, f) for f in (
            "id", "idea_id", "title", "surface", "format", "pillar", "status",
            "script", "hook", "cta_keyword", "notes", "critic_score",
            "scheduled_at", "published_at", "platform", "external_url",
            "created_by", "created_at",
        )},
        "asset_links": content.asset_links_list(),
        "idea_title": content.idea.title if content.idea else None,
        "latest_metric": _metric_out(latest_metric(content)),
        "is_winner": content.id in winner_ids if winner_ids is not None else None,
    }


def _validate_enums(pillar=None, fmt=None, surface=None, platform=None):
    checks = [(pillar, PILLARS, "pillar"), (fmt, FORMATS, "format"),
              (surface, SURFACES, "surface"), (platform, PLATFORMS, "platform")]
    for value, allowed, name in checks:
        if value is not None and value not in allowed:
            raise HTTPException(status_code=422, detail=f"{name} non valido: {value}")


@router.get("")
def list_contents(
    status: str | None = None,
    pillar: str | None = None,
    format: str | None = None,
    surface: str | None = None,
    platform: str | None = None,
    idea_id: int | None = None,
    created_by: int | None = None,
    scheduled_from: datetime | None = None,
    scheduled_to: datetime | None = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    user: User = Depends(any_user),
    db: OrmSession = Depends(get_db),
):
    q = db.query(Content).options(joinedload(Content.metrics), joinedload(Content.idea))
    if status:
        q = q.filter(Content.status.in_(status.split(",")))
    for field, value in (("pillar", pillar), ("format", format), ("surface", surface),
                         ("platform", platform), ("idea_id", idea_id), ("created_by", created_by)):
        if value is not None:
            q = q.filter(getattr(Content, field) == value)
    if scheduled_from:
        q = q.filter(Content.scheduled_at >= naive_utc(scheduled_from))
    if scheduled_to:
        q = q.filter(Content.scheduled_at <= naive_utc(scheduled_to))
    if published_from:
        q = q.filter(Content.published_at >= naive_utc(published_from))
    if published_to:
        q = q.filter(Content.published_at <= naive_utc(published_to))
    contents = q.order_by(Content.created_at.desc()).all()

    published = [c for c in contents if c.status in ("published", "archived")]
    winner_ids = compute_winner_ids(published, get_settings_map(db)) if published else set()
    return [serialize(c, winner_ids) for c in contents]


@router.get("/pipeline")
def pipeline_meta(user: User = Depends(any_user)):
    """Ordine e label degli stati per la board Kanban."""
    return {"statuses": CONTENT_STATUSES, "labels": CONTENT_STATUS_LABELS}


@router.get("/{content_id}")
def get_content(content_id: int, user: User = Depends(any_user), db: OrmSession = Depends(get_db)):
    content = db.get(Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Contenuto non trovato")
    return serialize(content)


@router.post("", status_code=201)
def create_content(body: ContentCreate, user: User = Depends(editor_or_admin),
                   db: OrmSession = Depends(get_db)):
    _validate_enums(pillar=body.pillar, fmt=body.format, surface=body.surface, platform=body.platform)
    content = Content(**body.model_dump(), status="idea", created_by=user.id)
    if not content.pillar and content.idea_id:
        idea = db.get(Idea, content.idea_id)
        content.pillar = idea.pillar if idea else None
    db.add(content)
    log_activity(db, user, "content", None, "creato contenuto")
    db.commit()
    db.refresh(content)
    return serialize(content)


@router.patch("/{content_id}")
def update_content(content_id: int, body: ContentUpdate, user: User = Depends(any_user),
                   db: OrmSession = Depends(get_db)):
    content = db.get(Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Contenuto non trovato")

    changed = body.model_dump(exclude_unset=True)
    if user.role == "contributor":
        forbidden = set(changed) - CONTRIBUTOR_FIELDS
        if forbidden:
            raise HTTPException(
                status_code=403,
                detail=f"Come Contributor non puoi modificare: {sorted(forbidden)}",
            )
    _validate_enums(pillar=changed.get("pillar"), fmt=changed.get("format"),
                    surface=changed.get("surface"), platform=changed.get("platform"))

    if "critic_score" in changed and changed["critic_score"] != content.critic_score:
        log_activity(db, user, "content", content.id,
                     f"critic_score: {content.critic_score} → {changed['critic_score']}")
    for field, value in changed.items():
        if field == "asset_links":
            content.asset_links = json.dumps(value)
        elif field in ("scheduled_at", "published_at") and isinstance(value, datetime):
            setattr(content, field, naive_utc(value))
        else:
            setattr(content, field, value)
    db.commit()
    db.refresh(content)
    return serialize(content)


@router.post("/{content_id}/status")
def change_status(content_id: int, body: StatusChangeIn, user: User = Depends(any_user),
                  db: OrmSession = Depends(get_db)):
    """Transizione di stato con gate qualità (FR-M1-05)."""
    content = db.get(Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Contenuto non trovato")
    new_status = body.status
    if new_status not in CONTENT_STATUSES:
        raise HTTPException(status_code=422, detail=f"Status non valido, usa uno di {CONTENT_STATUSES}")
    if new_status == content.status:
        return serialize(content)

    if user.role == "contributor" and new_status not in CONTRIBUTOR_STATUSES:
        raise HTTPException(
            status_code=403,
            detail="Come Contributor puoi muovere i contenuti solo fino allo stato Critico",
        )

    # GATE CRITICO: niente "Programmato" (né oltre) sotto soglia — vincolo non negoziabile §6.4
    gate = int(float(get_settings_map(db).get("critic_gate_min", "38")))
    if new_status in ("scheduled", "published") and content.status not in ("scheduled", "published"):
        if content.critic_score is None:
            raise HTTPException(
                status_code=422,
                detail=f"Gate qualità: serve uno score Critico (≥{gate}/50) prima di programmare. "
                       "Registra lo score nella colonna Critico.",
            )
        if content.critic_score < gate:
            raise HTTPException(
                status_code=422,
                detail=f"Gate qualità: score Critico {content.critic_score}/50 sotto la soglia {gate}. "
                       "Il contenuto non può essere programmato: rivedi hook/promessa/CTA e ripassa dal Critico.",
            )

    old = content.status
    content.status = new_status
    if new_status == "published" and content.published_at is None:
        content.published_at = utcnow()
    log_activity(db, user, "content", content.id,
                 f"status: {CONTENT_STATUS_LABELS[old]} → {CONTENT_STATUS_LABELS[new_status]}")
    db.commit()
    db.refresh(content)
    return serialize(content)


@router.post("/{content_id}/generate-script")
def generate_script_draft(content_id: int, user: User = Depends(any_user),
                          db: OrmSession = Depends(get_db)):
    """Bozza script AI dal brief (idea madre, angolo, hook, pillar, format).

    Ritorna solo la bozza: non salva nulla — l'umano rifinisce nella UI e preme Salva.
    Aperto anche ai Contributor: scrivere script è il loro lavoro.
    """
    content = db.get(Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Contenuto non trovato")
    result = generate_script(content, content.idea)
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])
    log_activity(db, user, "content", content_id, "generata bozza script AI")
    db.commit()
    return result


@router.delete("/{content_id}", status_code=204)
def delete_content(content_id: int, user: User = Depends(editor_or_admin),
                   db: OrmSession = Depends(get_db)):
    content = db.get(Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Contenuto non trovato")
    log_activity(db, user, "content", content_id, "eliminato contenuto")
    db.delete(content)
    db.commit()
