from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import settings as cfg
from ..db import get_db
from ..models.schemas import SystemStatus
from ..services.settings_store import get_setting

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status", response_model=SystemStatus)
def status(db: Session = Depends(get_db)):
    return SystemStatus(
        ok=True,
        version=cfg.VERSION,
        anthropic_configured=bool(cfg.ANTHROPIC_API_KEY),
        notion_configured=bool(get_setting(db, "notion_token")),
        mock_mode=cfg.mock_mode(),
    )
