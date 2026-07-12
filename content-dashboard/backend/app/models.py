"""Modello dati (§9 PRD) + sessioni auth."""
import json
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .db import Base


def utcnow():
    """UTC naive: SQLite non conserva il tz, quindi tutto il backend lavora in UTC naive."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="contributor")  # admin|editor|contributor
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utcnow)


class Session(Base):
    __tablename__ = "sessions"
    token = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User")


class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)  # rss|reddit|trend|competitor
    url = Column(String, nullable=False)
    label = Column(String, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    last_fetched_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)  # NFR-08: una fonte down logga e non blocca le altre
    created_at = Column(DateTime, default=utcnow)


class SourceItem(Base):
    __tablename__ = "source_items"
    __table_args__ = (UniqueConstraint("source_id", "url", name="uq_source_item_url"),)
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    snippet = Column(Text, nullable=True)
    fetched_at = Column(DateTime, default=utcnow)
    raw = Column(Text, nullable=True)
    processed = Column(Boolean, nullable=False, default=False)  # già passato all'AI

    source = relationship("Source")


class Idea(Base):
    """Idea madre (M1) e proposte dell'Idea Engine (M3, status=proposed)."""
    __tablename__ = "ideas"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    angle = Column(Text, nullable=True)
    pillar = Column(String, nullable=True)
    status = Column(String, nullable=False, default="approved")  # proposed|approved|discarded
    origin = Column(String, nullable=False, default="manual")  # ai|manual
    source_item_id = Column(Integer, ForeignKey("source_items.id"), nullable=True)
    relevance_score = Column(Integer, nullable=True)  # 1-10 (solo origin=ai)
    hook_draft = Column(Text, nullable=True)          # bozza hook proposta dall'AI
    suggested_format = Column(String, nullable=True)  # format suggerito dall'AI
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    source_item = relationship("SourceItem")
    contents = relationship("Content", back_populates="idea")


class Content(Base):
    __tablename__ = "contents"
    id = Column(Integer, primary_key=True)
    idea_id = Column(Integer, ForeignKey("ideas.id"), nullable=True, index=True)
    title = Column(String, nullable=True)  # label operativa; se vuota la UI usa il titolo dell'idea
    surface = Column(String, nullable=False, default="reel")  # reel|carousel|story|other
    format = Column(String, nullable=True)  # enum 12 format
    pillar = Column(String, nullable=True)  # ereditato dall'idea, override possibile
    status = Column(String, nullable=False, default="idea", index=True)
    script = Column(Text, nullable=True)
    hook = Column(Text, nullable=True)
    cta_keyword = Column(String, nullable=True)
    notes = Column(Text, nullable=True)  # note di regia
    critic_score = Column(Integer, nullable=True)  # 0-50, gate a 38
    scheduled_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    platform = Column(String, nullable=True, default="instagram")  # instagram|tiktok
    external_url = Column(String, nullable=True)
    asset_links = Column(Text, nullable=True)  # JSON array di link (Higgsfield/Gamma ecc.)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    idea = relationship("Idea", back_populates="contents")
    metrics = relationship("Metric", back_populates="content", cascade="all, delete-orphan")

    def asset_links_list(self):
        try:
            return json.loads(self.asset_links) if self.asset_links else []
        except (ValueError, TypeError):
            return []


class Metric(Base):
    """Snapshot metriche per contenuto (multi-riga = andamento nel tempo)."""
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False, index=True)
    captured_at = Column(DateTime, default=utcnow)
    # vanity
    views = Column(Integer, nullable=True)
    likes = Column(Integer, nullable=True)
    # segnali primari
    avg_retention_pct = Column(Float, nullable=True)
    hook_retention_pct = Column(Float, nullable=True)
    rewatch_rate = Column(Float, nullable=True)
    saves = Column(Integer, nullable=True)
    shares = Column(Integer, nullable=True)
    comments = Column(Integer, nullable=True)
    # composizione buyer (FR-M2-11)
    icp_comments = Column(Integer, nullable=True)
    non_icp_comments = Column(Integer, nullable=True)
    # funnel tie-in (FR-M2-10)
    dm_keyword_triggers = Column(Integer, nullable=True)
    fhs_clicks = Column(Integer, nullable=True)
    fhs_purchases = Column(Integer, nullable=True)

    content = relationship("Content", back_populates="metrics")

    # rate calcolati (save_rate = saves/views ecc.)
    @property
    def save_rate(self):
        return self.saves / self.views if self.saves is not None and self.views else None

    @property
    def share_rate(self):
        return self.shares / self.views if self.shares is not None and self.views else None

    @property
    def icp_ratio(self):
        icp = self.icp_comments or 0
        non = self.non_icp_comments or 0
        return icp / (icp + non) if (icp + non) > 0 else None

    @property
    def dm_fhs_rate(self):
        if self.fhs_purchases is not None and self.dm_keyword_triggers:
            return self.fhs_purchases / self.dm_keyword_triggers
        return None


class PillarTarget(Base):
    __tablename__ = "pillar_targets"
    pillar = Column(String, primary_key=True)
    target_pct = Column(Float, nullable=False)


class Setting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)


class ActivityLog(Base):
    """FR-X-04: chi ha cambiato stato/score."""
    __tablename__ = "activity_log"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    entity = Column(String, nullable=False)   # content|idea|source|settings|user
    entity_id = Column(Integer, nullable=True)
    action = Column(String, nullable=False)   # es. "status: critic → scheduled", "critic_score: 41"
    at = Column(DateTime, default=utcnow)

    user = relationship("User")
