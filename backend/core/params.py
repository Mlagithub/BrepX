"""Parameter specification and validation rules for BrepX operators."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from backend.core.errors import ParamRangeError, ParamTypeError


class ParamKind(Enum):
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    ENUM = "enum"

    @property
    def python_types(self) -> tuple[type, ...]:
        if self == ParamKind.INT:
            return (int,)
        if self == ParamKind.FLOAT:
            return (float, int)
        if self == ParamKind.BOOL:
            return (bool,)
        if self == ParamKind.ENUM:
            return (str,)
        return ()


@dataclass(frozen=True)
class ParamSpec:
    kind: ParamKind
    default: Any | None = None
    min: float | int | None = None
    max: float | int | None = None
    choices: tuple[str, ...] | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        if self.choices is not None and self.kind != ParamKind.ENUM:
            raise ValueError(f"Choices can only be provided for ENUM parameters, got {self.kind}")


def validate_value(spec: ParamSpec, value: Any) -> Any:
    if value is None:
        if spec.default is None:
            raise ParamRangeError("value", None, "Required parameter missing")
        return spec.default

    if spec.kind == ParamKind.BOOL:
        if not isinstance(value, bool):
            raise ParamTypeError("value", value, spec.kind.value)
        return value

    if spec.kind == ParamKind.INT:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ParamTypeError("value", value, spec.kind.value)
    elif spec.kind == ParamKind.FLOAT:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ParamTypeError("value", value, spec.kind.value)
        value = float(value)
    elif spec.kind == ParamKind.ENUM:
        if not isinstance(value, str):
            raise ParamTypeError("value", value, spec.kind.value)

    if spec.min is not None and value < spec.min:
        allowed = f"{spec.min}..{spec.max if spec.max is not None else ''}"
        raise ParamRangeError("value", value, allowed)

    if spec.max is not None and value > spec.max:
        allowed = f"{spec.min if spec.min is not None else ''}..{spec.max}"
        raise ParamRangeError("value", value, allowed)

    if spec.kind == ParamKind.ENUM and spec.choices is not None:
        if value not in spec.choices:
            allowed = ", ".join(spec.choices)
            raise ParamRangeError("value", value, allowed)

    return value
