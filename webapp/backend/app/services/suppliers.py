"""Wrapper su tools/verify_suppliers_from_email.py per il flusso webapp.

Espone:
- `run_verify_for_preview(statement_id, progress_cb)` → verify tutti i fornitori
  del preview, salva risultati nello Statement DB, chiama progress_cb dopo ogni
  fornitore.
- `get_verify_results(statement_id)` → legge risultati dal DB.
- `list_rejects()`, `get_reject_path(...)` → quarantine PDFs.
- `list_invoices_for_supplier(key)`, `get_invoice_path(...)` → PDFs scaricati.
"""
from __future__ import annotations

# settings -> inietta tools/ in sys.path
from app import settings  # noqa: F401

import logging
import os
import time
import traceback
from pathlib import Path
from typing import Any, Callable

from app.services import workflow as workflow_svc
from app.services import overrides as overrides_svc

# tools/verify_suppliers_from_email.py
import verify_suppliers_from_email as vsfe  # type: ignore
from gmail_client import load_service  # type: ignore


logger = logging.getLogger("app.services.suppliers")

ROOT = settings.PROJECT_ROOT
INVOICES_DIR = ROOT / ".tmp" / "invoices"
REJECTS_DIR = ROOT / ".tmp" / "invoices_rejected"

# Cap ragionevole per chiamata Gmail/Anthropic per fornitore
PER_SUPPLIER_TIMEOUT_S = 30.0
_anthropic_ping_cache: bool | None = None


def _supplier_lookup(name: str):
    """Matcha uno dei SUPPLIERS di vsfe in base al supplier_name."""
    key_norm = overrides_svc.normalize_key(name)
    # prova match diretto sul key
    for s in vsfe.SUPPLIERS:
        if overrides_svc.normalize_key(s.key) == key_norm:
            return s
    # match per substring sul display_name
    low = (name or "").lower()
    for s in vsfe.SUPPLIERS:
        if s.display_name.lower() in low or s.key in low:
            return s
    return None


def _anthropic_available() -> bool:
    """True se ANTHROPIC_API_KEY e' presente E un ping leggero non fallisce.

    Il ping viene cachato per processo; se fallisce il job fa skip-analysis
    (scarica solo i PDF, senza parsing) e popola verify_status='pdf_only'.
    """
    global _anthropic_ping_cache
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY mancante → analisi PDF disabilitata (pdf_only)")
        return False
    if _anthropic_ping_cache is not None:
        return _anthropic_ping_cache
    try:
        from anthropic import Anthropic  # type: ignore

        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-6")
        # Ping minimale: 1 token, prompt banale
        client.messages.create(
            model=model,
            max_tokens=1,
            messages=[{"role": "user", "content": "ok"}],
        )
        _anthropic_ping_cache = True
        logger.info("Anthropic ping ok (model=%s) → analisi PDF abilitata", model)
    except Exception as e:
        _anthropic_ping_cache = False
        logger.warning("Anthropic ping fallito: %s → fallback pdf_only", e)
    return _anthropic_ping_cache


def _build_services() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for account in ("business", "personal"):
        try:
            out[account] = load_service(account)
            logger.info("Gmail service loaded: %s", account)
        except Exception as e:
            logger.warning("Gmail service load failed for %s: %s", account, e)
    return out


