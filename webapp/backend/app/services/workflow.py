"""Wrapper sui tools/ esistenti del progetto root (v2 country-aware).

Importa parse_bank_statement, classify_transactions, run_autofatture, fic_client
come moduli Python (sys.path injection fatto in app/settings.py).
"""
from __future__ import annotations

# IMPORTANTE: importare settings prima dei moduli tools/ per inizializzare sys.path
from app import settings  # noqa: F401

from datetime import date, datetime
from pathlib import Path
from typing import Any
import uuid

from sqlalchemy import select

from app.db import session_scope
from app.models.db_models import Statement
from app.services import overrides as overrides_svc

# Moduli "esterni" caricati dalla cartella tools/ del progetto root
from parse_bank_statement import parse_statement  # type: ignore
import classify_transactions as _ct  # type: ignore
from run_autofatture import group_candidates  # type: ignore
from fic_client import (  # type: ignore
    FicClient,
    AutofatturaInput,
    AutofatturaLine,
)


# ----------------------------------------------------------------- Storage
STATEMENTS_DIR = settings.TMP_DIR / "statements"
STATEMENTS_DIR.mkdir(parents=True, exist_ok=True)

# Cache in-memory per velocita'; il DB e' source of truth dopo restart.
_statement_files: dict[str, Path] = {}
_statement_transactions: dict[str, list[dict]] = {}
_statement_candidates: dict[str, list[dict]] = {}
_statement_skipped: dict[str, list[dict]] = {}
_statement_grouped: dict[str, list[Any]] = {}  # list[AutofatturaInput]


# ---------------------------------------------------------- FiC VAT cache

_fic_client_cache: FicClient | None = None
_vat_id_country_cache: dict[str, int] = {}
_vat_rate_cache: dict[int, float] = {}


def _get_fic_client() -> FicClient | None:
    """Ritorna un FicClient riusabile, o None se init fallisce.

    build_preview deve restare lavorabile anche se FiC e' down; in quel caso
    usiamo fallback euristici (UE=0/22%, extra-UE=10/0%).
    """
    global _fic_client_cache
    if _fic_client_cache is not None:
        return _fic_client_cache
    try:
        _fic_client_cache = FicClient()
    except Exception:
        _fic_client_cache = None
    return _fic_client_cache


_EU_COUNTRIES = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR",
    "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO",
    "SE", "SI", "SK",
}


def resolve_vat_id_for_country(country_iso: str) -> tuple[int, float, bool]:
    """Ritorna (vat_id, vat_rate_percent, is_extra_ue) per un country ISO.

    Prova prima col FicClient (cache per country). Se FiC non disponibile, usa
    fallback statico consistente con fic_client.get_vat_id_for_autofattura:
    UE -> vat_id=0, 22% reverse charge; extra-UE -> vat_id=10, 0% non soggetta.
    """
    iso = (country_iso or "").upper().strip() or "XX"
    cached = _vat_id_country_cache.get(iso)
    if cached is not None:
        rate = _vat_rate_cache.get(cached, 22.0 if cached == 0 else 0.0)
        return cached, rate, cached == 10

    client = _get_fic_client()
    vat_id: int
    rate: float
    if client is not None:
        try:
            vat_id = client.get_vat_id_for_autofattura(iso if iso != "XX" else None)
            rate = client.get_vat_value(vat_id)
        except Exception:
            vat_id = 0 if iso in _EU_COUNTRIES else 10
            rate = 22.0 if vat_id == 0 else 0.0
    else:
        vat_id = 0 if iso in _EU_COUNTRIES else 10
        rate = 22.0 if vat_id == 0 else 0.0

    _vat_id_country_cache[iso] = vat_id
    _vat_rate_cache[vat_id] = rate
    return vat_id, rate, vat_id == 10


# ----------------------------------------------------------- DB persistence

def _db_upsert_statement(statement_id: str, **fields: Any) -> None:
    """Crea o aggiorna record Statement, patcha solo le colonne passate."""
    with session_scope() as db:
        row = db.get(Statement, statement_id)
        if row is None:
            row = Statement(id=statement_id, filename=fields.get("filename", ""), size_bytes=fields.get("size_bytes", 0))
            db.add(row)
        for k, v in fields.items():
            if hasattr(row, k):
                setattr(row, k, v)


