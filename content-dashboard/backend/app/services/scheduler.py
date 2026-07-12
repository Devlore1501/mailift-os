"""Scheduler in-process per il job Idea Engine (FR-M3-02, default giornaliero).

Thread daemon che controlla ogni 15 minuti se è passato l'intervallo configurato
dall'ultimo run. Sopravvive ai riavvii senza stato esterno: l'ultimo run è
persistito nella tabella settings (chiave interna `_idea_job_last_run`).
"""
import logging
import threading
import time
from datetime import datetime, timezone

from ..db import SessionLocal
from ..models import Setting
from .idea_engine import run_job
from .kpi import get_settings_map

log = logging.getLogger("scheduler")
CHECK_EVERY_SECONDS = 15 * 60
_LAST_RUN_KEY = "_idea_job_last_run"


def _tick():
    db = SessionLocal()
    try:
        settings = get_settings_map(db)
        if settings.get("idea_job_enabled", "true") != "true":
            return
        interval_h = float(settings.get("idea_job_interval_hours", "24"))
        last_run_row = db.get(Setting, _LAST_RUN_KEY)
        now = datetime.now(timezone.utc)
        if last_run_row:
            last = datetime.fromisoformat(last_run_row.value)
            if (now - last).total_seconds() < interval_h * 3600:
                return
        log.info("scheduler: avvio job Idea Engine")
        result = run_job(db)
        log.info("scheduler: job completato %s", result)
        if last_run_row:
            last_run_row.value = now.isoformat()
        else:
            db.add(Setting(key=_LAST_RUN_KEY, value=now.isoformat()))
        db.commit()
    except Exception:  # noqa: BLE001
        log.exception("scheduler: job Idea Engine fallito")
    finally:
        db.close()


def _loop(stop_event: threading.Event):
    # primo check dopo 60s dall'avvio, poi ogni CHECK_EVERY_SECONDS
    if stop_event.wait(60):
        return
    while not stop_event.is_set():
        _tick()
        if stop_event.wait(CHECK_EVERY_SECONDS):
            return


def start_scheduler() -> threading.Event:
    stop_event = threading.Event()
    thread = threading.Thread(target=_loop, args=(stop_event,), daemon=True, name="idea-engine-scheduler")
    thread.start()
    return stop_event
