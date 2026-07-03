from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.db_models import Brand, Plan, Product
from ..models.schemas import BrandCreate, BrandBase, BrandOut, BrandSummary
from ..services import extractor

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
            .order_by(Plan.month_start.desc())
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
                last_plan_month_start=last_plan.month_start if last_plan else None,
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


def _kind_for(file: UploadFile) -> str | None:
    if file.content_type in extractor.ALLOWED_TYPES:
        return extractor.ALLOWED_TYPES[file.content_type]
    name = (file.filename or "").lower()
    if name.endswith(".pdf"):
        return "pdf"
    if name.endswith((".txt", ".md")):
        return "text"
    return None


@router.post("/{brand_id}/extract-profile")
async def extract_profile(
    brand_id: int,
    apply: bool = False,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Estrae il profilo brand da documenti caricati (PDF/testo).

    Con apply=true salva subito i campi estratti (solo quelli non vuoti,
    senza sovrascrivere valori già compilati) e crea i prodotti trovati.
    """
    brand = get_brand_or_404(db, brand_id)
    if not files:
        raise HTTPException(400, "Nessun file caricato")
    if len(files) > 3:
        raise HTTPException(400, "Massimo 3 file per estrazione")

    payload: list[tuple[str, bytes, str]] = []
    total = 0
    for f in files:
        kind = _kind_for(f)
        if kind is None:
            raise HTTPException(
                415, f"Formato non supportato: {f.filename}. Usa PDF, TXT o MD."
            )
        data = await f.read()
        total += len(data)
        if total > extractor.MAX_TOTAL_BYTES:
            raise HTTPException(413, "Documenti troppo grandi (max 20 MB totali)")
        payload.append((f.filename or "documento", data, kind))

    try:
        result = extractor.extract_profile(payload)
    except extractor.ExtractionError as e:
        raise HTTPException(502, str(e))

    products_created = 0
    if apply:
        for field in ("description", "tone_of_voice", "mission", "positioning"):
            value = (result.get(field) or "").strip()
            if value and not getattr(brand, field):
                setattr(brand, field, value)
        extracted_avatar = result.get("avatar") or {}
        if any(v for v in extracted_avatar.values()) and not any(
            v for v in (brand.avatar or {}).values()
        ):
            brand.avatar = extracted_avatar
        existing_names = {p.name.lower() for p in brand.products}
        for p in result.get("products") or []:
            name = (p.get("name") or "").strip()
            if not name or name.lower() in existing_names:
                continue
            db.add(
                Product(
                    brand_id=brand.id,
                    name=name,
                    category=p.get("category") or "",
                    price=p.get("price"),
                    is_best_seller=bool(p.get("is_best_seller")),
                )
            )
            existing_names.add(name.lower())
            products_created += 1
        db.commit()

    return {**result, "applied": apply, "products_created": products_created}
