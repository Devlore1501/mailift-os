"""CRUD prodotti, offerte e occasioni (scoped per brand)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.db_models import Occasion, Offer, Product
from ..models.schemas import (
    OccasionBase,
    OccasionCreate,
    OccasionOut,
    OfferBase,
    OfferCreate,
    OfferOut,
    ProductBase,
    ProductCreate,
    ProductOut,
)
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
