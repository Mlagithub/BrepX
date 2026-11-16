"""Declarative assembly plans expand into immutable AssemblyDocument instances.

A plan is the authoring form; expansion is deterministic so the same plan always
yields the same instance ids and placements. Patterns are expanded here, never
inside the runtime assembly document.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from cadwork.design.assembly import (
    AssemblyDocument,
    AssemblyRef,
    Instance,
    PartRef,
    Transform,
    reference_from_json,
    reference_to_json,
    transform_from_json,
    transform_to_json,
)
from cadwork.design.document import DocumentError

_IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
_PLAN_FIELDS = frozenset({"id", "name", "version", "instances", "checks"})
_INSTANCE_FIELDS = frozenset(
    {
        "id",
        "ref",
        "placement",
        "overrides",
        "name",
        "suppressed",
        "visible",
        "pattern",
    }
)
_PATTERN_FIELDS = frozenset(
    {
        "kind",
        "count",
        "radius",
        "start_angle",
        "axis",
        "dx",
        "dy",
        "dz",
    }
)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise DocumentError("INVALID_ID", f"{label} must be a non-empty trimmed string")
    return value


def _rotate(axis: str, degrees: float) -> tuple[tuple[float, float, float], ...]:
    angle = math.radians(degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    if axis == "X":
        return ((1.0, 0.0, 0.0), (0.0, cosine, -sine), (0.0, sine, cosine))
    if axis == "Y":
        return ((cosine, 0.0, sine), (0.0, 1.0, 0.0), (-sine, 0.0, cosine))
    return ((cosine, -sine, 0.0), (sine, cosine, 0.0), (0.0, 0.0, 1.0))


def _matmul(
    left: tuple[tuple[float, float, float], ...],
    right: tuple[tuple[float, float, float], ...],
):
    return tuple(
        tuple(
            sum(left[row][k] * right[k][column] for k in range(3))
            for column in range(3)
        )
        for row in range(3)
    )


def _matvec(
    matrix: tuple[tuple[float, float, float], ...], vector: tuple[float, float, float]
):
    return tuple(sum(matrix[row][k] * vector[k] for k in range(3)) for row in range(3))


@dataclass(frozen=True)
class Pattern:
    """Deterministic placement rule for repeated instances."""

    kind: str
    count: int
    radius: float = 0.0
    start_angle: float = 0.0
    axis: str = "Z"
    dx: float = 0.0
    dy: float = 0.0
    dz: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in {"polar", "linear"}:
            raise DocumentError(
                "INVALID_PATTERN", f"unknown pattern kind {self.kind!r}"
            )
        if (
            isinstance(self.count, bool)
            or not isinstance(self.count, int)
            or self.count < 1
        ):
            raise DocumentError(
                "INVALID_PATTERN", "pattern count must be an integer >= 1"
            )
        if not math.isfinite(self.radius) or self.radius < 0.0:
            raise DocumentError(
                "INVALID_PATTERN", "pattern radius must be finite and >= 0"
            )
        if self.axis not in {"X", "Y", "Z"}:
            raise DocumentError(
                "INVALID_PATTERN", f"unknown pattern axis {self.axis!r}"
            )
        for value in (self.start_angle, self.dx, self.dy, self.dz):
            if not math.isfinite(value):
                raise DocumentError("INVALID_PATTERN", "pattern values must be finite")

    def placement(self, index: int) -> Transform:
        if self.kind == "linear":
            return Transform(
                translation=(self.dx * index, self.dy * index, self.dz * index)
            )
        angle = self.start_angle + 360.0 * index / self.count
        radians = math.radians(angle)
        if self.axis == "X":
            translation = (
                0.0,
                self.radius * math.cos(radians),
                self.radius * math.sin(radians),
            )
        elif self.axis == "Y":
            translation = (
                self.radius * math.cos(radians),
                0.0,
                self.radius * math.sin(radians),
            )
        else:
            translation = (
                self.radius * math.cos(radians),
                self.radius * math.sin(radians),
                0.0,
            )
        return Transform(rotation=_rotate(self.axis, angle), translation=translation)


def _compose(base: Transform, local: Transform) -> Transform:
    rotation = _matmul(base.rotation, local.rotation)
    moved = _matvec(base.rotation, local.translation)
    translation = tuple(moved[i] + base.translation[i] for i in range(3))
    return Transform(rotation=rotation, translation=translation)


@dataclass(frozen=True)
class PlanInstance:
    """One explicit instance or one patterned group in the plan."""

    id: str
    ref: PartRef | AssemblyRef
    placement: Transform = Transform()
    overrides: Mapping[str, Any] = field(default_factory=dict)
    name: str = ""
    suppressed: bool = False
    visible: bool = True
    pattern: Pattern | None = None

    def __post_init__(self) -> None:
        _text(self.id, "plan instance id")
        if not isinstance(self.ref, (PartRef, AssemblyRef)):
            raise DocumentError("INVALID_REF", "plan instance ref must be a pin")
        if not isinstance(self.placement, Transform):
            raise DocumentError(
                "INVALID_PLACEMENT", "plan placement must be a transform"
            )
        if self.pattern is not None and not isinstance(self.pattern, Pattern):
            raise DocumentError("INVALID_PATTERN", "pattern must be a Pattern or None")
        object.__setattr__(self, "overrides", dict(self.overrides))

    def expand(self) -> tuple[Instance, ...]:
        if self.pattern is None:
            return (
                Instance(
                    self.id,
                    self.ref,
                    self.placement,
                    self.overrides,
                    self.name,
                    self.suppressed,
                    self.visible,
                ),
            )
        instances = []
        for index in range(self.pattern.count):
            instances.append(
                Instance(
                    id=f"{self.id}_{index}",
                    ref=self.ref,
                    placement=_compose(self.placement, self.pattern.placement(index)),
                    overrides=dict(self.overrides),
                    name=f"{self.name or self.id}_{index}",
                    suppressed=self.suppressed,
                    visible=self.visible,
                )
            )
        return tuple(instances)


@dataclass(frozen=True)
class AssemblyPlan:
    id: str
    name: str
    instances: tuple[PlanInstance, ...] = ()
    version: int = 1
    checks: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        _text(self.id, "assembly plan id")
        if not isinstance(self.name, str):
            raise DocumentError("INVALID_FIELD", "assembly plan name must be a string")
        if (
            isinstance(self.version, bool)
            or not isinstance(self.version, int)
            or self.version < 1
        ):
            raise DocumentError("INVALID_VERSION", "assembly plan version must be >= 1")
        seen: set[str] = set()
        for instance in self.instances:
            if instance.id in seen:
                raise DocumentError(
                    "DUPLICATE_ID", f"duplicate plan instance {instance.id!r}"
                )
            seen.add(instance.id)
        object.__setattr__(self, "instances", tuple(self.instances))
        object.__setattr__(self, "checks", tuple(dict(item) for item in self.checks))

    def expand(self) -> tuple[Instance, ...]:
        result: list[Instance] = []
        for spec in self.instances:
            result.extend(spec.expand())
        ids = [instance.id for instance in result]
        duplicates = {item for item in ids if ids.count(item) > 1}
        if duplicates:
            raise DocumentError(
                "DUPLICATE_ID",
                f"expanded instance ids collide: {', '.join(sorted(duplicates))}",
            )
        return tuple(result)


def compile_assembly_plan(
    plan: AssemblyPlan, assembly_id: str | None = None, version: int | None = None
) -> AssemblyDocument:
    """Expand a plan into an immutable assembly document."""
    return AssemblyDocument(
        id=assembly_id or plan.id,
        name=plan.name,
        version=version or plan.version,
        instances=plan.expand(),
    )


def _object(payload: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise DocumentError("INVALID_JSON", f"{label} payload must be a JSON object")
    return payload


def _reject_unknown(
    payload: Mapping[str, Any], allowed: frozenset[str], label: str
) -> None:
    unknown = sorted(repr(key) for key in payload if key not in allowed)
    if unknown:
        raise DocumentError(
            "UNKNOWN_FIELD", f"unknown {label} field(s): {', '.join(unknown)}"
        )


def _required(payload: Mapping[str, Any], key: str, label: str) -> Any:
    if key not in payload:
        raise DocumentError("MISSING_FIELD", f"{label} requires field {key!r}")
    return payload[key]


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DocumentError("INVALID_PATTERN", f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise DocumentError("INVALID_PATTERN", f"{label} must be finite")
    return number


def pattern_from_json(payload: Mapping[str, Any]) -> Pattern:
    """A pattern is a placement rule; count and kind are required, the rest default."""
    payload = _object(payload, "pattern")
    _reject_unknown(payload, _PATTERN_FIELDS, "pattern")
    kind = _required(payload, "kind", "pattern")
    if not isinstance(kind, str) or not kind:
        raise DocumentError(
            "INVALID_PATTERN", "pattern kind must be a non-empty string"
        )
    count = _required(payload, "count", "pattern")
    if isinstance(count, bool) or not isinstance(count, int):
        raise DocumentError("INVALID_PATTERN", "pattern count must be an integer")
    axis = payload.get("axis", "Z")
    if not isinstance(axis, str):
        raise DocumentError("INVALID_PATTERN", "pattern axis must be a string")
    return Pattern(
        kind=kind,
        count=count,
        radius=_number(payload.get("radius", 0.0), "pattern radius"),
        start_angle=_number(payload.get("start_angle", 0.0), "pattern start_angle"),
        axis=axis,
        dx=_number(payload.get("dx", 0.0), "pattern dx"),
        dy=_number(payload.get("dy", 0.0), "pattern dy"),
        dz=_number(payload.get("dz", 0.0), "pattern dz"),
    )


def pattern_to_json(value: Pattern) -> dict[str, Any]:
    return {
        "kind": value.kind,
        "count": value.count,
        "radius": value.radius,
        "start_angle": value.start_angle,
        "axis": value.axis,
        "dx": value.dx,
        "dy": value.dy,
        "dz": value.dz,
    }


def plan_instance_from_json(payload: Mapping[str, Any]) -> PlanInstance:
    """One explicit instance or patterned group; the ref kind is required and explicit."""
    payload = _object(payload, "plan instance")
    _reject_unknown(payload, _INSTANCE_FIELDS, "plan instance")
    overrides = payload.get("overrides", {})
    if not isinstance(overrides, Mapping):
        raise DocumentError(
            "INVALID_FIELD", "plan instance overrides must be an object"
        )
    name = payload.get("name", "")
    if not isinstance(name, str):
        raise DocumentError("INVALID_FIELD", "plan instance name must be a string")
    flags: dict[str, bool] = {}
    for key, default in (("suppressed", False), ("visible", True)):
        value = payload.get(key, default)
        if not isinstance(value, bool):
            raise DocumentError(
                "INVALID_FIELD", f"plan instance {key} must be a boolean"
            )
        flags[key] = value
    pattern = payload.get("pattern")
    return PlanInstance(
        id=_required(payload, "id", "plan instance"),
        ref=reference_from_json(_required(payload, "ref", "plan instance")),
        placement=transform_from_json(payload.get("placement", {})),
        overrides=dict(overrides),
        name=name,
        suppressed=flags["suppressed"],
        visible=flags["visible"],
        pattern=None if pattern is None else pattern_from_json(pattern),
    )


def plan_instance_to_json(value: PlanInstance) -> dict[str, Any]:
    return {
        "id": value.id,
        "ref": reference_to_json(value.ref),
        "placement": transform_to_json(value.placement),
        "overrides": dict(value.overrides),
        "name": value.name,
        "suppressed": value.suppressed,
        "visible": value.visible,
        "pattern": pattern_to_json(value.pattern)
        if value.pattern is not None
        else None,
    }


def assembly_plan_from_json(payload: Mapping[str, Any]) -> AssemblyPlan:
    """Parse a declarative plan. A missing id is generated so callers need not invent one."""
    payload = _object(payload, "assembly plan")
    _reject_unknown(payload, _PLAN_FIELDS, "assembly plan")
    instances = _required(payload, "instances", "assembly plan")
    if isinstance(instances, (str, bytes)) or not isinstance(instances, (list, tuple)):
        raise DocumentError(
            "INVALID_JSON", "assembly plan instances must be a JSON array"
        )
    checks = payload.get("checks", ())
    if isinstance(checks, (str, bytes)) or not isinstance(checks, (list, tuple)):
        raise DocumentError("INVALID_JSON", "assembly plan checks must be a JSON array")
    normalized_checks: list[dict[str, Any]] = []
    for item in checks:
        if not isinstance(item, Mapping):
            raise DocumentError(
                "INVALID_JSON", "assembly plan checks must hold objects"
            )
        normalized_checks.append(dict(item))
    name = payload.get("name", "Assembly")
    if not isinstance(name, str):
        raise DocumentError("INVALID_FIELD", "assembly plan name must be a string")
    plan_id = payload.get("id")
    if plan_id is None:
        plan_id = f"a_{uuid.uuid4().hex[:10]}"
    return AssemblyPlan(
        id=plan_id,
        name=name,
        instances=tuple(plan_instance_from_json(item) for item in instances),
        version=payload.get("version", 1),
        checks=tuple(normalized_checks),
    )


def assembly_plan_to_json(value: AssemblyPlan) -> dict[str, Any]:
    return {
        "id": value.id,
        "name": value.name,
        "version": value.version,
        "instances": [plan_instance_to_json(item) for item in value.instances],
        "checks": [dict(item) for item in value.checks],
    }


__all__ = [
    "AssemblyPlan",
    "Pattern",
    "PlanInstance",
    "assembly_plan_from_json",
    "assembly_plan_to_json",
    "compile_assembly_plan",
    "pattern_from_json",
    "pattern_to_json",
    "plan_instance_from_json",
    "plan_instance_to_json",
]
