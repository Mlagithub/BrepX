"""Short-lived background jobs for UI-triggered plan runs.

MCP and tests keep the synchronous call. The browser needs a handle it can poll
and cancel; the job owns one cancel event and one node, never a queue.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .service import CADService, ServiceError


@dataclass
class PlanJob:
    job_id: str
    document_id: str
    node_id: str
    status: str = "queued"
    started: float | None = None
    finished: float | None = None
    error: str | None = None
    result: dict[str, Any] | None = None
    cancel: threading.Event = field(default_factory=threading.Event)
    cancel_requested: bool = False

    def to_json(self) -> dict[str, Any]:
        elapsed = None
        if self.started is not None:
            elapsed = (self.finished if self.finished is not None else time.time()) - self.started
        return {
            "job_id": self.job_id,
            "document_id": self.document_id,
            "node_id": self.node_id,
            "status": self.status,
            "elapsed_ms": None if elapsed is None else int(elapsed * 1000),
            "cancel_requested": self.cancel_requested,
            "error": self.error,
            "result": self.result,
        }


class PlanJobRegistry:
    def __init__(self, service: CADService) -> None:
        self._service = service
        self._jobs: dict[str, PlanJob] = {}
        self._lock = threading.Lock()

    def start(self, document_id: str, node_id: str,
              base_version: int | None = None,
              executor: str | None = None) -> PlanJob:
        job = PlanJob(job_id=f"job_{uuid.uuid4().hex[:10]}", document_id=document_id,
                      node_id=node_id)
        with self._lock:
            self._jobs[job.job_id] = job
        thread = threading.Thread(target=self._run, args=(job, base_version, executor),
                                  name=f"plan-{job.job_id}", daemon=True)
        thread.start()
        return job

    def get(self, job_id: str) -> PlanJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> PlanJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.cancel_requested = True
            job.cancel.set()
            if job.status == "queued":
                job.status = "cancelled"
                job.finished = time.time()
            elif job.status == "running":
                job.status = "cancelling"
            return job

    def _run(self, job: PlanJob, base_version: int | None,
             executor: str | None) -> None:
        if job.cancel.is_set():
            job.status = "cancelled"
            job.finished = time.time()
            return
        job.status = "running"
        job.started = time.time()
        try:
            result = self._service.plan_run(
                job.document_id, job.node_id, base_version=base_version,
                executor=executor, cancel_event=job.cancel,
            )
            job.result = result
            job.status = "done"
        except ServiceError as exc:
            if exc.code == "CANCELLED":
                job.status = "cancelled"
            else:
                job.status = "failed"
                job.error = f"{exc.code}: {exc.message}"
        except Exception as exc:
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
        finally:
            job.finished = time.time()
