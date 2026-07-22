"""CRUD sync per SupplierOverride.

Uso tipico:
    overrides.apply(af_dict)  # patcha in-place country_iso/vat_number/vat_id se c'e' override
    overrides.list_all()
    overrides.upsert(payload)
    overrides.delete(override_id)
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import session_scope
from app.models.db_models import SupplierOverride


_SUFFIX_RE = re.compile(
    r"\b(limited|ltd|llc|inc|s\.?r\.?l\.?|s\.?p\.?a\.?|spa|srl|gmbh|ab|oy|bv|sa|plc|co|corp|corporation|labs|technologies|tech|platforms)\b",
    re.IGNORECASE,
)


def normalize_key(name: str) -> str:
    if not name:
        return ""
    s = name.lower().strip()
    s = _SUFFIX_RE.sub("", s)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def _to_payload(o: SupplierOverride) -> dict[str, Any]:
    return {
        "id": o.id,
        "supplier_key": o.supplier_key,
        "supplier_name_display": o.supplier_name_display,
        "country_iso": o.country_iso,
        "vat_number": o.vat_number,
        "vat_id": o.vat_id,
        "note": o.note,
        "updated_at": o.updated_at,
    }


def list_all() -> list[dict[str, Any]]:
    with session_scope() as db:
        rows = db.execute(select(SupplierOverride).order_by(SupplierOverride.supplier_key)).scalars().all()
        return [_to_payload(r) for r in rows]


def get_by_key(key: str) -> dict[str, Any] | None:
    if not key:
        return None
    with session_scope() as db:
        row = db.execute(select(SupplierOverride).where(SupplierOverride.supplier_key == key)).scalar_one_or_none()
        return _to_payload(row) if row else None


def upsert(data: dict[str, Any]) -> dict[str, Any]:
    key = normalize_key(data.get("supplier_key") or data.get("supplier_name_display") or "")
    if not key:
        raise ValueError("supplier_key obbligatorio")
    with session_scope() as db:
        row = db.execute(select(SupplierOverride).where(SupplierOverride.supplier_key == key)).scalar_one_or_none()
        if row is None:
            row = SupplierOverride(supplier_key=key)
            db.add(row)
        row.supplier_name_display = data.get("supplier_name_display", "") or key
        row.country_iso = (data.get("country_iso") or "").upper()
        row.vat_number = data.get("vat_number", "") or ""
        row.vat_id = int(data.get("vat_id") or 0)
        row.note = data.get("note", "") or ""
        row.updated_at = datetime.utcnow()
        db.flush()
        return _to_payload(row)


def delete(override_id: int) -> bool:
    with session_scope() as db:
        row = db.get(SupplierOverride, override_id)
        if not row:
            return False
        db.delete(row)
        return True


def apply_to_autofattura(af_dict: dict[str, Any]) -> dict[str, Any]:
    """Se esiste un override matchante, sovrascrive country/vat_number/vat_id."""
    key = normalize_key(af_dict.get("supplier_name", ""))
    if not key:
        return af_dict
    ov = get_by_key(key)
    if not ov:
        return af_dict
    if ov["country_iso"]:
        af_dict["supplier_country"] = ov["country_iso"]
        af_dict["supplier_country_iso"] = ov["country_iso"]
    if ov["vat_number"]:
        af_dict["supplier_vat_number"] = ov["vat_number"]
    # vat_id viene ricalcolato dal workflow tramite FicClient, ma se override forza un vat_id
    # specifico lo rispettiamo
    if ov["vat_id"]:
        af_dict["_override_vat_id"] = ov["vat_id"]
    return af_dict
