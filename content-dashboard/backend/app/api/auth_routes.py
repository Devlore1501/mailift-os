from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as OrmSession

from ..auth import any_user, create_session, verify_password
from ..db import get_db
from ..models import Session, User
from ..schemas import LoginIn, LoginOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, db: OrmSession = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not user.active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    return LoginOut(token=create_session(db, user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(any_user)):
    return user


@router.post("/logout")
def logout(request: Request, user: User = Depends(any_user), db: OrmSession = Depends(get_db)):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    session = db.get(Session, token)
    if session:
        db.delete(session)
        db.commit()
    return {"ok": True}
