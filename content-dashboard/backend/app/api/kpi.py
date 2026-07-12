from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as OrmSession

from ..auth import any_user
from ..db import get_db
from ..models import User
from ..services import kpi as kpi_service

router = APIRouter(prefix="/api/kpi", tags=["kpi"])


@router.get("/overview")
def overview(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    platform: str | None = Query(default=None),
    user: User = Depends(any_user),
    db: OrmSession = Depends(get_db),
):
    """FR-M2-04/05: KPI primari + vanity secondari + trend settimanale."""
    return kpi_service.overview(db, date_from, date_to, platform)


@router.get("/pillar-mix")
def pillar_mix(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    user: User = Depends(any_user),
    db: OrmSession = Depends(get_db),
):
    """FR-M1-08: mix pillar reale vs target con alert."""
    return kpi_service.pillar_mix(db, date_from, date_to)


@router.get("/breakdown")
def breakdown(
    by: str = Query(default="format"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    platform: str | None = Query(default=None),
    user: User = Depends(any_user),
    db: OrmSession = Depends(get_db),
):
    """FR-M2-06/07/08/09: aggregati per format/pillar/surface + winner/kill."""
    if by not in ("format", "pillar", "surface"):
        raise HTTPException(status_code=422, detail="by deve essere format|pillar|surface")
    return kpi_service.breakdown(db, by, date_from, date_to, platform)
