"""Tabelle SQLAlchemy per la webapp.

4 tabelle:
- Statement: CSV caricato + output intermedi (parsed, candidates, preview, verify).
- Job: progress tracking per job async (classify, verify, create). Write-through.
- SupplierOverride: override manuale di country/vat per un fornitore.
- RunHistory: un record per ogni chiamata a POST /autofatture/create (fatta o dry-run).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    filename: Mapped[str] = mapped_column(String(512))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    parsed_transactions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    candidates: Mapped[list | None] = mapped_column(JSON, nullable=True)
    grouped_preview: Mapped[list | None] = mapped_column(JSON, nullable=True)
    skipped_italian: Mapped[list | None] = mapped_column(JSON, nullable=True)
    verify_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), default="generic")  # classify, verify, create
    status: Mapped[str] = mapped_column(String(16), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    step_name: Mapped[str] = mapped_column(String(512), default="")
    total: Mapped[int] = mapped_column(Integer, default=0)
    current: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    statement_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("statements.id"), nullable=True)


class SupplierOverride(Base):
    __tablename__ = "supplier_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    supplier_key: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    supplier_name_display: Mapped[str] = mapped_column(String(512), default="")
    country_iso: Mapped[str] = mapped_column(String(2), default="")
    vat_number: Mapped[str] = mapped_column(String(64), default="")
    vat_id: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RunHistory(Base):
    __tablename__ = "run_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    statement_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    result_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
