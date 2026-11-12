"""Shared types for execution backends.

A backend turns one compiled plan node into a real modelling-kernel operation
and reports the resulting measurements.  The service layer decides what to do
with a failure; a backend only raises a typed error.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable


class BackendError(RuntimeError):
    """A backend could not execute a node.

    ``code`` is a stable error code (``SCRIPT_FAILED`` here); ``raw`` keeps the
    kernel's own text so the service layer can show the real cause.
    """

    def __init__(self, message: str, *, code: str = "SCRIPT_FAILED", raw: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.raw = raw

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "raw": self.raw}


class BackendTimeout(BackendError):
    """The node did not finish in time (``SCRIPT_TIMEOUT``)."""

    def __init__(self, message: str = "the script did not finish in time", *, raw: str | None = None) -> None:
        super().__init__(message, code="SCRIPT_TIMEOUT", raw=raw)


@dataclass
class NodeResult:
    """What one successful node left behind.

    ``metrics`` is the JSON object the generated script printed (volume, faces,
    bbox, ...); ``step_path`` is the optional exported STEP file; ``raw`` is the
    complete tool answer, kept for diagnostics only.  ``value`` is the live
    kernel object for in-process backends and is ``None`` for script backends.
    """

    metrics: dict[str, Any]
    step_path: str | None = None
    raw: str | None = None
    value: Any = None


@runtime_checkable
class ExecutionBackend(Protocol):
    """The interface the service layer programs against.

    The signature carries the document id because one backend keeps one kernel
    session per document; ``prior_vars`` is the planner's view of the session
    variables and is passed for local backends that execute in-process.
    """

    name: str

    def build_node(
        self,
        document_id: str,
        step: Any,
        prior_vars: Mapping[str, Any],
        step_path: str | None = None,
    ) -> NodeResult: ...

    def reset(self, document_id: str) -> None: ...

    def close(self) -> None: ...


__all__ = [
    "BackendError",
    "BackendTimeout",
    "ExecutionBackend",
    "NodeResult",
]
