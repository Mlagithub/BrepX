"""Feature registry: generated kernel actions plus a few adapters.

A feature is a pure function: resolved inputs + params -> output value.
``kernel_actions`` generates a ``FeatureSpec`` per bindable kernel call and
``adapters`` adds the few operations the kernel expresses as Python operators
or document metadata.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from cadwork import smlib as S

from .checks import CheckResult


class FeatureError(Exception):
    def __init__(self, code: str, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint


@dataclass(frozen=True)
class Param:
    """A JSON-serialisable parameter.

    ``kind`` selects the coercion rule.  ``required`` marks a kernel argument
    that has no default (the caller must supply it); required params never fall
    back to ``default``.
    """

    kind: str
    default: Any = None
    minimum: float | None = None
    maximum: float | None = None
    unit: str | None = None
    choices: tuple[str, ...] | None = None
    description: str = ""
    required: bool = False

    def coerce(self, name: str, value: Any) -> Any:
        if value is None:
            if self.required:
                raise FeatureError("INVALID_PARAM", f"{name} is required")
            return None
        if self.kind == "bool":
            if not isinstance(value, bool):
                raise FeatureError("INVALID_PARAM", f"{name} must be a boolean")
            return value
        if self.kind == "int":
            if isinstance(value, bool):
                raise FeatureError("INVALID_PARAM", f"{name} must be an integer")
            if isinstance(value, float) and value.is_integer():
                return int(value)
            if not isinstance(value, int):
                raise FeatureError("INVALID_PARAM", f"{name} must be an integer")
            result: Any = value
        elif self.kind == "float":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise FeatureError("INVALID_PARAM", f"{name} must be a number")
            result = float(value)
            if not math.isfinite(result):
                raise FeatureError("INVALID_PARAM", f"{name} must be finite")
        elif self.kind in {"str", "enum"}:
            if not isinstance(value, str):
                raise FeatureError("INVALID_PARAM", f"{name} must be a string")
            if self.choices and value not in self.choices:
                raise FeatureError(
                    "INVALID_PARAM",
                    f"{name} must be one of {', '.join(self.choices)}, got {value!r}",
                )
            return value
        elif self.kind == "vector":
            if not isinstance(value, (list, tuple)) or len(value) != 3:
                raise FeatureError("INVALID_PARAM", f"{name} must be a 3-vector")
            return _numbers(name, list(value))
        elif self.kind == "points":
            if not isinstance(value, (list, tuple)) or not value:
                raise FeatureError(
                    "INVALID_PARAM", f"{name} must be a non-empty point list"
                )
            points: list[list[float]] = []
            for index, point in enumerate(value):
                if not isinstance(point, (list, tuple)) or len(point) not in (2, 3):
                    raise FeatureError(
                        "INVALID_PARAM", f"{name}[{index}] must be a 2D or 3D point"
                    )
                points.append(_numbers(f"{name}[{index}]", list(point)))
            return points
        else:
            raise FeatureError(
                "INVALID_PARAM", f"{name} has an unknown kind {self.kind!r}"
            )

        if self.kind in {"float", "int"}:
            if self.minimum is not None and result < self.minimum:
                raise FeatureError("INVALID_PARAM", f"{name} must be >= {self.minimum}")
            if self.maximum is not None and result > self.maximum:
                raise FeatureError("INVALID_PARAM", f"{name} must be <= {self.maximum}")
        return result


def _numbers(name: str, values: list[Any]) -> list[float]:
    out: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise FeatureError("INVALID_PARAM", f"{name} must contain only numbers")
        number = float(value)
        if not math.isfinite(number):
            raise FeatureError("INVALID_PARAM", f"{name} must contain finite numbers")
        out.append(number)
    return out


@dataclass(frozen=True)
class FeatureOutput:
    value: Any
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InputKind:
    """One way a reference resolves: the selectors it accepts and the kernel
    types it may produce."""

    selects: tuple[str, ...]
    accepts: tuple[type, ...] = ()


INPUT_KINDS: dict[str, InputKind] = {
    "part": InputKind(("self",), (S.Part, S.ShapeList)),
    "shell": InputKind(("self",), (S.Shell,)),
    "profile": InputKind(("self",), (S.Sketch,)),
    "curve": InputKind(("self",), (S.Edge, S.Wire)),
    "faces": InputKind(("faces",), (S.ShapeList, S.Face)),
    "edges": InputKind(("edges",), (S.ShapeList, S.Edge)),
    "face": InputKind(("faces",), (S.Face,)),
    "shape_list": InputKind(("self",), (S.ShapeList,)),
    "shape": InputKind(("self",), (S.Part, S.Shell, S.Sketch, S.Edge, S.Wire)),
}


def register_input_kind(
    name: str, selects: tuple[str, ...], accepts: tuple[type, ...] = ()
) -> None:
    """Extend the reference vocabulary without touching the build engine."""
    if not name or name in INPUT_KINDS:
        raise FeatureError("INVALID_KIND", f"input kind {name!r} already exists")
    INPUT_KINDS[name] = InputKind(tuple(selects), tuple(accepts))


@dataclass(frozen=True)
class InputRole:
    role: str
    kind: str
    many: bool = False
    optional: bool = False


@dataclass(frozen=True)
class FeatureSpec:
    type: str
    summary: str
    inputs: tuple[InputRole, ...]
    params: dict[str, Param]
    build: Callable[[dict[str, Any], dict[str, Any]], FeatureOutput]
    check: Callable[[Any, dict[str, Any], dict[str, Any]], list[CheckResult]]
    tier: str = "kernel"
    origin: str = ""
    return_kind: str = "part"


FEATURES: dict[str, FeatureSpec] = {}
_REGISTRY_LOADED = False
_REGISTRY_ERROR: Exception | None = None


def _load_registry() -> None:
    global _REGISTRY_LOADED, _REGISTRY_ERROR
    if _REGISTRY_LOADED:
        return
    _REGISTRY_LOADED = True
    try:
        from .adapters import ADAPTERS
        from .kernel_actions import generated_actions

        for spec in generated_actions():
            FEATURES.setdefault(spec.type, spec)
        for spec in ADAPTERS:
            FEATURES[spec.type] = spec
    except Exception as exc:
        _REGISTRY_ERROR = exc
        FEATURES.clear()


def all_specs() -> dict[str, FeatureSpec]:
    _load_registry()
    if not FEATURES and _REGISTRY_ERROR is not None:
        raise FeatureError(
            "REGISTRY_FAILED",
            f"the kernel action registry could not be built: {_REGISTRY_ERROR}",
        )
    return FEATURES


def spec_for(feature_type: str) -> FeatureSpec | None:
    return all_specs().get(feature_type)


def resolve_params(spec: FeatureSpec, provided: Mapping[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(provided) - set(spec.params))
    if unknown:
        raise FeatureError(
            "UNKNOWN_PARAM",
            f"{spec.type} has no parameter {', '.join(unknown)}",
            hint=f"known parameters: {', '.join(sorted(spec.params))}",
        )
    result: dict[str, Any] = {}
    for name, param in spec.params.items():
        if name in provided:
            value = provided[name]
        elif param.required:
            raise FeatureError(
                "INVALID_PARAM",
                f"{spec.type} requires {name}",
                hint=f"required parameters: {', '.join(sorted(k for k, p in spec.params.items() if p.required))}",
            )
        else:
            value = param.default
        result[name] = param.coerce(name, value)
    return result


def validate_feature(feature_type: str, refs: Mapping[str, Any]) -> FeatureSpec:
    spec = spec_for(feature_type)
    if spec is None:
        raise FeatureError(
            "UNKNOWN_FEATURE_TYPE",
            f"unknown feature type {feature_type!r}",
            hint=f"available: {', '.join(sorted(all_specs()))}",
        )
    roles = {role.role: role for role in spec.inputs}
    optional = {name for name, role in roles.items() if role.optional}
    missing = sorted(set(roles) - optional - set(refs))
    extra = sorted(set(refs) - set(roles))
    if missing or extra:
        raise FeatureError(
            "INVALID_REFS",
            f"{feature_type} refs: missing {missing}, unexpected {extra}",
            hint=f"required roles: {', '.join(sorted(set(roles) - optional)) or '(none)'}"
            + (f"; optional: {', '.join(sorted(optional))}" if optional else ""),
        )
    return spec


def catalog() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for spec in sorted(all_specs().values(), key=lambda item: item.type):
        entries.append(
            {
                "type": spec.type,
                "summary": spec.summary,
                "tier": spec.tier,
                "origin": spec.origin,
                "return_kind": spec.return_kind,
                "inputs": [
                    {
                        "role": role.role,
                        "kind": role.kind,
                        "many": role.many,
                        "optional": role.optional,
                    }
                    for role in spec.inputs
                ],
                "params": {
                    name: {
                        "kind": param.kind,
                        "default": param.default,
                        "min": param.minimum,
                        "max": param.maximum,
                        "unit": param.unit,
                        "choices": list(param.choices) if param.choices else None,
                        "description": param.description,
                        "required": param.required,
                    }
                    for name, param in spec.params.items()
                },
            }
        )
    return entries


_load_registry()
