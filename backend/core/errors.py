"""Domain error definitions for BrepX command and modeling pipeline."""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def to_diagnostic(self) -> dict[str, Any]:
        return {
            "error": type(self).__name__,
            "message": self.message,
        }


class OperatorNotFoundError(DomainError):
    def __init__(self, op: str, closest: list[str]) -> None:
        message = f"Operator '{op}' is not registered."
        if closest:
            message += f" Did you mean: {', '.join(closest)}?"
        super().__init__(message)
        self.op = op
        self.closest = closest

    def to_diagnostic(self) -> dict[str, Any]:
        diag = super().to_diagnostic()
        diag["op"] = self.op
        diag["closest"] = self.closest
        return diag


class ParamTypeError(DomainError):
    def __init__(self, param: str, value: Any, expected_kind: str) -> None:
        message = f"Parameter '{param}' expected kind '{expected_kind}', got value {value!r} of type {type(value).__name__}."
        super().__init__(message)
        self.param = param
        self.value = value
        self.expected_kind = expected_kind

    def to_diagnostic(self) -> dict[str, Any]:
        diag = super().to_diagnostic()
        diag["param"] = self.param
        diag["value"] = self.value
        diag["expected_kind"] = self.expected_kind
        return diag


class ParamRangeError(DomainError):
    def __init__(self, param: str, value: Any, allowed: str) -> None:
        message = f"Parameter '{param}' value {value!r} is out of allowed range ({allowed})."
        super().__init__(message)
        self.param = param
        self.value = value
        self.allowed = allowed

    def to_diagnostic(self) -> dict[str, Any]:
        diag = super().to_diagnostic()
        diag["param"] = self.param
        diag["value"] = self.value
        diag["allowed"] = self.allowed
        return diag


class PreconditionError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Precondition failed: {reason}")
        self.reason = reason

    def to_diagnostic(self) -> dict[str, Any]:
        diag = super().to_diagnostic()
        diag["reason"] = self.reason
        return diag


class PostconditionError(DomainError):
    def __init__(
        self,
        assertion_name: str,
        actual: Any,
        expected: Any,
        suggestion: str = "",
    ) -> None:
        message = f"Postcondition '{assertion_name}' failed: expected {expected!r}, observed {actual!r}."
        if suggestion:
            message += f" Suggestion: {suggestion}"
        super().__init__(message)
        self.assertion_name = assertion_name
        self.actual = actual
        self.expected = expected
        self.suggestion = suggestion

    def to_diagnostic(self) -> dict[str, Any]:
        diag = super().to_diagnostic()
        diag["assertion_name"] = self.assertion_name
        diag["actual"] = self.actual
        diag["expected"] = self.expected
        diag["suggestion"] = self.suggestion
        return diag
