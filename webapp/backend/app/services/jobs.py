"""Job manager thread-safe con write-through a SQLite.

In-memory cache per velocita' di lettura frequente (polling del frontend) ma
DB come source of truth per sopravvivere al restart.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select

from app.db import session_scope
from app.models.db_models import Job as JobRow


@dataclass
class Job:
    id: str
    kind: str = "generic"
    status: str = "pending"  # pending | running | done | error
    progress: int = 0
    step_name: str = ""
    total: int = 0
    current: int = 0
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    statement_id: Optional[str] = None


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, kind: str = "generic", statement_id: str | None = None) -> Job:
        jid = uuid.uuid4().hex[:12]
        job = Job(id=jid, kind=kind, statement_id=statement_id)
        with self._lock:
            self._jobs[jid] = job
        self._persist(job)
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is not None:
            return job
        # fallback DB (post-restart)
        with session_scope() as db:
            row = db.get(JobRow, job_id)
            if not row:
                return None
            job = Job(
                id=row.id,
                kind=row.kind,
                status=row.status,
                progress=row.progress,
                step_name=row.step_name,
                total=row.total,
                current=row.current,
                result=row.result,
                error=row.error,
                created_at=row.created_at.timestamp() if row.created_at else time.time(),
                statement_id=row.statement_id,
            )
        with self._lock:
            self._jobs[job_id] = job
        return job

    def update(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for k, v in fields.items():
                if hasattr(job, k):
                    setattr(job, k, v)
        self._persist(job)

    def _persist(self, job: Job) -> None:
        try:
            with session_scope() as db:
                row = db.get(JobRow, job.id)
                if row is None:
                    row = JobRow(
                        id=job.id,
                        kind=job.kind,
                        created_at=datetime.utcfromtimestamp(job.created_at),
                        statement_id=job.statement_id,
                    )
                    db.add(row)
                row.kind = job.kind
                row.status = job.status
                row.progress = job.progress
                row.step_name = job.step_name
                row.total = job.total
                row.current = job.current
                row.result = job.result
                row.error = job.error
                row.statement_id = job.statement_id
                row.updated_at = datetime.utcnow()
        except Exception as e:
            # DB down non deve bloccare il job flow
            print(f"[JobManager] persist warning for {job.id}: {e}")


jobs = JobManager()
