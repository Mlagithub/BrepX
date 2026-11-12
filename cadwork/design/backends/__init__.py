"""Execution backends: turn a compiled plan node into real geometry."""

from __future__ import annotations

from .base import BackendError, BackendTimeout, ExecutionBackend, NodeResult
from .local import LocalBackend

__all__ = [
    "BackendError",
    "BackendTimeout",
    "ExecutionBackend",
    "LocalBackend",
    "NodeResult",
    "ScriptBackend",
]


def __getattr__(name: str):
    # Imported lazily: the script backend pulls in the MCP client, and
    # ``cadwork.service.smlibpy_client`` imports this package for its errors.
    if name == "ScriptBackend":
        from .script import ScriptBackend

        return ScriptBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
