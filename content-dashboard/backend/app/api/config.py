from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession, joinedload

from ..auth import admin_only, any_user, editor_or_admin
from ..db import get_db
from ..enums import (
    CONTENT_STATUS_LABELS,
    CONTENT_STATUSES,
    DEFAULT_PILLAR_TARGETS,
    FORMATS,
    PILLARS,
    PLATFORMS,
    ROLES,
    SOURCE_TYPES,
    SURFACES,
)
from ..models import ActivityLog, PillarTarget, Setting, User
from ..schemas import PillarTargetIn, SettingsIn
from ..services.activity import log_activity
from ..services.kpi import get_settings_map
from ..settings import ANTHROPIC_API_KEY

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/health")
def health(db: OrmSession = Depends(get_db)):
    db_ok = True
    try:
        db.query(Setting).first()
    except Exception:  # noqa: BLE001
        db_ok = False
    return {"db_ok": db_ok, "anthropic_configured": bool(ANTHROPIC_API_KEY)}


@router.get("/config")
def get_config(user: User = Depends(any_user), db: OrmSession = Depends(get_db)):
    """Enum, soglie e target: tutto ciò che serve alla UI in un colpo solo."""
    targets = {row.pillar: row.target_pct for row in db.query(PillarTarget).all()}
    if not targets:
        targets = {k: float(v) for k, v in DEFAULT_PILLAR_TARGETS.items()}
    settings = {k: v for k, v in get_settings_map(db).items() if not k.startswith("_")}
    return {
        "pillars": PILLARS,
        "formats": FORMATS,
        "surfaces": SURFACES,
        "statuses": CONTENT_STATUSES,
        "status_labels": CONTENT_STATUS_LABELS,
        "platforms": PLATFORMS,
        "roles": ROLES,
        "source_types": SOURCE_TYPES,
        "pillar_targets": targets,
        "settings": settings,
        "anthropic_configured": bool(ANTHROPIC_API_KEY),
    }


@router.put("/config/pillar-targets")
def set_pillar_targets(body: PillarTargetIn, user: User = Depends(admin_only),
                       db: OrmSession = Depends(get_db)):
    unknown = set(body.targets) - set(PILLARS)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Pillar sconosciuti: {sorted(unknown)}")
    total = sum(body.targets.values())
    if abs(total - 100) > 0.5:
        raise HTTPException(status_code=422, detail=f"I target devono sommare a 100 (ora {total:g})")
    for pillar, pct in body.targets.items():
        row = db.get(PillarTarget, pillar)
        if row:
            row.target_pct = pct
        else:
            db.add(PillarTarget(pillar=pillar, target_pct=pct))
    log_activity(db, user, "settings", None, f"aggiornati target pillar: {body.targets}")
    db.commit()
    return {"ok": True, "targets": body.targets}


@router.put("/config/settings")
def set_settings(body: SettingsIn, user: User = Depends(admin_only),
                 db: OrmSession = Depends(get_db)):
    for key, value in body.values.items():
        if key.startswith("_"):
            raise HTTPException(status_code=422, detail=f"Chiave riservata: {key}")
        row = db.get(Setting, key)
        if row:
            row.value = value
        else:
            db.add(Setting(key=key, value=value))
    log_activity(db, user, "settings", None, f"aggiornate impostazioni: {sorted(body.values)}")
    db.commit()
    return {"ok": True}


@router.get("/activity")
def activity(limit: int = 100, user: User = Depends(editor_or_admin),
             db: OrmSession = Depends(get_db)):
    rows = (db.query(ActivityLog).options(joinedload(ActivityLog.user))
            .order_by(ActivityLog.at.desc()).limit(min(limit, 500)).all())
    return [
        {"id": r.id, "user": r.user.name if r.user else None, "entity": r.entity,
         "entity_id": r.entity_id, "action": r.action, "at": r.at}
        for r in rows
    ]
