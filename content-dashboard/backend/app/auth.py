"""Auth email+password (FR-X-01) e permessi per ruolo applicati a livello API (NFR-04)."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as OrmSession

from .db import get_db
from .models import Session, User
from .settings import SESSION_TTL_DAYS

_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS)
    return f"pbkdf2${_PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, AttributeError):
        return False


def create_session(db: OrmSession, user: User) -> str:
    token = secrets.token_hex(32)
    db.add(Session(
        token=token,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=SESSION_TTL_DAYS),
    ))
    db.commit()
    return token


def get_current_user(request: Request, db: OrmSession = Depends(get_db)) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token mancante")
    token = auth.removeprefix("Bearer ").strip()
    session = db.get(Session, token)
    if not session:
        raise HTTPException(status_code=401, detail="Sessione non valida")
    expires = session.expires_at
    if expires.tzinfo is not None:
        expires = expires.astimezone(timezone.utc).replace(tzinfo=None)
    if expires < datetime.now(timezone.utc).replace(tzinfo=None):
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Sessione scaduta")
    user = db.get(User, session.user_id)
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="Utente disattivato")
    return user


def require_role(*roles: str):
    """Dependency: consente solo i ruoli indicati. Admin passa sempre."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role == "admin" or user.role in roles:
            return user
        raise HTTPException(status_code=403, detail="Permesso negato per il tuo ruolo")
    return checker


# Alias leggibili per i router
any_user = get_current_user
editor_or_admin = require_role("editor")
admin_only = require_role()
