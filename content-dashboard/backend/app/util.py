"""Utility condivise."""
from datetime import datetime, timezone


def naive_utc(dt: datetime | None) -> datetime | None:
    """Normalizza qualunque datetime (aware o naive) a UTC naive.

    Il DB memorizza tutto in UTC naive (SQLite scarta il tz): ogni datetime
    che entra dall'API va passato di qui prima di filtrare o salvare.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
