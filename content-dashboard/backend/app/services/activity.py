"""Log attività basilare (FR-X-04)."""
from sqlalchemy.orm import Session

from ..models import ActivityLog, User


def log_activity(db: Session, user: User | None, entity: str, entity_id: int | None, action: str):
    db.add(ActivityLog(
        user_id=user.id if user else None,
        entity=entity,
        entity_id=entity_id,
        action=action[:500],
    ))
