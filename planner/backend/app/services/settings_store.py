"""Impostazioni globali persistite nel DB (Notion), con seed dall'env."""

from __future__ import annotations

from sqlalchemy.orm import Session

from .. import settings as cfg
from ..models.db_models import Setting

_ENV_DEFAULTS = {
    "notion_token": cfg.NOTION_TOKEN_ENV,
    "notion_templates_db_id": cfg.NOTION_TEMPLATES_DB_ID_ENV,
    "notion_calendar_parent_id": cfg.NOTION_CALENDAR_PARENT_ID_ENV,
}


def get_setting(db: Session, key: str) -> str:
    row = db.get(Setting, key)
    if row is not None:
        return row.value
    return _ENV_DEFAULTS.get(key, "")


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(Setting, key)
    if row is None:
        row = Setting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()


def notion_config(db: Session) -> dict:
    return {
        "token": get_setting(db, "notion_token"),
        "templates_db_id": get_setting(db, "notion_templates_db_id"),
        "calendar_parent_page_id": get_setting(db, "notion_calendar_parent_id"),
    }
