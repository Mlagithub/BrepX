"""Topological selector resolution error definitions for BrepX."""

from __future__ import annotations

from typing import Any
from backend.core.errors import DomainError

VALID_REASONS = {"no_match", "ambiguous", "bad_syntax", "unsupported"}


class SelectorResolutionError(DomainError):
    def __init__(
        self,
        expr: str,
        base_version: str | int,
        candidates: list[str] | None = None,
        reason: str = "no_match",
    ) -> None:
        if reason not in VALID_REASONS:
            raise ValueError(
                f"Invalid selector resolution failure reason '{reason}'. Allowed reasons: {sorted(VALID_REASONS)}"
            )

        message = (
            f"Failed to resolve selector expression '{expr}' against base geometry version {base_version}: {reason}."
        )
        if candidates:
            message += f" Available candidates: {', '.join(candidates)}"
        super().__init__(message)

        self.expr = expr
        self.base_version = str(base_version)
        self.candidates = candidates or []
        self.reason = reason

    def to_diagnostic(self) -> dict[str, Any]:
        diag = super().to_diagnostic()
        diag["expr"] = self.expr
        diag["base_version"] = self.base_version
        diag["candidates"] = self.candidates
        diag["reason"] = self.reason
        return diag
