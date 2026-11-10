"""The seven feature types of the impeller slice.

A feature is a pure function: resolved inputs + params -> output value.
Nothing here knows about documents, versions or HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from cadwork import smlib as S

from . import checks
from .checks import CheckResult


class FeatureError(Exception):
    def __init__(self, code: str, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint


@dataclass(frozen=True)
class Param:
    kind: str
    default: Any
    minimum: float | None = None
    maximum: float | None = None
    unit: str | None = None
    choices: tuple[str, ...] | None = None
    description: str = ""

    def coerce(self, name: str, value: Any) -> Any:
        if self.kind == "bool":
            if not isinstance(value, bool):
                raise FeatureError("INVALID_PARAM", f"{name} must be a boolean")
            return value
        if self.kind == "int":
            if isinstance(value, bool) or not isinstance(value, int):
                raise FeatureError("INVALID_PARAM", f"{name} must be an integer")
            result: Any = value
        elif self.kind == "float":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise FeatureError("INVALID_PARAM", f"{name} must be a number")
            result = float(value)
        elif self.kind == "str":
            if not isinstance(value, str):
                raise FeatureError("INVALID_PARAM", f"{name} must be a string")
            if self.choices and value not in self.choices:
                raise FeatureError(
                    "INVALID_PARAM",
                    f"{name} must be one of {', '.join(self.choices)}, got {value!r}",
                )
            result = value
        else:
            raise FeatureError("INVALID_PARAM", f"{name} has an unknown kind {self.kind!r}")

        if self.minimum is not None and result < self.minimum:
            raise FeatureError("INVALID_PARAM", f"{name} must be >= {self.minimum}")
        if self.maximum is not None and result > self.maximum:
            raise FeatureError("INVALID_PARAM", f"{name} must be <= {self.maximum}")
        return result


@dataclass(frozen=True)
class FeatureOutput:
    value: Any
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FeatureSpec:
    type: str
    summary: str
    inputs: tuple[tuple[str, str], ...]  # (role, "part" | "faces" | "edges")
    params: dict[str, Param]
    build: Callable[[dict[str, Any], dict[str, Any]], FeatureOutput]
    check: Callable[[Any, dict[str, Any], dict[str, Any]], list[CheckResult]]


# ---------------------------------------------------------------- hub

def build_hub(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    r_in = params["r_in"]
    r_out = params["r_out"]
    z_in = params["z_in"]
    z_out = params["z_out"]
    back_t = params["back_t"]
    profile = [
        (r_in, z_in),
        (r_out, z_out),
        (r_out, z_out - back_t),
        (r_in, z_in - back_t),
    ]
    part = S.revolve(S.Polygon(*profile).on(S.Plane.XZ), S.Z)
    radius = params["fillet_r"]
    if radius > 0:
        part = part.fillet(part.edges().concave(), radius)
    return FeatureOutput(part)


def check_hub(part: Any, params: Mapping[str, Any], inputs: Mapping[str, Any]) -> list[CheckResult]:
    return [
        checks.valid(part),
        checks.solid(part),
        checks.watertight(part),
        checks.volume_gt(part, 0.0),
    ]


# ---------------------------------------------------------------- blade

def build_blade(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    r_in = params["r_in"]
    r_out = params["r_out"]
    b_out = params["b_out"]
    beta_in = params["beta_in"]
    beta_out = params["beta_out"]
    wrap = params["wrap"]
    thickness = params["t"]
    sections = params["sections"]
    sections_out: list[Any] = []
    for index in range(sections):
        u = index / (sections - 1)
        radius = r_in + u * (r_out - r_in)
        lean = beta_in + u * (beta_out - beta_in)
        section = S.Rectangle(thickness, b_out).on(S.Plane.YZ)
        section = section.rotate(S.X, lean)
        section = section.translate(radius, 0.0, b_out / 2.0)
        sections_out.append(section.rotate(S.Z, u * wrap))
    return FeatureOutput(S.loft(sections_out))


def check_blade(part: Any, params: Mapping[str, Any], inputs: Mapping[str, Any]) -> list[CheckResult]:
    return [
        checks.valid(part),
        checks.min_edge(part, 1e-6),
        checks.thickness_param(dict(params), "t", 0.8),
        checks.watertight(part),
    ]


# ---------------------------------------------------------------- pattern

def build_pattern(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    target = inputs["target"]
    copies = S.PolarLocations(0.0, params["count"]) * target
    return FeatureOutput(S.merge(copies))


def check_pattern(part: Any, params: Mapping[str, Any], inputs: Mapping[str, Any]) -> list[CheckResult]:
    count = params["count"]
    return [
        checks.valid(part),
        checks.solid(part),
        checks.volume_ratio(part, float(inputs["target"].volume) * count, 0.01),
        checks.face_count(part, minimum=count * 2),
    ]


# ---------------------------------------------------------------- boolean

def build_boolean(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    target = inputs["target"]
    tool = inputs["tool"]
    kind = params["kind"]
    if kind == "join":
        return FeatureOutput(target.fuse(tool))
    if kind == "cut":
        return FeatureOutput(target.cut(tool))
    return FeatureOutput(target.intersect(tool))


def check_boolean(part: Any, params: Mapping[str, Any], inputs: Mapping[str, Any]) -> list[CheckResult]:
    target = float(inputs["target"].volume)
    tool = float(inputs["tool"].volume)
    kind = params["kind"]
    if kind == "join":
        bounds = (max(target, tool), target + tool)
    elif kind == "cut":
        bounds = (0.0, target)
    else:
        bounds = (0.0, min(target, tool))
    return [
        checks.valid(part),
        checks.solid(part),
        checks.volume_between(part, *bounds),
    ]


# ---------------------------------------------------------------- fillet

def build_fillet(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    return FeatureOutput(inputs["target"].fillet(inputs["edges"], params["radius"]))


def check_fillet(part: Any, params: Mapping[str, Any], inputs: Mapping[str, Any]) -> list[CheckResult]:
    baseline = len(inputs["target"].faces())
    return [
        checks.valid(part),
        checks.face_count(part, minimum=baseline),
    ]


# ---------------------------------------------------------------- tag

def build_tag(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    faces = inputs["faces"]
    count = len(faces) if hasattr(faces, "__len__") else 1
    return FeatureOutput(
        inputs["target"],
        {"tag": {"name": params["name"], "kind": params["kind"], "faces": count}},
    )


def check_tag(part: Any, params: Mapping[str, Any], inputs: Mapping[str, Any]) -> list[CheckResult]:
    faces = inputs["faces"]
    count = len(faces) if hasattr(faces, "__len__") else 1
    return [
        CheckResult("ref_hit", count >= 1, {"faces": count}, "at least one face", None),
        checks.valid(part),
    ]


# ---------------------------------------------------------------- cavity

def build_cavity(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    target = inputs["target"]
    box = target.bbox()
    pad = params["z_pad"]
    radius = max(float(box.size[0]), float(box.size[1])) / 2.0 + pad
    if params["r_env"] > 0:
        radius = max(radius, params["r_env"])
    height = float(box.size[2]) + 2.0 * pad
    center_x = (float(box.min[0]) + float(box.max[0])) / 2.0
    center_y = (float(box.min[1]) + float(box.max[1])) / 2.0
    center_z = (float(box.min[2]) + float(box.max[2])) / 2.0
    envelope = S.Cylinder(radius, height).translate(center_x, center_y, center_z)
    return FeatureOutput(envelope.cut(target))


def check_cavity(part: Any, params: Mapping[str, Any], inputs: Mapping[str, Any]) -> list[CheckResult]:
    return [
        checks.valid(part),
        checks.watertight(part),
        checks.volume_gt(part, 0.0),
    ]


# ---------------------------------------------------------------- registry

FEATURES: dict[str, FeatureSpec] = {
    spec.type: spec
    for spec in (
        FeatureSpec(
            "hub_revolve",
            "Solid of revolution from a meridional profile (r_in, z_in) -> (r_out, z_out).",
            (),
            {
                "r_in": Param("float", 0.0, 0.0, 1e4, "mm", description="inner radius"),
                "r_out": Param("float", 45.0, 1e-3, 1e4, "mm", description="outer radius"),
                "z_in": Param("float", 0.0, -1e4, 1e4, "mm", description="profile height at r_in"),
                "z_out": Param("float", 0.0, -1e4, 1e4, "mm", description="profile height at r_out"),
                "back_t": Param("float", 4.0, 1e-3, 1e4, "mm", description="back disc thickness"),
                "fillet_r": Param("float", 0.0, 0.0, 1e3, "mm", description="optional hub fillet"),
            },
            build_hub,
            check_hub,
        ),
        FeatureSpec(
            "blade_loft",
            "Twisted blade lofted from radial sections (Rectangle in the YZ plane).",
            (),
            {
                "r_in": Param("float", 18.0, 0.0, 1e4, "mm"),
                "r_out": Param("float", 44.0, 1e-3, 1e4, "mm"),
                "b_out": Param("float", 20.0, 1e-3, 1e4, "mm", description="blade span in Z"),
                "beta_in": Param("float", 25.0, -89.0, 89.0, "deg", description="inlet lean"),
                "beta_out": Param("float", 35.0, -89.0, 89.0, "deg", description="outlet lean"),
                "wrap": Param("float", 30.0, -360.0, 360.0, "deg", description="total sweep"),
                "t": Param("float", 3.0, 0.8, 1e3, "mm", description="blade thickness"),
                "sections": Param("int", 5, 2, 64, description="loft sections"),
            },
            build_blade,
            check_blade,
        ),
        FeatureSpec(
            "pattern_circular",
            "Circular pattern of the target around the Z axis.",
            (("target", "part"),),
            {
                "count": Param("int", 9, 2, 360),
            },
            build_pattern,
            check_pattern,
        ),
        FeatureSpec(
            "boolean",
            "Boolean of target with tool: join, cut or intersect.",
            (("target", "part"), ("tool", "part")),
            {
                "kind": Param("str", "join", choices=("join", "cut", "intersect")),
            },
            build_boolean,
            check_boolean,
        ),
        FeatureSpec(
            "fillet",
            "Round the given edges of the target.",
            (("target", "part"), ("edges", "edges")),
            {
                "radius": Param("float", 0.3, 1e-4, 1e3, "mm"),
            },
            build_fillet,
            check_fillet,
        ),
        FeatureSpec(
            "tag_boundary",
            "Name a face set as a CFD boundary; geometry is unchanged.",
            (("target", "part"), ("faces", "faces")),
            {
                "name": Param("str", "boundary"),
                "kind": Param(
                    "str", "wall",
                    choices=("inlet", "outlet", "wall", "symmetry", "interface", "internal"),
                ),
            },
            build_tag,
            check_tag,
        ),
        FeatureSpec(
            "cavity_extraction",
            "Fluid volume: a cylindrical envelope minus the target.",
            (("target", "part"),),
            {
                "r_env": Param("float", 0.0, 0.0, 1e4, "mm", description="0 = derive from bbox"),
                "z_pad": Param("float", 2.0, 0.0, 1e3, "mm"),
            },
            build_cavity,
            check_cavity,
        ),
    )
}


def resolve_params(spec: FeatureSpec, provided: Mapping[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(provided) - set(spec.params))
    if unknown:
        raise FeatureError(
            "UNKNOWN_PARAM",
            f"{spec.type} has no parameter {', '.join(unknown)}",
            hint=f"known parameters: {', '.join(sorted(spec.params))}",
        )
    return {name: param.coerce(name, provided.get(name, param.default))
            for name, param in spec.params.items()}


def validate_feature(feature_type: str, refs: Mapping[str, Any]) -> FeatureSpec:
    spec = FEATURES.get(feature_type)
    if spec is None:
        raise FeatureError(
            "UNKNOWN_FEATURE_TYPE",
            f"unknown feature type {feature_type!r}",
            hint=f"available: {', '.join(sorted(FEATURES))}",
        )
    roles = {role for role, _ in spec.inputs}
    if set(refs) != roles:
        missing = sorted(roles - set(refs))
        extra = sorted(set(refs) - roles)
        raise FeatureError(
            "INVALID_REFS",
            f"{feature_type} refs: missing {missing}, unexpected {extra}",
            hint=f"required roles: {', '.join(sorted(roles)) or '(none)'}",
        )
    return spec


def catalog() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for spec in FEATURES.values():
        entries.append({
            "type": spec.type,
            "summary": spec.summary,
            "inputs": [{"role": role, "kind": kind} for role, kind in spec.inputs],
            "params": {
                name: {
                    "kind": param.kind,
                    "default": param.default,
                    "min": param.minimum,
                    "max": param.maximum,
                    "unit": param.unit,
                    "choices": list(param.choices) if param.choices else None,
                    "description": param.description,
                }
                for name, param in spec.params.items()
            },
        })
    return entries
