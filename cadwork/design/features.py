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
class InputKind:
    """One way a reference resolves: the selectors it accepts and the kernel
    types it may produce. Steps declare a kind name; the engine looks it up
    here, so a new kind is a registration, not an engine edit."""

    selects: tuple[str, ...]
    accepts: tuple[type, ...] = ()


INPUT_KINDS: dict[str, InputKind] = {
    "part": InputKind(("self",)),
    "faces": InputKind(("faces",)),
    "edges": InputKind(("edges",)),
    "curve": InputKind(("self",), (S.Edge, S.Wire)),
    "profile": InputKind(("self",), (S.Sketch,)),
}


def register_input_kind(name: str, selects: tuple[str, ...],
                        accepts: tuple[type, ...] = ()) -> None:
    """Extend the reference vocabulary without touching the build engine."""
    INPUT_KINDS[name] = InputKind(tuple(selects), tuple(accepts))


@dataclass(frozen=True)
class FeatureSpec:
    type: str
    summary: str
    inputs: tuple[tuple[str, str], ...]  # (role, "part" | "faces" | "edges")
    params: dict[str, Param]
    build: Callable[[dict[str, Any], dict[str, Any]], FeatureOutput]
    check: Callable[[Any, dict[str, Any], dict[str, Any]], list[CheckResult]]
    # Roles that may be omitted: an open-topped shell, say. Declaring them here
    # keeps the engine free of per-step exceptions.
    optional: tuple[str, ...] = ()


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


# ---------------------------------------------------------------- curve spiral

