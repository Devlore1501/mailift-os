"""CRUD prodotti, offerte e occasioni (scoped per brand)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.db_models import Launch, Occasion, Offer, Product
from ..models.schemas import (
    LaunchBase,
    LaunchCreate,
    LaunchOut,
    OccasionBase,
    OccasionCreate,
    OccasionOut,
    OccasionSuggestIn,
    OccasionSuggestOut,
    OfferBase,
    OfferCreate,
    OfferOut,
    ProductBase,
    ProductCreate,
    ProductOut,
)
from ..services import claude_ai
from .brands import get_brand_or_404

router = APIRouter(prefix="/api", tags=["catalog"])


def _apply(entity, payload) -> None:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(entity, key, value)


# ---- Products


@router.get("/brands/{brand_id}/products", response_model=list[ProductOut])
def list_products(brand_id: int, db: Session = Depends(get_db)):
    get_brand_or_404(db, brand_id)
    return db.query(Product).filter(Product.brand_id == brand_id).order_by(Product.name).all()


@router.post("/brands/{brand_id}/products", response_model=ProductOut, status_code=201)
def create_product(brand_id: int, payload: ProductCreate, db: Session = Depends(get_db)):
    get_brand_or_404(db, brand_id)
    product = Product(brand_id=brand_id)
    _apply(product, payload)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductBase, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Prodotto non trovato")
    _apply(product, payload)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Prodotto non trovato")
    db.delete(product)
    db.commit()


# ---- Offers


@router.get("/brands/{brand_id}/offers", response_model=list[OfferOut])
def list_offers(brand_id: int, db: Session = Depends(get_db)):
    get_brand_or_404(db, brand_id)
    return db.query(Offer).filter(Offer.brand_id == brand_id).order_by(Offer.id.desc()).all()


@router.post("/brands/{brand_id}/offers", response_model=OfferOut, status_code=201)
def create_offer(brand_id: int, payload: OfferCreate, db: Session = Depends(get_db)):
    get_brand_or_404(db, brand_id)
    offer = Offer(brand_id=brand_id)
    _apply(offer, payload)
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


@router.patch("/offers/{offer_id}", response_model=OfferOut)
def update_offer(offer_id: int, payload: OfferBase, db: Session = Depends(get_db)):
    offer = db.get(Offer, offer_id)
    if offer is None:
        raise HTTPException(404, "Offerta non trovata")
    _apply(offer, payload)
    db.commit()
    db.refresh(offer)
    return offer


@router.delete("/offers/{offer_id}", status_code=204)
def delete_offer(offer_id: int, db: Session = Depends(get_db)):
    offer = db.get(Offer, offer_id)
    if offer is None:
        raise HTTPException(404, "Offerta non trovata")
    db.delete(offer)
    db.commit()


# ---- Occasions


@router.get("/brands/{brand_id}/occasions", response_model=list[OccasionOut])
def list_occasions(brand_id: int, db: Session = Depends(get_db)):
    get_brand_or_404(db, brand_id)
    return (
        db.query(Occasion).filter(Occasion.brand_id == brand_id).order_by(Occasion.date).all()
    )


@router.post("/brands/{brand_id}/occasions", response_model=OccasionOut, status_code=201)
def create_occasion(brand_id: int, payload: OccasionCreate, db: Session = Depends(get_db)):
    get_brand_or_404(db, brand_id)
    occasion = Occasion(brand_id=brand_id)
    _apply(occasion, payload)
    db.add(occasion)
    db.commit()
    db.refresh(occasion)
    return occasion


@router.post("/brands/{brand_id}/occasions/suggest", response_model=OccasionSuggestOut)
def suggest_occasions(
    brand_id: int, payload: OccasionSuggestIn, db: Session = Depends(get_db)
):
    """Analizza festività, ponti e ricorrenze del paese del brand nel mese
    indicato e propone date + idee email da inserire a calendario."""
    brand = get_brand_or_404(db, brand_id)
    month = payload.month[:7]
    if len(month) != 7 or month[4] != "-":
        raise HTTPException(400, "Mese non valido, formato atteso YYYY-MM")
    country = brand.country or "IT"
    brand_ctx = {
        "name": brand.name,
        "description": brand.description,
        "positioning": brand.positioning,
        "avatar": brand.avatar or {},
        "prodotti": [p.name for p in brand.products][:20],
    }
    try:
        suggestions = claude_ai.suggest_occasions(brand_ctx, country, month)
    except Exception as e:
        raise HTTPException(502, f"Analisi festività fallita: {e}")
    return OccasionSuggestOut(country=country, month=month, suggestions=suggestions)


@router.patch("/occasions/{occasion_id}", response_model=OccasionOut)
def update_occasion(occasion_id: int, payload: OccasionBase, db: Session = Depends(get_db)):
    occasion = db.get(Occasion, occasion_id)
    if occasion is None:
        raise HTTPException(404, "Occasione non trovata")
    _apply(occasion, payload)
    db.commit()
    db.refresh(occasion)
    return occasion


@router.delete("/occasions/{occasion_id}", status_code=204)
def delete_occasion(occasion_id: int, db: Session = Depends(get_db)):
    occasion = db.get(Occasion, occasion_id)
    if occasion is None:
        raise HTTPException(404, "Occasione non trovata")
    db.delete(occasion)
    db.commit()


# ---- Lanci & Promo


@router.get("/brands/{brand_id}/launches", response_model=list[LaunchOut])
def list_launches(brand_id: int, db: Session = Depends(get_db)):
    get_brand_or_404(db, brand_id)
    return (
        db.query(Launch)
        .filter(Launch.brand_id == brand_id)
        .order_by(Launch.start_date.desc(), Launch.id.desc())
        .all()
    )


@router.post("/brands/{brand_id}/launches", response_model=LaunchOut, status_code=201)
def create_launch(brand_id: int, payload: LaunchCreate, db: Session = Depends(get_db)):
    get_brand_or_404(db, brand_id)
    launch = Launch(brand_id=brand_id)
    _apply(launch, payload)
    db.add(launch)
    db.commit()
    db.refresh(launch)
    return launch


@router.patch("/launches/{launch_id}", response_model=LaunchOut)
def update_launch(launch_id: int, payload: LaunchBase, db: Session = Depends(get_db)):
    launch = db.get(Launch, launch_id)
    if launch is None:
        raise HTTPException(404, "Lancio non trovato")
    _apply(launch, payload)
    db.commit()
    db.refresh(launch)
    return launch


@router.delete("/launches/{launch_id}", status_code=204)
def delete_launch(launch_id: int, db: Session = Depends(get_db)):
    launch = db.get(Launch, launch_id)
    if launch is None:
        raise HTTPException(404, "Lancio non trovato")
    db.delete(launch)
    db.commit()
