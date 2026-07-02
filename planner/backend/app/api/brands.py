from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.db_models import Brand, Plan
from ..models.schemas import BrandCreate, BrandBase, BrandOut, BrandSummary

router = APIRouter(prefix="/api/brands", tags=["brands"])


def get_brand_or_404(db: Session, brand_id: int) -> Brand:
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(404, "Brand non trovato")
    return brand


def _to_out(brand: Brand) -> BrandOut:
    out = BrandOut.model_validate(brand)
    out.klaviyo_configured = bool(brand.klaviyo_api_key)
    return out


@router.get("", response_model=list[BrandSummary])
def list_brands(db: Session = Depends(get_db)):
    result = []
    for b in db.query(Brand).order_by(Brand.name).all():
        last_plan = (
            db.query(Plan)
            .filter(Plan.brand_id == b.id)
            .order_by(Plan.week_start.desc())
            .first()
        )
        result.append(
            BrandSummary(
                id=b.id,
                name=b.name,
                positioning=b.positioning,
                emails_per_week=b.emails_per_week,
                klaviyo_configured=bool(b.klaviyo_api_key),
                num_products=len(b.products),
                num_active_offers=sum(1 for o in b.offers if o.active),
                last_plan_status=last_plan.status if last_plan else None,
                last_plan_week_start=last_plan.week_start if last_plan else None,
                created_at=b.created_at,
            )
        )
    return result


@router.post("", response_model=BrandOut, status_code=201)
def create_brand(payload: BrandCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    if data.get("avatar") is not None:
        data["avatar"] = payload.avatar.model_dump()
    brand = Brand(**data)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return _to_out(brand)


@router.get("/{brand_id}", response_model=BrandOut)
def get_brand(brand_id: int, db: Session = Depends(get_db)):
    return _to_out(get_brand_or_404(db, brand_id))


@router.patch("/{brand_id}", response_model=BrandOut)
def update_brand(brand_id: int, payload: BrandBase, db: Session = Depends(get_db)):
    brand = get_brand_or_404(db, brand_id)
    data = payload.model_dump(exclude_unset=True)
    if "avatar" in data and payload.avatar is not None:
        data["avatar"] = payload.avatar.model_dump()
    for key, value in data.items():
        setattr(brand, key, value)
    db.commit()
    db.refresh(brand)
    return _to_out(brand)


@router.delete("/{brand_id}", status_code=204)
def delete_brand(brand_id: int, db: Session = Depends(get_db)):
    brand = get_brand_or_404(db, brand_id)
    db.delete(brand)
    db.commit()
