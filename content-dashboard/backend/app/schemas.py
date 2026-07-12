"""Pydantic schemas del contratto API."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---- Auth / users ----

class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    active: bool


class LoginOut(BaseModel):
    token: str
    user: UserOut


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = "contributor"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8)


# ---- Ideas ----

class IdeaCreate(BaseModel):
    title: str
    angle: Optional[str] = None
    pillar: Optional[str] = None
    hook_draft: Optional[str] = None
    suggested_format: Optional[str] = None


class IdeaUpdate(BaseModel):
    title: Optional[str] = None
    angle: Optional[str] = None
    pillar: Optional[str] = None
    hook_draft: Optional[str] = None
    suggested_format: Optional[str] = None
    status: Optional[str] = None  # proposed|approved|discarded


class SourceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_id: int
    title: str
    url: str
    snippet: Optional[str] = None
    fetched_at: Optional[datetime] = None


class ContentBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: Optional[str] = None
    surface: str
    format: Optional[str] = None
    status: str
    critic_score: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None


class IdeaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    angle: Optional[str] = None
    pillar: Optional[str] = None
    status: str
    origin: str
    source_item_id: Optional[int] = None
    relevance_score: Optional[int] = None
    hook_draft: Optional[str] = None
    suggested_format: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    source_item: Optional[SourceItemOut] = None
    contents: list[ContentBrief] = []


# ---- Contents ----

class ContentChildSpec(BaseModel):
    surface: str = "reel"
    format: Optional[str] = None
    title: Optional[str] = None


class GenerateChildrenIn(BaseModel):
    children: list[ContentChildSpec]


class ContentCreate(BaseModel):
    idea_id: Optional[int] = None
    title: Optional[str] = None
    surface: str = "reel"
    format: Optional[str] = None
    pillar: Optional[str] = None
    platform: Optional[str] = "instagram"


class ContentUpdate(BaseModel):
    title: Optional[str] = None
    surface: Optional[str] = None
    format: Optional[str] = None
    pillar: Optional[str] = None
    script: Optional[str] = None
    hook: Optional[str] = None
    cta_keyword: Optional[str] = None
    notes: Optional[str] = None
    critic_score: Optional[int] = Field(default=None, ge=0, le=50)
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    platform: Optional[str] = None
    external_url: Optional[str] = None
    asset_links: Optional[list[str]] = None


class StatusChangeIn(BaseModel):
    status: str


class MetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    content_id: int
    captured_at: Optional[datetime] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    avg_retention_pct: Optional[float] = None
    hook_retention_pct: Optional[float] = None
    rewatch_rate: Optional[float] = None
    saves: Optional[int] = None
    shares: Optional[int] = None
    comments: Optional[int] = None
    icp_comments: Optional[int] = None
    non_icp_comments: Optional[int] = None
    dm_keyword_triggers: Optional[int] = None
    fhs_clicks: Optional[int] = None
    fhs_purchases: Optional[int] = None
    save_rate: Optional[float] = None
    share_rate: Optional[float] = None
    icp_ratio: Optional[float] = None
    dm_fhs_rate: Optional[float] = None


class ContentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    idea_id: Optional[int] = None
    title: Optional[str] = None
    surface: str
    format: Optional[str] = None
    pillar: Optional[str] = None
    status: str
    script: Optional[str] = None
    hook: Optional[str] = None
    cta_keyword: Optional[str] = None
    notes: Optional[str] = None
    critic_score: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    platform: Optional[str] = None
    external_url: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    asset_links: list[str] = []
    idea_title: Optional[str] = None
    latest_metric: Optional[MetricOut] = None
    is_winner: Optional[bool] = None


# ---- Metrics ----

class MetricIn(BaseModel):
    captured_at: Optional[datetime] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    avg_retention_pct: Optional[float] = None
    hook_retention_pct: Optional[float] = None
    rewatch_rate: Optional[float] = None
    saves: Optional[int] = None
    shares: Optional[int] = None
    comments: Optional[int] = None
    icp_comments: Optional[int] = None
    non_icp_comments: Optional[int] = None
    dm_keyword_triggers: Optional[int] = None
    fhs_clicks: Optional[int] = None
    fhs_purchases: Optional[int] = None


# ---- Sources ----

class SourceCreate(BaseModel):
    type: str
    url: str
    label: str
    active: bool = True


class SourceUpdate(BaseModel):
    type: Optional[str] = None
    url: Optional[str] = None
    label: Optional[str] = None
    active: Optional[bool] = None


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    url: str
    label: str
    active: bool
    last_fetched_at: Optional[datetime] = None
    last_error: Optional[str] = None


# ---- Settings ----

class PillarTargetIn(BaseModel):
    targets: dict[str, float]  # pillar -> target_pct (somma 100)


class SettingsIn(BaseModel):
    values: dict[str, str]