def build_spiral(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    plane = getattr(S.Plane, params["plane"])
    curve = S.Spiral(
        params["r_start"], params["r_end"], params["turns"], plane,
        clockwise=params["clockwise"],
    )
    return FeatureOutput(curve)


def check_spiral(curve: Any, params: Mapping[str, Any], inputs: Mapping[str, Any]) -> list[CheckResult]:
    return [checks.extent(curve, 1e-6)]


# ---------------------------------------------------------------- curve helix

def build_helix(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    end_radius = params["end_radius"] if params["end_radius"] > 0 else None
    curve = S.Helix(
        params["pitch"], params["height"], params["radius"],
        direction=getattr(S, params["axis"]),
        end_radius=end_radius,
        left_handed=params["left_handed"],
    )
    return FeatureOutput(curve)


def check_helix(curve: Any, params: Mapping[str, Any], inputs: Mapping[str, Any]) -> list[CheckResult]:
    return [checks.extent(curve, 1e-6)]


# ---------------------------------------------------------------- profile rect

def _placed(shape: Any, params: Mapping[str, Any]) -> Any:
    """Every primitive and profile is built at the origin, then moved: one rule
    for all of them, so placement never becomes a modelling step of its own."""
    x, y, z = params.get("x", 0.0), params.get("y", 0.0), params.get("z", 0.0)
    return shape if (x == 0 and y == 0 and z == 0) else shape.translate(x, y, z)


def build_profile_rect(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    sketch = S.Rectangle(params["width"], params["height"], fillet=params["fillet"])
    return FeatureOutput(_placed(sketch, params))


def check_profile_rect(sketch: Any, params: Mapping[str, Any],
                       inputs: Mapping[str, Any]) -> list[CheckResult]:
    return [checks.extent(sketch, 1e-6)]


def build_profile_circle(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    return FeatureOutput(_placed(S.Circle(params["radius"]), params))


def build_profile_polygon(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    sketch = S.RegularPolygon(
        params["radius"], int(params["sides"]), inscribed=params["inscribed"],
    )
    return FeatureOutput(_placed(sketch, params))


def check_profile(sketch: Any, params: Mapping[str, Any],
                  inputs: Mapping[str, Any]) -> list[CheckResult]:
    return [checks.extent(sketch, 1e-6)]


# ---------------------------------------------------------------- solids

def check_solid(part: Any, params: Mapping[str, Any], inputs: Mapping[str, Any]) -> list[CheckResult]:
    return [
        checks.valid(part),
        checks.solid(part),
        checks.watertight(part),
        checks.volume_gt(part, 0.0),
    ]


def build_solid_box(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    return FeatureOutput(_placed(
        S.Box(params["length"], params["width"], params["height"]), params))


def build_solid_cylinder(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    return FeatureOutput(_placed(S.Cylinder(params["radius"], params["height"]), params))


def build_solid_cone(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    return FeatureOutput(_placed(
        S.Cone(params["bottom_radius"], params["top_radius"], params["height"]), params))


def build_solid_sphere(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    return FeatureOutput(_placed(S.Sphere(params["radius"]), params))


# ---------------------------------------------------------------- form

def build_extrude(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    part = S.extrude(
        inputs["profile"], params["amount"],
        both=params["both"], taper=params["taper"],
    )
    return FeatureOutput(part)


def build_revolve_profile(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    axis = getattr(S, params["axis"])
    part = S.revolve(inputs["profile"], axis, params["angle"])
    return FeatureOutput(part)


# ---------------------------------------------------------------- place and pattern

def build_transform(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    part = inputs["target"]
    for name in ("x", "y", "z"):
        angle = params[f"r{name}"]
        if angle:
            part = part.rotate(getattr(S, name.upper()), angle)
    if params["dx"] or params["dy"] or params["dz"]:
        part = part.translate(params["dx"], params["dy"], params["dz"])
    return FeatureOutput(part)


def check_transform(part: Any, params: Mapping[str, Any],
                    inputs: Mapping[str, Any]) -> list[CheckResult]:
    return [
        checks.valid(part),
        checks.watertight(part),
        checks.volume_ratio(part, float(inputs["target"].volume), 1e-6),
    ]


def build_pattern_linear(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    target = inputs["target"]
    count = int(params["count"])
    copies = [
        target if index == 0 else target.translate(
            index * params["dx"], index * params["dy"], index * params["dz"],
        )
        for index in range(count)
    ]
    return FeatureOutput(S.merge(copies))


def check_pattern_linear(part: Any, params: Mapping[str, Any],
                         inputs: Mapping[str, Any]) -> list[CheckResult]:
    count = int(params["count"])
    solids = len(part.solids())
    return [
        checks.valid(part),
        checks.watertight(part),
        checks.volume_ratio(part, float(inputs["target"].volume) * count, 0.01),
        CheckResult("copies", solids == count, {"solids": solids}, f"{count} solids"),
    ]


# ---------------------------------------------------------------- modify

def build_mirror(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    return FeatureOutput(S.mirror(inputs["target"], getattr(S.Plane, params["plane"])))


def check_mirror(part: Any, params: Mapping[str, Any],
                 inputs: Mapping[str, Any]) -> list[CheckResult]:
    return [
        checks.valid(part),
        checks.watertight(part),
        checks.volume_ratio(part, float(inputs["target"].volume), 1e-6),
    ]


def build_chamfer(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    return FeatureOutput(inputs["target"].chamfer(inputs["edges"], params["length"]))


def check_chamfer(part: Any, params: Mapping[str, Any],
                  inputs: Mapping[str, Any]) -> list[CheckResult]:
    return [
        checks.valid(part),
        checks.watertight(part),
        checks.volume_lt(part, float(inputs["target"].volume)),
    ]


def build_offset_solid(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    return FeatureOutput(
        inputs["target"].offset(params["distance"], corners=params["corners"]))


def check_offset_solid(part: Any, params: Mapping[str, Any],
                       inputs: Mapping[str, Any]) -> list[CheckResult]:
    target_volume = float(inputs["target"].volume)
    grown = (checks.volume_gt(part, target_volume) if params["distance"] > 0
             else checks.volume_lt(part, target_volume))
    return [checks.valid(part), checks.watertight(part), grown]


def build_split_part(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    plane = getattr(S.Plane, params["plane"])
    return FeatureOutput(S.split(inputs["target"], plane, keep=params["keep"]))


def check_split_part(part: Any, params: Mapping[str, Any],
                     inputs: Mapping[str, Any]) -> list[CheckResult]:
    target_volume = float(inputs["target"].volume)
    return [
        checks.valid(part),
        checks.watertight(part),
        checks.volume_gt(part, 0.0),
        checks.volume_lt(part, target_volume * 0.999),
    ]


def build_scale_part(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    return FeatureOutput(inputs["target"].scale(params["factor"]))


def check_scale_part(part: Any, params: Mapping[str, Any],
                     inputs: Mapping[str, Any]) -> list[CheckResult]:
    expected = float(inputs["target"].volume) * float(params["factor"]) ** 3
    return [
        checks.valid(part),
        checks.watertight(part),
        checks.volume_ratio(part, expected, 0.01),
    ]


def build_thicken_faces(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    return FeatureOutput(S.thicken(inputs["faces"], params["thickness"], both=params["both"]))


def check_thicken_faces(part: Any, params: Mapping[str, Any],
                        inputs: Mapping[str, Any]) -> list[CheckResult]:
    return [
        checks.valid(part),
        checks.solid(part),
        checks.watertight(part),
        checks.volume_gt(part, 0.0),
    ]


def build_hole(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    """A hole is a cutter, not a special kernel call: the plate's own bounds say
    where the top surface is, and depth 0 means through."""
    target = inputs["target"]
    bounds = target.bbox()
    top = float(bounds.max.z)
    radius = params["diameter"] / 2.0
    through = params["depth"] <= 0
    reach = float(bounds.size.z) + 2.0 if through else params["depth"]

    x, y = params["x"], params["y"]
    length = reach + 0.5
    cutter = S.Cylinder(radius, length).translate(x, y, top + 0.5 - length / 2.0)

    kind = params["kind"]
    if kind == "counterbore":
        cb_depth = params["cb_depth"]
        cutter = cutter.fuse(
            S.Cylinder(params["cb_diameter"] / 2.0, cb_depth + 0.5).translate(
                x, y, top + 0.5 - (cb_depth + 0.5) / 2.0))
    elif kind == "countersink":
        cs_depth = params["cs_depth"]
        cutter = cutter.fuse(
            S.Cone(radius, params["cs_diameter"] / 2.0, cs_depth + 0.5).translate(
                x, y, top + 0.5 - (cs_depth + 0.5) / 2.0))

    return FeatureOutput(target.cut(cutter))


def check_hole(part: Any, params: Mapping[str, Any],
               inputs: Mapping[str, Any]) -> list[CheckResult]:
    target_volume = float(inputs["target"].volume)
    return [
        checks.valid(part),
        checks.watertight(part),
        checks.volume_lt(part, target_volume),
        checks.volume_gt(part, target_volume * 0.5),
    ]


def build_pattern_grid(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    target = inputs["target"]
    copies = S.GridLocations(
        params["x_spacing"], params["y_spacing"],
        int(params["x_count"]), int(params["y_count"]),
    ) * target
    return FeatureOutput(S.merge(copies))


def check_pattern_grid(part: Any, params: Mapping[str, Any],
                       inputs: Mapping[str, Any]) -> list[CheckResult]:
    count = int(params["x_count"]) * int(params["y_count"])
    solids = len(part.solids())
    return [
        checks.valid(part),
        checks.watertight(part),
        checks.volume_ratio(part, float(inputs["target"].volume) * count, 0.01),
        CheckResult("copies", solids == count, {"solids": solids}, f"{count} solids"),
    ]


# ---------------------------------------------------------------- sweep

def build_sweep(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    scale = [(0.0, params["scale_start"]), (1.0, params["scale_end"])]
    part = S.sweep(
        inputs["profile"], inputs["path"],
        orient=params["orient"],
        translational=params["translational"],
        twist=params["twist"],
        scale=scale,
    )
    return FeatureOutput(part)


def check_sweep(part: Any, params: Mapping[str, Any], inputs: Mapping[str, Any]) -> list[CheckResult]:
    return [
        checks.valid(part),
        checks.solid(part),
        checks.watertight(part),
        checks.volume_gt(part, 0.0),
    ]


# ---------------------------------------------------------------- shell

def build_shell(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> FeatureOutput:
    part = S.shell(
        inputs["target"], params["thickness"],
        openings=inputs.get("openings"),
        outward=params["outward"], corners=params["corners"],
    )
    return FeatureOutput(part)


def check_shell(part: Any, params: Mapping[str, Any], inputs: Mapping[str, Any]) -> list[CheckResult]:
    return [
        checks.valid(part),
        checks.watertight(part),
        checks.volume_lt(part, float(inputs["target"].volume)),
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
        FeatureSpec(
            "curve_spiral",
            "Flat Archimedean spiral from r_start to r_end over `turns`; a sweep path.",
            (),
            {
                "r_start": Param("float", 30.0, 0.0, 1e4, "mm"),
                "r_end": Param("float", 70.0, 0.0, 1e4, "mm"),
                "turns": Param("float", 1.25, 0.05, 20.0, "turn"),
                "plane": Param("str", "XY", choices=("XY", "XZ", "YZ")),
                "clockwise": Param("bool", False),
            },
            build_spiral,
            check_spiral,
        ),
        FeatureSpec(
            "curve_helix",
            "Helix around an axis; optionally conical via end_radius. A sweep path.",
            (),
            {
                "pitch": Param("float", 20.0, 0.1, 1e4, "mm", description="rise per turn"),
                "height": Param("float", 20.0, 0.1, 1e4, "mm"),
                "radius": Param("float", 20.0, 1e-3, 1e4, "mm"),
                "end_radius": Param("float", 0.0, 0.0, 1e4, "mm", description="0 = stay cylindrical"),
                "axis": Param("str", "Z", choices=("X", "Y", "Z")),
                "left_handed": Param("bool", False),
            },
            build_helix,
            check_helix,
        ),
        FeatureSpec(
            "profile_rect",
            "Rectangular 2D profile for sweep, extrude and loft.",
            (),
            {
                "width": Param("float", 8.0, 1e-3, 1e4, "mm"),
                "height": Param("float", 20.0, 1e-3, 1e4, "mm"),
                "fillet": Param("float", 0.0, 0.0, 1e3, "mm"),
                "x": Param("float", 0.0, -1e4, 1e4, "mm"),
                "y": Param("float", 0.0, -1e4, 1e4, "mm"),
                "z": Param("float", 0.0, -1e4, 1e4, "mm"),
            },
            build_profile_rect,
            check_profile_rect,
        ),
        FeatureSpec(
            "sweep",
            "Sweep a profile along a curve, twisting and scaling along the way.",
            (("profile", "profile"), ("path", "curve")),
            {
                "twist": Param("float", 0.0, -3600.0, 3600.0, "deg"),
                "scale_start": Param("float", 1.0, 1e-3, 100.0),
                "scale_end": Param("float", 1.0, 1e-3, 100.0),
                "orient": Param("bool", True),
                "translational": Param("bool", False),
            },
            build_sweep,
            check_sweep,
        ),
        FeatureSpec(
            "shell",
            "Hollow a part into walls of a given thickness; open it by naming faces.",
            (("target", "part"), ("openings", "faces")),
            {
                "thickness": Param("float", 1.0, 1e-4, 1e3, "mm"),
                "outward": Param("bool", False),
                "corners": Param("str", "round", choices=("round", "sharp")),
            },
            build_shell,
            check_shell,
            optional=("openings",),
        ),
        FeatureSpec(
            "solid_box",
            "Box primitive, centred at its own origin, then placed.",
            (),
            {
                "length": Param("float", 80.0, 1e-3, 1e4, "mm"),
                "width": Param("float", 60.0, 1e-3, 1e4, "mm"),
                "height": Param("float", 20.0, 1e-3, 1e4, "mm"),
                "x": Param("float", 0.0, -1e4, 1e4, "mm"),
                "y": Param("float", 0.0, -1e4, 1e4, "mm"),
                "z": Param("float", 0.0, -1e4, 1e4, "mm"),
            },
            build_solid_box,
            check_solid,
        ),
        FeatureSpec(
            "solid_cylinder",
            "Cylinder primitive along Z.",
            (),
            {
                "radius": Param("float", 20.0, 1e-3, 1e4, "mm"),
                "height": Param("float", 40.0, 1e-3, 1e4, "mm"),
                "x": Param("float", 0.0, -1e4, 1e4, "mm"),
                "y": Param("float", 0.0, -1e4, 1e4, "mm"),
                "z": Param("float", 0.0, -1e4, 1e4, "mm"),
            },
            build_solid_cylinder,
            check_solid,
        ),
        FeatureSpec(
            "solid_cone",
            "Cone or frustum primitive along Z.",
            (),
            {
                "bottom_radius": Param("float", 20.0, 1e-3, 1e4, "mm"),
                "top_radius": Param("float", 0.0, 0.0, 1e4, "mm"),
                "height": Param("float", 30.0, 1e-3, 1e4, "mm"),
                "x": Param("float", 0.0, -1e4, 1e4, "mm"),
                "y": Param("float", 0.0, -1e4, 1e4, "mm"),
                "z": Param("float", 0.0, -1e4, 1e4, "mm"),
            },
            build_solid_cone,
            check_solid,
        ),
        FeatureSpec(
            "solid_sphere",
            "Sphere primitive.",
            (),
            {
                "radius": Param("float", 20.0, 1e-3, 1e4, "mm"),
                "x": Param("float", 0.0, -1e4, 1e4, "mm"),
                "y": Param("float", 0.0, -1e4, 1e4, "mm"),
                "z": Param("float", 0.0, -1e4, 1e4, "mm"),
            },
            build_solid_sphere,
            check_solid,
        ),
        FeatureSpec(
            "profile_circle",
            "Circular 2D profile.",
            (),
            {
                "radius": Param("float", 10.0, 1e-3, 1e4, "mm"),
                "x": Param("float", 0.0, -1e4, 1e4, "mm"),
                "y": Param("float", 0.0, -1e4, 1e4, "mm"),
                "z": Param("float", 0.0, -1e4, 1e4, "mm"),
            },
            build_profile_circle,
            check_profile,
        ),
        FeatureSpec(
            "profile_polygon",
            "Regular polygon 2D profile.",
            (),
            {
                "radius": Param("float", 10.0, 1e-3, 1e4, "mm"),
                "sides": Param("int", 6, 3, 64, "sides"),
                "inscribed": Param("bool", False),
                "x": Param("float", 0.0, -1e4, 1e4, "mm"),
                "y": Param("float", 0.0, -1e4, 1e4, "mm"),
                "z": Param("float", 0.0, -1e4, 1e4, "mm"),
            },
            build_profile_polygon,
            check_profile,
        ),
        FeatureSpec(
            "extrude",
            "Extrude a profile along its normal, optionally tapered and both ways.",
            (("profile", "profile"),),
            {
                "amount": Param("float", 10.0, -1e4, 1e4, "mm"),
                "taper": Param("float", 0.0, -45.0, 45.0, "deg"),
                "both": Param("bool", False),
            },
            build_extrude,
            check_solid,
        ),
        FeatureSpec(
            "revolve_profile",
            "Revolve a profile about an axis.",
            (("profile", "profile"),),
            {
                "axis": Param("str", "Z", choices=("X", "Y", "Z")),
                "angle": Param("float", 360.0, 1.0, 360.0, "deg"),
            },
            build_revolve_profile,
            check_solid,
        ),
        FeatureSpec(
            "transform",
            "Move and rotate a part: dx/dy/dz in mm, rx/ry/rz in degrees.",
            (("target", "part"),),
            {
                "dx": Param("float", 0.0, -1e4, 1e4, "mm"),
                "dy": Param("float", 0.0, -1e4, 1e4, "mm"),
                "dz": Param("float", 0.0, -1e4, 1e4, "mm"),
                "rx": Param("float", 0.0, -360.0, 360.0, "deg"),
                "ry": Param("float", 0.0, -360.0, 360.0, "deg"),
                "rz": Param("float", 0.0, -360.0, 360.0, "deg"),
            },
            build_transform,
            check_transform,
        ),
        FeatureSpec(
            "pattern_linear",
            "Repeat a part along a vector.",
            (("target", "part"),),
            {
                "count": Param("int", 3, 1, 50, "copies"),
                "dx": Param("float", 30.0, -1e4, 1e4, "mm"),
                "dy": Param("float", 0.0, -1e4, 1e4, "mm"),
                "dz": Param("float", 0.0, -1e4, 1e4, "mm"),
            },
            build_pattern_linear,
            check_pattern_linear,
        ),
        FeatureSpec(
            "mirror_part",
            "Mirror a part across a named plane.",
            (("target", "part"),),
            {
                "plane": Param("str", "XZ", choices=("XY", "XZ", "YZ")),
            },
            build_mirror,
            check_mirror,
        ),
        FeatureSpec(
            "chamfer",
            "Bevel the given edges by a fixed length.",
            (("target", "part"), ("edges", "edges")),
            {
                "length": Param("float", 2.0, 1e-3, 1e3, "mm"),
            },
            build_chamfer,
            check_chamfer,
        ),
        FeatureSpec(
            "offset_solid",
            "Grow or shrink a part by offsetting every face.",
            (("target", "part"),),
            {
                "distance": Param("float", 2.0, -1e3, 1e3, "mm"),
                "corners": Param("str", "sharp", choices=("sharp", "round")),
            },
            build_offset_solid,
            check_offset_solid,
        ),
        FeatureSpec(
            "split_part",
            "Keep one side of a part, split by a named plane.",
            (("target", "part"),),
            {
                "plane": Param("str", "XY", choices=("XY", "XZ", "YZ")),
                "keep": Param("str", "above", choices=("above", "below")),
            },
            build_split_part,
            check_split_part,
        ),
        FeatureSpec(
            "scale_part",
            "Scale a part about its origin.",
            (("target", "part"),),
            {
                "factor": Param("float", 1.5, 0.05, 20.0, "x"),
            },
            build_scale_part,
            check_scale_part,
        ),
        FeatureSpec(
            "pattern_grid",
            "Repeat a part on a rectangular grid.",
            (("target", "part"),),
            {
                "x_count": Param("int", 2, 1, 20, "copies"),
                "y_count": Param("int", 2, 1, 20, "copies"),
                "x_spacing": Param("float", 50.0, -1e4, 1e4, "mm"),
                "y_spacing": Param("float", 50.0, -1e4, 1e4, "mm"),
            },
            build_pattern_grid,
            check_pattern_grid,
        ),
        FeatureSpec(
            "thicken_faces",
            "Turn named faces into a solid of the given thickness.",
            (("faces", "faces"),),
            {
                "thickness": Param("float", 3.0, 1e-3, 1e3, "mm"),
                "both": Param("bool", False),
            },
            build_thicken_faces,
            check_thicken_faces,
        ),
        FeatureSpec(
            "hole",
            "Drill a hole from the top surface: simple, counterbore or countersink.",
            (("target", "part"),),
            {
                "x": Param("float", 0.0, -1e4, 1e4, "mm"),
                "y": Param("float", 0.0, -1e4, 1e4, "mm"),
                "diameter": Param("float", 8.0, 1e-3, 1e3, "mm"),
                "depth": Param("float", 0.0, 0.0, 1e4, "mm"),
                "kind": Param("str", "simple",
                              choices=("simple", "counterbore", "countersink")),
                "cb_diameter": Param("float", 16.0, 1e-3, 1e3, "mm"),
                "cb_depth": Param("float", 6.0, 1e-3, 1e3, "mm"),
                "cs_diameter": Param("float", 16.0, 1e-3, 1e3, "mm"),
                "cs_depth": Param("float", 4.0, 1e-3, 1e3, "mm"),
            },
            build_hole,
            check_hole,
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
    optional = set(spec.optional) & roles
    missing = sorted(roles - optional - set(refs))
    extra = sorted(set(refs) - roles)
    if missing or extra:
        raise FeatureError(
            "INVALID_REFS",
            f"{feature_type} refs: missing {missing}, unexpected {extra}",
            hint=f"required roles: {', '.join(sorted(roles - optional)) or '(none)'}"
                 + (f"; optional: {', '.join(sorted(optional))}" if optional else ""),
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
