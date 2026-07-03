from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Brand(Base):
    """Workspace di un cliente: tutti i dati sono scoped su brand_id."""

    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    tone_of_voice: Mapped[str] = mapped_column(Text, default="")
    mission: Mapped[str] = mapped_column(Text, default="")
    positioning: Mapped[str] = mapped_column(Text, default="")
    avatar: Mapped[dict] = mapped_column(JSON, default=dict)
    emails_per_week: Mapped[int] = mapped_column(Integer, default=3)
    country: Mapped[str] = mapped_column(String(5), default="IT")

    klaviyo_api_key: Mapped[str] = mapped_column(String(200), default="")
    klaviyo_account_name: Mapped[str] = mapped_column(String(200), default="")
    klaviyo_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    klaviyo_last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    products: Mapped[list["Product"]] = relationship(
        back_populates="brand", cascade="all, delete-orphan"
    )
    offers: Mapped[list["Offer"]] = relationship(
        back_populates="brand", cascade="all, delete-orphan"
    )
    occasions: Mapped[list["Occasion"]] = relationship(
        back_populates="brand", cascade="all, delete-orphan"
    )
    plans: Mapped[list["Plan"]] = relationship(
        back_populates="brand", cascade="all, delete-orphan"
    )
    launches: Mapped[list["Launch"]] = relationship(
        back_populates="brand", cascade="all, delete-orphan"
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(200), default="")
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    seasonality: Mapped[str] = mapped_column(String(200), default="")
    is_best_seller: Mapped[bool] = mapped_column(Boolean, default=False)
    url: Mapped[str] = mapped_column(String(500), default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    brand: Mapped[Brand] = relationship(back_populates="products")


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    code: Mapped[str] = mapped_column(String(100), default="")
    discount: Mapped[str] = mapped_column(String(100), default="")
    valid_from: Mapped[str] = mapped_column(String(20), default="")  # ISO date
    valid_to: Mapped[str] = mapped_column(String(20), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")

    brand: Mapped[Brand] = relationship(back_populates="offers")


class Occasion(Base):
    __tablename__ = "occasions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    date: Mapped[str] = mapped_column(String(20), default="")  # ISO date
    notes: Mapped[str] = mapped_column(Text, default="")

    brand: Mapped[Brand] = relationship(back_populates="occasions")


class Launch(Base):
    """Lancio prodotto o promo pianificata: genera una sequenza email dedicata."""

    __tablename__ = "launches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="lancio")  # lancio | promo
    start_date: Mapped[str] = mapped_column(String(20), default="")  # ISO
    end_date: Mapped[str] = mapped_column(String(20), default="")
    subject: Mapped[str] = mapped_column(Text, default="")  # prodotto/offerta protagonista
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    brand: Mapped[Brand] = relationship(back_populates="launches")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), index=True)
    # primo giorno del mese pianificato (la colonna si chiama week_start per
    # compatibilità con i DB creati quando il piano era settimanale)
    month_start: Mapped[str] = mapped_column("week_start", String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="generating")
    notes: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # strategia delle sequenze lancio/promo del mese: [{name, kind, strategy, proposals}]
    campaigns: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notion_database_id: Mapped[str] = mapped_column(String(100), default="")
    notion_url: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    brand: Mapped[Brand] = relationship(back_populates="plans")
    emails: Mapped[list["PlanEmail"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="PlanEmail.position"
    )


class PlanEmail(Base):
    __tablename__ = "plan_emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=1)
    send_date: Mapped[str] = mapped_column(String(20), default="")
    send_day: Mapped[str] = mapped_column(String(20), default="")
    send_time: Mapped[str] = mapped_column(String(10), default="09:00")
    objective: Mapped[str] = mapped_column(String(30), default="nurturing")
    format: Mapped[str] = mapped_column(String(20), default="grafica")
    theme: Mapped[str] = mapped_column(Text, default="")
    angle: Mapped[str] = mapped_column(Text, default="")
    segment: Mapped[dict] = mapped_column(JSON, default=dict)
    subject_variants: Mapped[list] = mapped_column(JSON, default=list)
    preview_text: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    # scaletta per il designer (email grafiche): lista di blocchi copy
    blocks: Mapped[list] = mapped_column(JSON, default=list)
    # appartenenza a una sequenza lancio/promo: {name, role} oppure null
    campaign: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    products: Mapped[list] = mapped_column(JSON, default=list)
    offer: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    canva_template: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    notion_page_url: Mapped[str] = mapped_column(String(500), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    plan: Mapped[Plan] = relationship(back_populates="emails")


class Template(Base):
    """Cache locale dei template Canva letti dal database Notion."""

    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notion_page_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300), default="")
    category: Mapped[str] = mapped_column(String(100), default="", index=True)
    canva_url: Mapped[str] = mapped_column(String(600), default="")
    notion_url: Mapped[str] = mapped_column(String(600), default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    preview_url: Mapped[str] = mapped_column(String(600), default="")
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Setting(Base):
    """Key-value per impostazioni globali (es. Notion)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