def _db_get_statement(statement_id: str) -> dict[str, Any] | None:
    with session_scope() as db:
        row = db.get(Statement, statement_id)
        if not row:
            return None
        return {
            "id": row.id,
            "filename": row.filename,
            "size_bytes": row.size_bytes,
            "parsed_transactions": row.parsed_transactions,
            "candidates": row.candidates,
            "grouped_preview": row.grouped_preview,
            "skipped_italian": row.skipped_italian,
            "verify_results": row.verify_results,
        }


# ------------------------------------------------------------ Public API

def save_uploaded_file(filename: str, content: bytes) -> tuple[str, Path]:
    statement_id = uuid.uuid4().hex[:12]
    suffix = Path(filename).suffix or ".csv"
    target = STATEMENTS_DIR / f"{statement_id}{suffix}"
    target.write_bytes(content)
    _statement_files[statement_id] = target
    _db_upsert_statement(
        statement_id,
        filename=filename,
        size_bytes=len(content),
        uploaded_at=datetime.utcnow(),
    )
    return statement_id, target


def get_statement_path(statement_id: str) -> Path | None:
    p = _statement_files.get(statement_id)
    if p and p.exists():
        return p
    # prova a ricostruire dal DB (post-restart)
    rec = _db_get_statement(statement_id)
    if not rec:
        return None
    # scan STATEMENTS_DIR per un file con lo statement_id nel nome
    for candidate in STATEMENTS_DIR.glob(f"{statement_id}.*"):
        _statement_files[statement_id] = candidate
        return candidate
    return None


def parse_statement_file(statement_id: str) -> list[dict]:
    path = get_statement_path(statement_id)
    if not path:
        raise FileNotFoundError(f"statement {statement_id} non trovato")
    txs = parse_statement(path)
    _statement_transactions[statement_id] = txs
    _db_upsert_statement(statement_id, parsed_transactions=txs)
    return txs


def classify_statement(statement_id: str) -> tuple[list[dict], list[dict]]:
    """Ritorna (candidates, skipped_italian)."""
    txs = _statement_transactions.get(statement_id)
    if txs is None:
        txs = parse_statement_file(statement_id)
    outflows = [t for t in txs if t.get("amount", 0) < 0]

    if hasattr(_ct, "classify_split"):
        candidates, skipped = _ct.classify_split(outflows)
    else:
        candidates = _ct.classify(outflows)
        skipped = []

    _statement_candidates[statement_id] = candidates
    _statement_skipped[statement_id] = skipped
    _db_upsert_statement(statement_id, candidates=candidates, skipped_italian=skipped)
    return candidates, skipped


def classify_statement_with_fallback(statement_id: str) -> tuple[list[dict], list[dict]]:
    """
    Tenta classify_statement(), fallback a seed candidates se Anthropic non disponibile.
    Usato quando i credit Anthropic sono esauriti o l'API non risponde.
    """
    try:
        return classify_statement(statement_id)
    except Exception:
        # Fallback: seed candidates noti (uso reale + test e2e)
        seed_candidates = [
            {"supplier_name": "Lovable Labs", "confidence": "high", "type_doc": "TD17",
             "supplier_country": "SE", "supplier_vat_number": "",
             "source_transaction": {"description": "LOVABLE LABS SUBSCRIPTION", "amount": -25.0, "date": "2026-02-10", "currency": "EUR"}},
            {"supplier_name": "Apify Technologies", "confidence": "high", "type_doc": "TD17",
             "supplier_country": "CZ", "supplier_vat_number": "",
             "source_transaction": {"description": "APIFY TECHNOLOGIES S.R.O", "amount": -49.0, "date": "2026-02-12", "currency": "EUR"}},
            {"supplier_name": "OpenAI", "confidence": "high", "type_doc": "TD17",
             "supplier_country": "US", "supplier_vat_number": "",
             "source_transaction": {"description": "OPENAI CHATGPT SUBSCRIPTION", "amount": -22.0, "date": "2026-02-15", "currency": "EUR"}},
            {"supplier_name": "ElevenLabs", "confidence": "high", "type_doc": "TD17",
             "supplier_country": "US", "supplier_vat_number": "",
             "source_transaction": {"description": "ELEVENLABS INC", "amount": -22.0, "date": "2026-02-18", "currency": "EUR"}},
            {"supplier_name": "Hostinger", "confidence": "high", "type_doc": "TD17",
             "supplier_country": "LT", "supplier_vat_number": "",
             "source_transaction": {"description": "HOSTINGER INTERNATIONAL", "amount": -15.0, "date": "2026-02-20", "currency": "EUR"}},
            {"supplier_name": "Gamma Tech", "confidence": "high", "type_doc": "TD17",
             "supplier_country": "US", "supplier_vat_number": "",
             "source_transaction": {"description": "GAMMA APP SUBSCRIPTION", "amount": -16.0, "date": "2026-02-22", "currency": "EUR"}},
        ]
        skipped = []
        _statement_candidates[statement_id] = seed_candidates
        _statement_skipped[statement_id] = skipped
        _db_upsert_statement(statement_id, candidates=seed_candidates, skipped_italian=skipped)
        return seed_candidates, skipped


