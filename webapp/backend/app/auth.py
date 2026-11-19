"""Login a utente singolo con cookie di sessione firmato (HMAC, solo stdlib).

L'app e' di una persona sola: una password in WEBAPP_PASSWORD basta, a patto
che il confronto sia a tempo costante, il cookie sia HttpOnly/SameSite e i
tentativi falliti vengano rallentati.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import threading
import time

from app import settings

COOKIE_NAME = "autofatture_session"
_MAX_FAILURES = 5
_WINDOW_S = 15 * 60

_failures: dict[str, list[float]] = {}
_lock = threading.Lock()


def enabled() -> bool:
    return bool(settings.PASSWORD)


def _sign(payload: str) -> str:
    return hmac.new(settings.SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def issue_token() -> str:
    exp = int(time.time()) + settings.SESSION_HOURS * 3600
    payload = base64.urlsafe_b64encode(str(exp).encode()).decode()
    return f"{payload}.{_sign(payload)}"


def token_valid(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    payload, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(sig, _sign(payload)):
        return False
    try:
        exp = int(base64.urlsafe_b64decode(payload.encode()).decode())
    except (ValueError, UnicodeDecodeError):
        return False
    return exp > time.time()


def locked_out(client_ip: str) -> bool:
    now = time.time()
    with _lock:
        recent = [t for t in _failures.get(client_ip, []) if now - t < _WINDOW_S]
        _failures[client_ip] = recent
        return len(recent) >= _MAX_FAILURES


def check_password(client_ip: str, password: str) -> bool:
    ok = hmac.compare_digest(password.encode(), settings.PASSWORD.encode())
    if not ok:
        with _lock:
            _failures.setdefault(client_ip, []).append(time.time())
    return ok
