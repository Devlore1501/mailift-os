"""Pydantic schemas per request/response del backend (API v2)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------- System

class HealthResponse(BaseModel):
    status: Literal["ok", "error"]
    fic_token_valid: bool
    company: Optional[dict[str, Any]] = None
    detail: Optional[str] = None
    dry_run: bool = False
    db_ok: bool = False
    gmail_tokens_ok: dict[str, bool] = Field(default_factory=lambda: {"personal": False, "business": False})
    anthropic_api_ok: bool = False


class ConfigResponse(BaseModel):
    company_id: str
    company_name: Optional[str] = None
    numeration: str
    payment_method: str
    payment_account_hint: str
    dry_run: bool
    blacklist_count: int = 0


# ---------------------------------------------------------------- Statements

class UploadResponse(BaseModel):
    statement_id: str
    filename: str
    size_bytes: int


class Transaction(BaseModel):
    date: str
    amount: float
    currency: str = "EUR"
    description: str
    raw: Optional[str] = None


class ParseResponse(BaseModel):
    statement_id: str
    transactions: list[Transaction]
    outflows_count: int


# ---------------------------------------------------------------- Jobs

class JobInfo(BaseModel):
    id: str
    kind: str = "generic"
    status: Literal["pending", "running", "done", "error"]
    progress: int = 0
    step_name: str = ""
    total: int = 0
    current: int = 0
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float
    statement_id: Optional[str] = None


class JobStartResponse(BaseModel):
    job_id: str


# --------------------------------------------------------------- Autofatture

VerifyStatus = Literal["pending", "verified", "not_found", "bill_to_mismatch", "skipped", "pdf_only"]


class AutofatturaLinePayload(BaseModel):
    description: str
    amount_net: float
    vat_id: int
    vat_rate_percent: float


class AutofatturaPayload(BaseModel):
    """Una autofattura proposta / editata dall'utente lato frontend."""
    id: str  # uuid client-side per tracciare la riga
    type_doc: Literal["TD17", "TD18", "TD19"]
    supplier_name: str
    supplier_key: str = ""  # slug normalizzato, usato dal frontend per il path PDF preview
    supplier_country: str
    supplier_country_iso: str = ""
    supplier_vat_number: str = ""
    invoice_date: date
    period_label: str = ""
    currency: str = "EUR"
    ref_invoice_number: str = ""
    ref_invoice_date: Optional[date] = None
    excluded: bool = False
    is_extra_ue: bool = False
    billing_data_warning: bool = False
    warning_message: str = ""
    verify_status: VerifyStatus = "pending"
    verified_data: Optional[dict[str, Any]] = None
    lines: list[AutofatturaLinePayload]


class SkippedItalianItem(BaseModel):
    supplier_name: str
    description: str = ""
    amount: float = 0.0
    reason: str = ""
    source_transaction: Optional[dict[str, Any]] = None


class PreviewResponse(BaseModel):
    statement_id: str
    autofatture: list[AutofatturaPayload]
    skipped_italian: list[SkippedItalianItem] = Field(default_factory=list)


class CreateRequest(BaseModel):
    autofatture: list[AutofatturaPayload]
    dry_run: bool = False
    statement_id: Optional[str] = None


class CreatedItem(BaseModel):
    status: Literal["ok", "error", "skipped"]
    supplier: str
    type_doc: str
    total_net: float
    fic_id: Optional[int] = None
    fic_number: Optional[str] = None
    fic_numeration: Optional[str] = None
    fic_url: Optional[str] = None
    error: Optional[str] = None


# -------------------------------------------------------------- Verify supp.

class VerifySupplierResult(BaseModel):
    supplier_key: str
    supplier_name: str
    status: VerifyStatus
    pdf_count: int = 0
    pdfs: list[str] = Field(default_factory=list)  # relative paths sotto .tmp/invoices/<key>/
    extracted: Optional[dict[str, Any]] = None
    warning: Optional[str] = None
    error: Optional[str] = None


class VerifyResultsResponse(BaseModel):
    statement_id: str
    results: list[VerifySupplierResult]


# ------------------------------------------------------------------- Overrides

class SupplierOverridePayload(BaseModel):
    id: int
    supplier_key: str
    supplier_name_display: str
    country_iso: str
    vat_number: str
    vat_id: int
    note: str
    updated_at: datetime


class SupplierOverrideCreate(BaseModel):
    supplier_key: str
    supplier_name_display: str = ""
    country_iso: str = ""
    vat_number: str = ""
    vat_id: int = 0
    note: str = ""


# --------------------------------------------------------------------- History

class RunHistoryItem(BaseModel):
    id: int
    statement_id: Optional[str]
    started_at: datetime
    finished_at: Optional[datetime]
    dry_run: bool
    total_count: int
    created_count: int
    error_count: int
    skipped_count: int


class RunHistoryDetail(RunHistoryItem):
    result_json: Optional[list[dict[str, Any]]] = None


# ----------------------------------------------------------- Rejected PDFs

class VerifyRejectItem(BaseModel):
    supplier_key: str
    filename: str
    path: str
    size_bytes: int
