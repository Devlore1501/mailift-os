"""System endpoints: health & config."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import text

from app import settings
from app.db import engine
from app.models.schemas import ConfigResponse, HealthResponse
from app.services.workflow import make_fic_client

router = APIRouter(prefix="/api", tags=["system"])


def _check_db() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _check_gmail_tokens() -> dict[str, bool]:
    tokens_dir = settings.PROJECT_ROOT / "tokens"
    return {
        "personal": (tokens_dir / "gmail_personal.json").exists(),
        "business": (tokens_dir / "gmail_business.json").exists(),
    }


def _check_anthropic() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_ok = _check_db()
    gmail_tokens_ok = _check_gmail_tokens()
    anthropic_api_ok = _check_anthropic()

    try:
        client = make_fic_client()
        # Verifica token con una chiamata leggera
        data = client._request("GET", "/user/companies")
        companies = (data.get("data") or {}).get("companies") or []
        company = next(
            (c for c in companies if str(c.get("id")) == str(client.company_id)),
            companies[0] if companies else None,
        )
        return HealthResponse(
            status="ok",
            fic_token_valid=True,
            company={"id": client.company_id, "name": (company or {}).get("name")},
            dry_run=settings.DRY_RUN_DEFAULT,
            db_ok=db_ok,
            gmail_tokens_ok=gmail_tokens_ok,
            anthropic_api_ok=anthropic_api_ok,
        )
    except Exception as e:
        return HealthResponse(
            status="error",
            fic_token_valid=False,
            detail=str(e),
            dry_run=settings.DRY_RUN_DEFAULT,
            db_ok=db_ok,
            gmail_tokens_ok=gmail_tokens_ok,
            anthropic_api_ok=anthropic_api_ok,
        )


@router.get("/config", response_model=ConfigResponse)
def config() -> ConfigResponse:
    # Count blacklist entries (safe import senza call ad Anthropic)
    blacklist_count = 0
    try:
        import classify_transactions as _ct  # type: ignore
        blacklist_count = len(getattr(_ct, "AUTOFATTURA_BLACKLIST", []) or [])
    except Exception:
        pass

    return ConfigResponse(
        company_id=os.environ.get("FIC_COMPANY_ID", ""),
        company_name=os.environ.get("FIC_COMPANY_NAME"),
        numeration=os.environ.get("FIC_NUMERATION", "a"),
        payment_method=os.environ.get("FIC_PAYMENT_METHOD", "MP05"),
        payment_account_hint=os.environ.get("FIC_PAYMENT_ACCOUNT_NAME", "revolut"),
        dry_run=settings.DRY_RUN_DEFAULT,
        blacklist_count=blacklist_count,
    )
