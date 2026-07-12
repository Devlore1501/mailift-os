"""Seed idempotente eseguito all'avvio: admin di default, target pillar, soglie."""
import logging
import os

from sqlalchemy.orm import Session

from .auth import hash_password
from .enums import DEFAULT_PILLAR_TARGETS, DEFAULT_SETTINGS
from .models import PillarTarget, Setting, Source, User
from .source_catalog import CATALOG

log = logging.getLogger("seed")

DEFAULT_ADMIN_EMAIL = "lorenzo@mailift.it"


def run_seed(db: Session):
    if not db.query(User).first():
        password = os.environ.get("CONTENT_DASHBOARD_ADMIN_PASSWORD", "mailift-admin")
        db.add(User(
            name="Lorenzo",
            email=DEFAULT_ADMIN_EMAIL,
            role="admin",
            password_hash=hash_password(password),
        ))
        log.warning(
            "Creato admin di default %s (password da env CONTENT_DASHBOARD_ADMIN_PASSWORD, "
            "default 'mailift-admin' — cambiarla subito da Impostazioni → Utenti)",
            DEFAULT_ADMIN_EMAIL,
        )
    for pillar, pct in DEFAULT_PILLAR_TARGETS.items():
        if not db.get(PillarTarget, pillar):
            db.add(PillarTarget(pillar=pillar, target_pct=float(pct)))
    for key, value in DEFAULT_SETTINGS.items():
        if not db.get(Setting, key):
            db.add(Setting(key=key, value=value))
    # primo avvio: fonti consigliate pronte, così l'Idea Engine parte subito
    if not db.query(Source).first():
        for entry in CATALOG:
            db.add(Source(type=entry["type"], url=entry["url"], label=entry["label"], active=True))
        log.info("Seed: aggiunte %d fonti consigliate dal catalogo", len(CATALOG))
    db.commit()
