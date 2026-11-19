"""Pianificatore minimo: un giro dell'archivio ogni notte alle 03:00 (Europe/Rome).

Attivo solo con ARCHIVE_ENABLED=true. Gira nel processo della webapp, quindi
funziona finche' Railway tiene il servizio acceso.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta

from app.services import archive

log = logging.getLogger("app.scheduler")
RUN_HOUR = int(os.getenv("ARCHIVE_HOUR", "3"))


def enabled() -> bool:
    return os.getenv("ARCHIVE_ENABLED", "false").lower() in {"1", "true", "yes"}


def seconds_until_next_run(now: datetime | None = None) -> float:
    now = now or datetime.now(archive.TZ)
    nxt = now.replace(hour=RUN_HOUR, minute=0, second=0, microsecond=0)
    if nxt <= now:
        nxt += timedelta(days=1)
    return (nxt - now).total_seconds()


async def nightly_loop() -> None:
    while True:
        wait = seconds_until_next_run()
        log.info("prossimo archivio tra %.0f minuti", wait / 60)
        await asyncio.sleep(wait)
        try:
            # 3 giorni di margine: un giro saltato non perde email
            stats = await asyncio.to_thread(archive.run_archive, None, 3, "nightly")
            log.info("archivio notturno concluso: %s", {a: s["uploaded"] for a, s in stats["accounts"].items()})
        except Exception:
            log.exception("archivio notturno fallito")
