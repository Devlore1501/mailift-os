"""Integrazione Klaviyo per brand + impostazioni Notion globali."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import settings as cfg
from ..db import get_db
from ..models.db_models import Template
from ..models.schemas import (
    KlaviyoKeyIn,
    KlaviyoStatus,
    NotionSettingsIn,
    NotionSettingsOut,
)
from ..services import klaviyo, mockdata
from ..services.settings_store import get_setting, set_setting
from .brands import get_brand_or_404

router = APIRouter(prefix="/api", tags=["integrations"])


def _key_preview(key: str) -> str | None:
    return (key[:7] + "...") if key else None


def _status(brand) -> KlaviyoStatus:
    return KlaviyoStatus(
        configured=bool(brand.klaviyo_api_key),
        key_preview=_key_preview(brand.klaviyo_api_key),
        account_name=brand.klaviyo_account_name or None,
        last_sync_at=brand.klaviyo_last_sync_at,
    )


@router.put("/brands/{brand_id}/klaviyo", response_model=KlaviyoStatus)
def set_klaviyo_key(brand_id: int, payload: KlaviyoKeyIn, db: Session = Depends(get_db)):
    brand = get_brand_or_404(db, brand_id)
    brand.klaviyo_api_key = payload.api_key.strip()
    brand.klaviyo_account_name = ""
    db.commit()
    return _status(brand)


@router.delete("/brands/{brand_id}/klaviyo", status_code=204)
def unset_klaviyo_key(brand_id: int, db: Session = Depends(get_db)):
    brand = get_brand_or_404(db, brand_id)
    brand.klaviyo_api_key = ""
    brand.klaviyo_account_name = ""
    brand.klaviyo_snapshot = None
    brand.klaviyo_last_sync_at = None
    db.commit()


@router.get("/brands/{brand_id}/klaviyo/status", response_model=KlaviyoStatus)
def klaviyo_status(brand_id: int, db: Session = Depends(get_db)):
    return _status(get_brand_or_404(db, brand_id))


@router.post("/brands/{brand_id}/klaviyo/sync")
def klaviyo_sync(brand_id: int, db: Session = Depends(get_db)):
    brand = get_brand_or_404(db, brand_id)
    if brand.klaviyo_api_key:
        try:
            snapshot = klaviyo.build_snapshot(brand.klaviyo_api_key)
        except klaviyo.KlaviyoError as e:
            raise HTTPException(502, str(e))
    elif cfg.mock_mode():
        snapshot = mockdata.mock_klaviyo_snapshot()
    else:
        raise HTTPException(409, "Chiave API Klaviyo non configurata per questo brand")
    brand.klaviyo_snapshot = snapshot
    brand.klaviyo_account_name = snapshot.get("account_name", "")
    brand.klaviyo_last_sync_at = datetime.now(timezone.utc)
    db.commit()
    return snapshot


@router.get("/brands/{brand_id}/klaviyo/insights")
def klaviyo_insights(brand_id: int, db: Session = Depends(get_db)):
    brand = get_brand_or_404(db, brand_id)
    if not brand.klaviyo_snapshot:
        raise HTTPException(404, "Nessuno snapshot Klaviyo: eseguire prima una sincronizzazione")
    return brand.klaviyo_snapshot


# ---- Notion settings (globali)


def _notion_out(db: Session) -> NotionSettingsOut:
    token = get_setting(db, "notion_token")
    count = db.query(Template).count()
    last = (
        db.query(Template.last_synced_at).order_by(Template.last_synced_at.desc()).first()
    )
    return NotionSettingsOut(
        configured=bool(token),
        token_preview=(token[:7] + "...") if token else None,
        templates_db_id=get_setting(db, "notion_templates_db_id"),
        calendar_parent_page_id=get_setting(db, "notion_calendar_parent_id"),
        templates_synced=count,
        templates_last_sync_at=last[0] if last else None,
    )


@router.get("/settings/notion", response_model=NotionSettingsOut)
def get_notion_settings(db: Session = Depends(get_db)):
    return _notion_out(db)


@router.put("/settings/notion", response_model=NotionSettingsOut)
def put_notion_settings(payload: NotionSettingsIn, db: Session = Depends(get_db)):
    if payload.token is not None:
        set_setting(db, "notion_token", payload.token.strip())
    if payload.templates_db_id is not None:
        set_setting(db, "notion_templates_db_id", payload.templates_db_id.strip())
    if payload.calendar_parent_page_id is not None:
        set_setting(db, "notion_calendar_parent_id", payload.calendar_parent_page_id.strip())
    return _notion_out(db)
