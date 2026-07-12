from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from ..auth import admin_only, hash_password
from ..db import get_db
from ..enums import ROLES
from ..models import User
from ..schemas import UserCreate, UserOut, UserUpdate
from ..services.activity import log_activity

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(user: User = Depends(admin_only), db: OrmSession = Depends(get_db)):
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, user: User = Depends(admin_only), db: OrmSession = Depends(get_db)):
    if body.role not in ROLES:
        raise HTTPException(status_code=422, detail=f"Ruolo non valido, usa uno di {ROLES}")
    email = body.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email già registrata")
    new_user = User(name=body.name, email=email, role=body.role,
                    password_hash=hash_password(body.password))
    db.add(new_user)
    log_activity(db, user, "user", None, f"creato utente {email} ({body.role})")
    db.commit()
    db.refresh(new_user)
    return new_user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, user: User = Depends(admin_only),
                db: OrmSession = Depends(get_db)):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    if body.role is not None:
        if body.role not in ROLES:
            raise HTTPException(status_code=422, detail=f"Ruolo non valido, usa uno di {ROLES}")
        target.role = body.role
    if body.name is not None:
        target.name = body.name
    if body.active is not None:
        if target.id == user.id and not body.active:
            raise HTTPException(status_code=422, detail="Non puoi disattivare il tuo stesso account")
        target.active = body.active
    if body.password:
        target.password_hash = hash_password(body.password)
    log_activity(db, user, "user", target.id, "aggiornato utente")
    db.commit()
    db.refresh(target)
    return target