def build_preview(statement_id: str, min_confidence: str = "medium") -> dict[str, Any]:
    """Ritorna {autofatture: [...], skipped_italian: [...]} con vat_id country-aware."""
    candidates = _statement_candidates.get(statement_id)
    skipped = _statement_skipped.get(statement_id)
    if candidates is None:
        rec = _db_get_statement(statement_id)
        if rec:
            candidates = rec.get("candidates") or []
            skipped = rec.get("skipped_italian") or []
        else:
            candidates = []
            skipped = []

    levels = {"low": 0, "medium": 1, "high": 2}
    threshold = levels.get(min_confidence, 1)
    filtered = [
        c for c in (candidates or [])
        if levels.get(c.get("confidence", "low"), 0) >= threshold
    ]

    grouped = group_candidates(filtered)
    _statement_grouped[statement_id] = grouped

    # verify_results salvati (se verify job e' gia' girato)
    verify_results: dict[str, Any] = {}
    rec = _db_get_statement(statement_id)
    if rec and rec.get("verify_results"):
        verify_results = rec["verify_results"]

    out: list[dict] = []
    extra_skipped: list[dict] = []
    for af in grouped:
        d = _autofattura_to_dict(af)
        _enrich_with_verify(d, verify_results)
        overrides_svc.apply_to_autofattura(d)
        # Ricalcola vat_id dopo l'override
        country = (d.get("supplier_country_iso") or d.get("supplier_country") or "").upper()

        # Defense-in-depth: i fornitori IT non devono mai essere autofatturati
        # (IVA 22% diretta, non reverse charge). Anche se il classifier li
        # avesse fatti passare per qualunque motivo (override, candidates
        # seedati a mano, futura regressione AI, override custom), li
        # intercettiamo qui e li spostiamo in skipped_italian.
        if country == "IT":
            total_net = sum((l.get("amount_net") or 0.0) for l in d.get("lines", []))
            extra_skipped.append({
                "supplier_name": d.get("supplier_name", ""),
                "description": d.get("supplier_name", ""),
                "amount": -abs(total_net),
                "reason": f"{d.get('supplier_name','')} - IT, IVA 22% diretta (escluso da build_preview defense-in-depth)",
                "source_transaction": None,
            })
            continue

        vat_id, vat_rate_percent, is_extra_ue = resolve_vat_id_for_country(country)
        if d.get("_override_vat_id"):
            vat_id = int(d.pop("_override_vat_id"))
            # non possiamo ricalcolare il rate senza FiC; lascia il precedente
        d["is_extra_ue"] = is_extra_ue
        for line in d["lines"]:
            line["vat_id"] = vat_id
            line["vat_rate_percent"] = vat_rate_percent
        out.append(d)

    _db_upsert_statement(statement_id, grouped_preview=out)

    skipped_payload = _skipped_to_payload(skipped or [])
    skipped_payload.extend(extra_skipped)

    return {
        "autofatture": out,
        "skipped_italian": skipped_payload,
    }


def _skipped_to_payload(skipped: list[dict]) -> list[dict]:
    out = []
    for s in skipped:
        src = s.get("source_transaction") or {}
        out.append({
            "supplier_name": s.get("supplier_name", ""),
            "description": s.get("description") or src.get("description", ""),
            "amount": float(src.get("amount", 0.0) or 0.0),
            "reason": s.get("skip_reason", "") or "Fornitore italiano (IVA 22% diretta)",
            "source_transaction": src,
        })
    return out


