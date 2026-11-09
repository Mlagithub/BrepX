"""SMLib geometric kernel symbols export and exception translation."""

from __future__ import annotations

from typing import Any, Callable

import smlibpy
from smlibpy import (
    Box,
    Cone,
    Cylinder,
    Helix,
    Hole,
    Part,
    Sphere,
    Torus,
    Wedge,
    X,
    Y,
    Z,
)
from backend.core.errors import DomainError


class KernelError(DomainError):
    def __init__(self, origin: str, message: str) -> None:
        super().__init__(f"Geometric kernel error [{origin}]: {message}")
        self.origin = origin
        self.raw_message = message

    def to_diagnostic(self) -> dict[str, Any]:
        diag = super().to_diagnostic()
        diag["origin"] = self.origin
        diag["raw_message"] = self.raw_message
        return diag


def call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return fn(*args, **kwargs)
    except DomainError:
        raise
    except Exception as exc:
        raise KernelError(type(exc).__name__, str(exc)) from exc


__all__ = [
    "Box",
    "Cylinder",
    "Sphere",
    "Cone",
    "Torus",
    "Wedge",
    "Helix",
    "Hole",
    "Part",
    "X",
    "Y",
    "Z",
    "KernelError",
    "call",
]
