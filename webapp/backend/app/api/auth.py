"""Login / logout / stato sessione."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app import auth, settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/me")
def me(request: Request) -> dict:
    if not auth.enabled():
        return {"authenticated": True, "auth_enabled": False}
    return {
        "authenticated": auth.token_valid(request.cookies.get(auth.COOKIE_NAME)),
        "auth_enabled": True,
    }


@router.post("/login")
def login(req: LoginRequest, request: Request, response: Response) -> dict:
    if not auth.enabled():
        return {"authenticated": True}
    ip = _client_ip(request)
    if auth.locked_out(ip):
        raise HTTPException(429, "Troppi tentativi. Riprova tra 15 minuti.")
    if not auth.check_password(ip, req.password):
        raise HTTPException(401, "Password errata")
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.issue_token(),
        max_age=settings.SESSION_HOURS * 3600,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="strict",
    )
    return {"authenticated": True}


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(auth.COOKIE_NAME)
    return {"authenticated": False}