def run_verify_for_preview(
    statement_id: str,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> dict[str, dict[str, Any]]:
    """Per ogni fornitore del preview dello statement, cerca/scarica/analizza.

    Ritorna {supplier_key: result_dict} dove result_dict ha la shape di
    VerifySupplierResult (schemas.py). Salva anche in Statement.verify_results.
    """
    logger.info("verify start: statement_id=%s", statement_id)
    rec = workflow_svc._db_get_statement(statement_id)
    if not rec:
        raise FileNotFoundError(f"statement {statement_id} non trovato")
    preview = rec.get("grouped_preview") or []
    if not preview:
        # fallback: ricalcola
        logger.info("verify: preview vuoto, ricalcolo build_preview")
        built = workflow_svc.build_preview(statement_id)
        preview = built.get("autofatture", [])

    services = _build_services()
    analyze_enabled = _anthropic_available()
    logger.info(
        "verify setup: preview=%d, gmail_accounts=%s, analyze_enabled=%s",
        len(preview), list(services.keys()), analyze_enabled,
    )

    results: dict[str, dict[str, Any]] = {}
    total = len(preview)
    t0_all = time.time()
    for i, af in enumerate(preview, 1):
        name = af.get("supplier_name", "")
        key_norm = overrides_svc.normalize_key(name)
        if progress_cb:
            try:
                progress_cb(i, total, name)
            except Exception as cb_err:  # pragma: no cover — non deve bloccare
                logger.warning("progress_cb error: %s", cb_err)

        t0 = time.time()
        logger.info("verify [%d/%d] %s", i, total, name)

        s = _supplier_lookup(name)
        if s is None:
            logger.info("  not in SUPPLIERS catalog")
            results[key_norm or name] = {
                "supplier_key": key_norm or name,
                "supplier_name": name,
                "status": "not_found",
                "pdf_count": 0,
                "pdfs": [],
                "extracted": None,
                "warning": "Supplier non presente nel catalog SUPPLIERS di verify_suppliers_from_email",
                "error": None,
            }
            continue

        if not services:
            logger.warning("  nessun Gmail service → salto")
            results[s.key] = {
                "supplier_key": s.key,
                "supplier_name": name,
                "status": "not_found",
                "pdf_count": 0,
                "pdfs": [],
                "extracted": None,
                "warning": "Nessun account Gmail disponibile (token mancanti)",
                "error": None,
            }
            continue

        try:
            found = vsfe.find_invoices_for_supplier(services, s, max_msgs=2)
        except Exception as e:
            logger.error("  gmail lookup failed: %s", e, exc_info=True)
            results[s.key] = {
                "supplier_key": s.key,
                "supplier_name": name,
                "status": "not_found",
                "pdf_count": 0,
                "pdfs": [],
                "extracted": None,
                "warning": None,
                "error": f"gmail lookup: {e}",
            }
            continue

        if not found:
            rej_dir = REJECTS_DIR / s.key
            has_rejects = rej_dir.exists() and any(rej_dir.glob("*.pdf"))
            logger.info("  no PDF found (has_rejects=%s)", has_rejects)
            results[s.key] = {
                "supplier_key": s.key,
                "supplier_name": name,
                "status": "bill_to_mismatch" if has_rejects else "not_found",
                "pdf_count": 0,
                "pdfs": [],
                "extracted": None,
                "warning": ("Nessun PDF con bill to Mailift. Fatture trovate ma intestate a nominativo personale — verifica billing presso il fornitore." if has_rejects else "Nessun PDF trovato via Gmail"),
                "error": None,
            }
            continue

        pdfs_rel = [str(p.relative_to(INVOICES_DIR)) for _, _, p in found]
        extracted: dict[str, Any] | None = None
        status: str = "verified"
        err: str | None = None

        if analyze_enabled:
            try:
                extracted = vsfe.analyze_pdf(found[0][2])
            except Exception as e:
                logger.error("  analyze_pdf failed: %s", e, exc_info=True)
                err = f"analyze: {e}"
                status = "pdf_only"
        else:
            # Fallback deterministico: abbiamo i PDF ma non i dati strutturati
            status = "pdf_only"

        dt = time.time() - t0
        logger.info(
            "  -> %s (pdfs=%d, analyze_err=%s, %.1fs)",
            status, len(found), bool(err), dt,
        )
        if dt > PER_SUPPLIER_TIMEOUT_S:
            logger.warning("  verify lento: %.1fs > soft cap %.0fs", dt, PER_SUPPLIER_TIMEOUT_S)

        results[s.key] = {
            "supplier_key": s.key,
            "supplier_name": name,
            "status": status,
            "pdf_count": len(found),
            "pdfs": pdfs_rel,
            "extracted": extracted,
            "warning": None,
            "error": err,
        }

    workflow_svc._db_upsert_statement(statement_id, verify_results=results)
    logger.info(
        "verify done: statement_id=%s, %d fornitori, %.1fs totali",
        statement_id, len(results), time.time() - t0_all,
    )
    return results


def get_verify_results(statement_id: str) -> dict[str, dict[str, Any]]:
    rec = workflow_svc._db_get_statement(statement_id)
    if not rec:
        return {}
    return rec.get("verify_results") or {}


def list_rejects() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not REJECTS_DIR.exists():
        return out
    for supplier_dir in sorted(REJECTS_DIR.iterdir()):
        if not supplier_dir.is_dir():
            continue
        for pdf in sorted(supplier_dir.glob("*.pdf")):
            out.append({
                "supplier_key": supplier_dir.name,
                "filename": pdf.name,
                "path": str(pdf.relative_to(REJECTS_DIR)),
                "size_bytes": pdf.stat().st_size,
            })
    return out


def get_reject_path(relpath: str) -> Path | None:
    if ".." in relpath:
        return None
    p = (REJECTS_DIR / relpath).resolve()
    try:
        p.relative_to(REJECTS_DIR.resolve())
    except ValueError:
        return None
    if not p.exists() or not p.is_file():
        return None
    return p


def list_invoices_for_supplier(supplier_key: str) -> list[str]:
    d = INVOICES_DIR / supplier_key
    if not d.exists():
        return []
    return [p.name for p in sorted(d.glob("*.pdf"))]


def get_invoice_path(supplier_key: str, filename: str) -> Path | None:
    if ".." in supplier_key or ".." in filename:
        return None
    p = (INVOICES_DIR / supplier_key / filename).resolve()
    try:
        p.relative_to(INVOICES_DIR.resolve())
    except ValueError:
        return None
    if not p.exists() or not p.is_file():
        return None
    return p