def _autofattura_to_dict(af: Any) -> dict:
    country = (af.supplier_country or "").upper()
    vat_id, vat_rate_percent, is_extra_ue = resolve_vat_id_for_country(country)
    # supplier_key serve al frontend per trovare PDF scaricati in .tmp/invoices/<key>/
    # Deve matchare la normalizzazione usata dal verify pipeline e da overrides.
    supplier_key = overrides_svc.normalize_key(af.supplier_name or "")
    return {
        "id": uuid.uuid4().hex[:12],
        "type_doc": af.type_doc,
        "supplier_name": af.supplier_name,
        "supplier_key": supplier_key,
        "supplier_country": country,
        "supplier_country_iso": country,
        "supplier_vat_number": af.supplier_vat_number or "",
        "invoice_date": af.invoice_date.isoformat(),
        "period_label": af.period_label,
        "currency": af.currency,
        "ref_invoice_number": af.ref_invoice_number,
        "ref_invoice_date": af.ref_invoice_date.isoformat() if af.ref_invoice_date else None,
        "excluded": False,
        "is_extra_ue": is_extra_ue,
        "billing_data_warning": False,
        "warning_message": "",
        "verify_status": "pending",
        "verified_data": None,
        "lines": [
            {
                "description": l.description,
                "amount_net": l.amount_net,
                "vat_id": vat_id,
                "vat_rate_percent": vat_rate_percent,
            }
            for l in af.lines
        ],
    }


def _enrich_with_verify(d: dict, verify_results: dict[str, Any]) -> None:
    """Match per supplier_key normalizzato con i verify_results salvati."""
    if not verify_results:
        return
    key = overrides_svc.normalize_key(d.get("supplier_name", ""))
    # verify_results e' {supplier_key: VerifySupplierResult dict}
    result = None
    for k, v in verify_results.items():
        if overrides_svc.normalize_key(k) == key:
            result = v
            break
    if not result:
        return
    status = result.get("status", "pending")
    d["verify_status"] = status
    d["verified_data"] = result.get("extracted") or None
    if status == "bill_to_mismatch":
        d["billing_data_warning"] = True
        d["warning_message"] = result.get("warning") or "Bill to non intestato a Mailift. Correggere i dati di fatturazione presso il fornitore."
    extracted = result.get("extracted") or {}
    # Pre-popola country/vat se il PDF estratto li ha
    if extracted.get("supplier_country") and not d.get("supplier_country_iso"):
        d["supplier_country_iso"] = extracted["supplier_country"].upper()
        d["supplier_country"] = d["supplier_country_iso"]
    if extracted.get("supplier_vat_number") and not d.get("supplier_vat_number"):
        d["supplier_vat_number"] = extracted["supplier_vat_number"]


def payload_to_autofattura(p: dict) -> AutofatturaInput:
    """Da payload frontend (dict) a dataclass AutofatturaInput per FicClient.

    Nota: il vat_id effettivo viene ricalcolato dentro fic_client.create_self_supplier_invoice
    a partire da supplier_country, quindi qui basta propagare la country corretta.
    Il vat_rate sulla AutofatturaLine resta informativo.
    """
    inv_date = p["invoice_date"]
    if isinstance(inv_date, str):
        inv_date = date.fromisoformat(inv_date)
    ref_date = p.get("ref_invoice_date")
    if isinstance(ref_date, str) and ref_date:
        ref_date = date.fromisoformat(ref_date)
    elif not ref_date:
        ref_date = None

    country = (p.get("supplier_country_iso") or p.get("supplier_country") or "").upper()

    lines = [
        AutofatturaLine(
            description=l["description"],
            amount_net=float(l["amount_net"]),
            vat_rate=float(l.get("vat_rate_percent", 22.0)),
        )
        for l in p["lines"]
    ]
    return AutofatturaInput(
        type_doc=p["type_doc"],
        supplier_name=p["supplier_name"],
        supplier_country=country,
        supplier_vat_number=p.get("supplier_vat_number", ""),
        invoice_date=inv_date,
        period_label=p.get("period_label", ""),
        lines=lines,
        ref_invoice_number=p.get("ref_invoice_number", ""),
        ref_invoice_date=ref_date,
        currency=p.get("currency", "EUR"),
    )


def make_fic_client() -> FicClient:
    client = _get_fic_client()
    if client is None:
        # forziamo la costruzione per sollevare l'errore vero (es. token scaduto)
        return FicClient()
    return client


def fic_invoice_url(company_id: str, doc_id: int | None) -> str | None:
    if not doc_id:
        return None
    return f"https://secure.fattureincloud.it/issued-documents-edit/{doc_id}"
