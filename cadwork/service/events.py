"""Domain event log and the derived timeline.

dsh already owns the agent-side session log (tool calls, messages, startup
errors).  This module only records what dsh cannot see: what the CAD service did
inside a document, correlated by ``request_id``.  It deliberately stores ids,
counts, durations and error codes, never geometry payloads or secrets.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_MAX_BYTES = 8 * 1024 * 1024


def new_request_id() -> str:
    return f"r_{uuid.uuid4().hex[:12]}"


@dataclass
class DomainEvent:
    event: str
    request_id: str = ""
    document_id: str = ""
    plan_id: str = ""
    node_id: str = ""
    actor: str = ""
    tool: str = ""
    backend: str = ""
    duration_ms: int | None = None
    cache_hit: bool | None = None
    code: str = ""
    hint: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ts"] = round(time.time(), 6)
        payload["detail"] = dict(self.detail)
        return payload


class EventLog:
    """A tiny rotating JSONL writer; failures must never break a CAD request."""

    def __init__(
        self, path: str | os.PathLike[str], max_bytes: int = _MAX_BYTES
    ) -> None:
        self.path = Path(path)
        self.max_bytes = max_bytes
        self._lock = threading.Lock()

    def write(self, event: DomainEvent) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                self._rotate()
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(event.to_json(), ensure_ascii=False) + "\n")
        except OSError:
            # Observability must not turn into an outage.
            pass

    def _rotate(self) -> None:
        try:
            if self.path.exists() and self.path.stat().st_size >= self.max_bytes:
                backup = self.path.with_suffix(self.path.suffix + ".1")
                if backup.exists():
                    backup.unlink()
                os.replace(self.path, backup)
        except OSError:
            pass

    def read(self, limit: int = 200) -> list[dict[str, Any]]:
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
        except OSError:
            return []
        out: list[dict[str, Any]] = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out


def timeline(document: Any, plan: Any | None = None) -> list[dict[str, Any]]:
    """Derive a human-readable audit trail from milestones and plan nodes.

    This is not a log file: it is a projection of the document and the plan,
    so it survives restarts, reverts and exports without another source of truth.
    """
    entries: list[dict[str, Any]] = []
    feature_map = {feature.id: feature for feature in getattr(document, "features", ())}
    for milestone in getattr(document, "milestones", ()):
        metrics = dict(getattr(milestone, "metrics", ()))
        entries.append(
            {
                "version": milestone.version,
                "at": milestone.created,
                "actor": milestone.actor,
                "title": milestone.title,
                "plan_id": getattr(milestone, "plan_id", None),
                "node_id": getattr(milestone, "node_id", None),
                "changed": list(getattr(milestone, "changed_features", ())),
                "features": [
                    {"id": fid, "type": feature_map[fid].type}
                    for fid in getattr(milestone, "changed_features", ())
                    if fid in feature_map
                ],
                "checks": {
                    "passed": metrics.get("checks_passed", 0),
                    "total": metrics.get("checks_total", 0),
                },
                "metrics": {
                    key: value
                    for key, value in metrics.items()
                    if key
                    in {
                        "faces",
                        "volume",
                        "edges",
                        "seconds",
                        "backend",
                        "duration_ms",
                        "cache_hits",
                    }
                },
            }
        )
    if plan is not None:
        for node in getattr(plan, "nodes", ()):
            entries.append(
                {
                    "version": getattr(node, "milestone_version", None),
                    "at": None,
                    "actor": "agent",
                    "title": f"{node.kind}: {node.title}",
                    "plan_id": getattr(plan, "id", None),
                    "node_id": node.id,
                    "changed": [],
                    "features": [],
                    "checks": {},
                    "metrics": {"node_status": node.status},
                    "error": getattr(node, "error", None),
                }
            )
    entries.sort(
        key=lambda item: (
            item["version"] if item["version"] is not None else -1,
            item["at"] or 0.0,
        )
    )
    return entries


def emit(log: EventLog | None, event: str, **fields: Any) -> None:
    if log is None:
        return
    log.write(DomainEvent(event=event, **fields))
