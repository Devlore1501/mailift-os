"""Pydantic schemas — rispecchiano planner/design/api_contract.md."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AvatarSchema(BaseModel):
    who: str = ""
    desires: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    language: str = ""
    notes: str = ""


class BrandBase(BaseModel):
    name: str | None = None
    description: str | None = None
    tone_of_voice: str | None = None
    mission: str | None = None
    positioning: str | None = None
    avatar: AvatarSchema | None = None
    emails_per_week: int | None = None
    country: str | None = None


class BrandCreate(BrandBase):
    name: str


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    tone_of_voice: str
    mission: str
    positioning: str
    avatar: dict
    emails_per_week: int
    country: str
    klaviyo_configured: bool = False
    created_at: datetime
    updated_at: datetime


class BrandSummary(BaseModel):
    id: int
    name: str
    positioning: str
    emails_per_week: int
    klaviyo_configured: bool
    num_products: int
    num_active_offers: int
    last_plan_status: str | None = None
    last_plan_month_start: str | None = None
    created_at: datetime


class ProductBase(BaseModel):
    name: str | None = None
    category: str | None = None
    price: float | None = None
    seasonality: str | None = None
    is_best_seller: bool | None = None
    url: str | None = None
    notes: str | None = None


class ProductCreate(ProductBase):
    name: str


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_id: int
    name: str
    category: str
    price: float | None
    seasonality: str
    is_best_seller: bool
    url: str
    notes: str


class OfferBase(BaseModel):
    name: str | None = None
    code: str | None = None
    discount: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    active: bool | None = None
    notes: str | None = None


class OfferCreate(OfferBase):
    name: str


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_id: int
    name: str
    code: str
    discount: str
    valid_from: str
    valid_to: str
    active: bool
    notes: str


class OccasionBase(BaseModel):
    name: str | None = None
    date: str | None = None
    notes: str | None = None


class OccasionCreate(OccasionBase):
    name: str


class OccasionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_id: int
    name: str
    date: str
    notes: str


class LaunchBase(BaseModel):
    name: str | None = None
    kind: Literal["lancio", "promo"] | None = None
    start_date: str | None = None
    end_date: str | None = None
    subject: str | None = None
    notes: str | None = None
    active: bool | None = None


class LaunchCreate(LaunchBase):
    name: str


class LaunchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_id: int
    name: str
    kind: str
    start_date: str
    end_date: str
    subject: str
    notes: str
    active: bool


class KlaviyoKeyIn(BaseModel):
    api_key: str


class KlaviyoStatus(BaseModel):
    configured: bool
    key_preview: str | None = None
    account_name: str | None = None
    last_sync_at: datetime | None = None
    error: str | None = None


class NotionSettingsIn(BaseModel):
    token: str | None = None
    templates_db_id: str | None = None
    calendar_parent_page_id: str | None = None


class NotionSettingsOut(BaseModel):
    configured: bool
    token_preview: str | None = None
    templates_db_id: str = ""
    calendar_parent_page_id: str = ""
    templates_synced: int = 0
    templates_last_sync_at: datetime | None = None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    notion_page_id: str
    name: str
    category: str
    canva_url: str
    notion_url: str
    tags: list
    preview_url: str = ""


class CanvaSetEntry(BaseModel):
    name: str
    count: int = 3
    category: str = ""  # vuota = assegnata automaticamente dal nome


class CanvaSetIn(BaseModel):
    canva_file_url: str = ""
    entries: list[CanvaSetEntry] = Field(default_factory=list)
    # in alternativa a entries: testo grezzo incollato da Notion ("About x3\n...")
    entries_text: str = ""


class CanvaSetOut(BaseModel):
    canva_file_url: str = ""
    entries: list[CanvaSetEntry] = Field(default_factory=list)
    template_count: int = 0
    categories: list[str] = Field(default_factory=list)


class PlanGenerateIn(BaseModel):
    month_start: str  # primo giorno del mese, YYYY-MM-01
    num_emails: int | None = None
    notes: str = ""


class SegmentInfo(BaseModel):
    name: str = ""
    klaviyo_segment_id: str | None = None
    rationale: str = ""


class PlanEmailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    position: int
    send_date: str
    send_day: str
    send_time: str
    objective: str
    format: str = "grafica"
    theme: str
    angle: str
    segment: dict
    subject_variants: list
    preview_text: str
    body: str
    blocks: list = Field(default_factory=list)
    campaign: dict | None = None
    products: list
    offer: dict | None
    canva_template: dict | None
    status: str
    notion_page_url: str
    updated_at: datetime


class PlanEmailPatch(BaseModel):
    send_date: str | None = None
    send_day: str | None = None
    send_time: str | None = None
    objective: Literal["nurturing", "promo", "storytelling", "vendita"] | None = None
    format: Literal["grafica", "testuale"] | None = None
    theme: str | None = None
    angle: str | None = None
    segment: dict | None = None
    subject_variants: list[str] | None = None
    preview_text: str | None = None
    body: str | None = None
    blocks: list | None = None
    campaign: dict | None = None
    products: list | None = None
    offer: dict | None = None
    canva_template: dict | None = None
    status: Literal["draft", "edited", "approved"] | None = None


class RegenerateIn(BaseModel):
    instructions: str = ""


class PlanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_id: int
    month_start: str
    status: str
    num_emails: int = 0
    notes: str
    error: str | None
    notion_url: str
    created_at: datetime
    updated_at: datetime


class PlanDetail(PlanSummary):
    emails: list[PlanEmailOut] = Field(default_factory=list)
    campaigns: list = Field(default_factory=list)
    context_snapshot: dict[str, Any] | None = None

    @field_validator("campaigns", mode="before")
    @classmethod
    def _campaigns_none_to_list(cls, v):
        return v or []


class PlanPatch(BaseModel):
    status: Literal["draft", "approved"] | None = None
    notes: str | None = None


class PublishResult(BaseModel):
    status: str
    notion_database_id: str | None = None
    notion_url: str | None = None
    pages: list[dict] = Field(default_factory=list)


class SystemStatus(BaseModel):
    ok: bool = True
    version: str
    anthropic_configured: bool
    notion_configured: bool
    mock_mode: bool


class OccasionSuggestIn(BaseModel):
    month: str  # "YYYY-MM"


class OccasionSuggestion(BaseModel):
    name: str
    date: str  # ISO
    kind: str  # festività | ponte | ricorrenza
    idea: str


class OccasionSuggestOut(BaseModel):
    country: str
    month: str
    suggestions: list[OccasionSuggestion]
