"""Adapters for the operations the kernel does not expose as one call.

Everything here is justified by a kernel fact, not by a missing wrapper:

* ``pattern`` applies ``Locations * shape`` (an operator) and merges the copies;
* ``tag_boundary`` records document metadata (CFD boundary intent);
* ``import_base`` freezes an external B-Rep as a document base body;
* ``place_on`` is the face/plane placement (``shape.on(...)``) that the
  kernel exposes as a method on every shape, so one adapter covers them all.
"""

from __future__ import annotations

from typing import Any

from cadwork import smlib as S

from . import checks
from .checks import CheckResult
from .features import FeatureError, FeatureOutput, FeatureSpec, InputRole, Param


def _items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _face_signature(face: Any) -> dict[str, Any]:
    center = face.center()
    normal = face.normal_at(center)
    return {
        "center": [round(float(center[i]), 4) for i in range(3)],
        "normal": [round(float(normal[i]), 4) for i in range(3)],
        "area": round(float(face.area), 4),
        "surface": str(
            getattr(face, "surface_type", None) or getattr(face, "geom_type", "face")
        ),
    }


def _build_pattern(inputs: dict[str, Any], params: dict[str, Any]) -> FeatureOutput:
    target = inputs["target"]
    kind = params["kind"]
    count = int(params["count"])
    if kind == "circular":
        locations = S.PolarLocations(
            params["radius"],
            count,
            start_angle=params["start_angle"],
            angular_range=params["angular_range"],
        )
    elif kind == "linear":
        points = [
            (params["dx"] * index, params["dy"] * index, params["dz"] * index)
            for index in range(count)
        ]
        locations = S.Locations(*points)
    elif kind == "grid":
        locations = S.GridLocations(
            params["x_spacing"],
            params["y_spacing"],
            int(params["x_count"]),
            int(params["y_count"]),
        )
        count = int(params["x_count"]) * int(params["y_count"])
    else:
        raise FeatureError("INVALID_PARAM", f"unknown pattern kind {kind!r}")
    copies = locations * target
    merged = S.merge(list(copies))
    return FeatureOutput(
        merged,
        {"pattern": {"kind": kind, "count": count, "copies": len(list(copies))}},
    )


def _check_pattern(
    value: Any, params: dict[str, Any], inputs: dict[str, Any]
) -> list[CheckResult]:
    count = int(params["count"])
    if params["kind"] == "grid":
        count = int(params["x_count"]) * int(params["y_count"])
    return [
        checks.valid(value),
        checks.solid(value),
        checks.watertight(value),
        checks.volume_gt(value, 0.0),
        checks.face_count(value, minimum=count),
    ]


PATTERN = FeatureSpec(
    type="pattern",
    summary="Repeat a body with a circular, linear or grid array and merge the copies.",
    inputs=(InputRole("target", "part"),),
    params={
        "kind": Param("enum", "circular", choices=("circular", "linear", "grid")),
        "count": Param("int", 9, 1, 1000, unit="copies"),
        "radius": Param(
            "float",
            0.0,
            0.0,
            1e5,
            unit="mm",
            description="bolt-circle radius; 0 turns the copies",
        ),
        "start_angle": Param("float", 0.0, -360.0, 360.0, unit="deg"),
        "angular_range": Param("float", 360.0, -360.0, 360.0, unit="deg"),
        "dx": Param("float", 0.0, -1e5, 1e5, unit="mm"),
        "dy": Param("float", 0.0, -1e5, 1e5, unit="mm"),
        "dz": Param("float", 0.0, -1e5, 1e5, unit="mm"),
        "x_count": Param("int", 2, 1, 200),
        "y_count": Param("int", 2, 1, 200),
        "x_spacing": Param("float", 10.0, 0.01, 1e5, unit="mm"),
        "y_spacing": Param("float", 10.0, 0.01, 1e5, unit="mm"),
    },
    build=_build_pattern,
    check=_check_pattern,
    tier="adapter",
    origin="adapter:pattern",
    return_kind="part",
)


def _build_tag(inputs: dict[str, Any], params: dict[str, Any]) -> FeatureOutput:
    faces = _items(inputs["faces"])
    signatures = []
    for face in faces:
        try:
            signatures.append(_face_signature(face))
        except Exception:
            continue
    return FeatureOutput(
        inputs["target"],
        {
            "tag": {
                "name": params["name"],
                "kind": params["kind"],
                "faces": len(faces),
                "signatures": signatures,
            }
        },
    )


def _check_tag(
    value: Any, params: dict[str, Any], inputs: dict[str, Any]
) -> list[CheckResult]:
    return [checks.items(inputs["faces"])]


TAG = FeatureSpec(
    type="tag_boundary",
    summary="Name a set of faces as a CFD boundary (inlet/outlet/wall) and record their signatures.",
    inputs=(InputRole("target", "part"), InputRole("faces", "faces")),
    params={
        "name": Param("str", "wall", description="boundary name used by the exporter"),
        "kind": Param(
            "enum", "wall", choices=("inlet", "outlet", "wall", "symmetry", "other")
        ),
    },
    build=_build_tag,
    check=_check_tag,
    tier="annotation",
    origin="adapter:tag_boundary",
    return_kind="same",
)


_IMPORTERS = {
    "step": S.import_step,
    "iges": S.import_iges,
    "brep": S.import_brep,
    "stl": S.import_stl,
}


def _build_import(inputs: dict[str, Any], params: dict[str, Any]) -> FeatureOutput:
    importer = _IMPORTERS.get(params["format"])
    if importer is None:
        raise FeatureError(
            "INVALID_PARAM", f"unsupported import format {params['format']!r}"
        )
    part = importer(params["ref"])
    # STEP/IGES importers return a ShapeList even for a single body; every
    # downstream check expects a Part. Multi-body files are merged into one
    # multi-cell Part so a reference assembly can still be frozen as one body.
    if isinstance(part, S.ShapeList):
        part = part.one() if len(part) == 1 else S.merge(part)
    if params["heal"]:
        part = part.heal()
    return FeatureOutput(
        part, {"import": {"format": params["format"], "sha256": params["sha256"]}}
    )


def _check_import(
    value: Any, params: dict[str, Any], inputs: dict[str, Any]
) -> list[CheckResult]:
    return [checks.valid(value), checks.solid(value)]


IMPORT_BASE = FeatureSpec(
    type="import_base",
    summary="Freeze an external STEP/IGES/B-Rep file as a base body in the document.",
    inputs=(),
    params={
        "ref": Param(
            "str",
            "",
            description="store-relative path of the frozen copy",
            required=True,
        ),
        "format": Param("enum", "step", choices=("step", "iges", "brep", "stl")),
        "sha256": Param(
            "str", "", description="digest of the frozen bytes", required=True
        ),
        "heal": Param(
            "bool", False, description="run the kernel repair pass after import"
        ),
    },
    build=_build_import,
    check=_check_import,
    tier="adapter",
    origin="adapter:import_base",
    return_kind="part",
)


def _build_place(inputs: dict[str, Any], params: dict[str, Any]) -> FeatureOutput:
    shape = inputs["shape"]
    face = inputs.get("face")
    plane = params.get("plane")
    if face is not None:
        target = face
    elif plane:
        target = getattr(S.Plane, plane).offset(params["offset"])
    else:
        raise FeatureError(
            "INVALID_PARAM",
            "place_on needs a face ref or a plane",
            hint="set refs.face, or params.plane to XY/XZ/YZ",
        )
    return FeatureOutput(shape.on(target))


def _check_place(
    value: Any, params: dict[str, Any], inputs: dict[str, Any]
) -> list[CheckResult]:
    if hasattr(value, "is_valid"):
        return [checks.valid(value)]
    return [checks.extent(value, 0.0)]


PLACE_ON = FeatureSpec(
    type="place_on",
    summary="Place a sketch, curve or body on a picked face or on a world plane.",
    inputs=(
        InputRole("shape", "shape"),
        InputRole("face", "face", optional=True),
    ),
    params={
        "plane": Param(
            "enum",
            None,
            choices=("XY", "XZ", "YZ"),
            description="world plane when no face is given",
        ),
        "offset": Param("float", 0.0, -1e5, 1e5, unit="mm"),
    },
    build=_build_place,
    check=_check_place,
    tier="adapter",
    origin="adapter:place_on",
    return_kind="same",
)


ADAPTERS = (PATTERN, TAG, IMPORT_BASE, PLACE_ON)


def _edge_signature(edge: Any) -> tuple[float, float, float, float, str]:
    center = edge.center()
    return (
        float(center[0]),
        float(center[1]),
        float(center[2]),
        float(edge.length),
        str(getattr(edge, "geom_type", "edge")),
    )


def _find_edge(
    part: Any, signature: tuple[float, float, float, float, str]
) -> Any | None:
    """Find the current edge that corresponds to a pre-blend edge.

    A blend changes the edge list, so an edge object from the input cannot be
    reused. Match on position, length and geometry type; a blend group is only
    applied to edges that still exist after earlier blends.
    """
    cx, cy, cz, length, geom = signature
    best = None
    best_score = float("inf")
    for edge in part.edges():
        try:
            center = edge.center()
            current_length = float(edge.length)
            current_geom = str(getattr(edge, "geom_type", "edge"))
        except Exception:
            continue
        distance = (
            (float(center[0]) - cx) ** 2
            + (float(center[1]) - cy) ** 2
            + (float(center[2]) - cz) ** 2
        ) ** 0.5
        length_delta = abs(current_length - length) / max(length, 1.0)
        score = distance + 20.0 * length_delta + (0.0 if current_geom == geom else 0.5)
        if score < best_score:
            best = edge
            best_score = score
    return best


def _blend_one(part: Any, edge: Any, kind: str, size: float, propagate: bool) -> Any:
    if kind == "fillet":
        return part.fillet([edge], size, propagate=propagate)
    return part.chamfer([edge], size, propagate=propagate)


def _build_blend_group(inputs: dict[str, Any], params: dict[str, Any]) -> FeatureOutput:
    target = inputs["target"]
    edges = _items(inputs["edges"])
    if not edges:
        raise FeatureError("BLEND_EMPTY", "blend_group needs at least one edge")
    kind = params["kind"]
    size = float(params["size"])
    propagate = bool(params["propagate"])
    try:
        if kind == "fillet":
            result = target.fillet(edges, size, propagate=propagate)
        else:
            result = target.chamfer(edges, size, propagate=propagate)
        return FeatureOutput(
            result, {"blend": {"kind": kind, "applied": len(edges), "skipped": 0}}
        )
    except Exception as group_error:
        if params["on_failure"] == "fail":
            raise FeatureError(
                "BLEND_FAILED",
                f"{kind} failed for the selected edge group: {group_error}",
                hint="use on_failure=skip to isolate non-blendable edges",
            ) from group_error

    current = target
    applied: list[str] = []
    skipped: list[str] = []
    signatures = [_edge_signature(edge) for edge in edges]
    for signature in signatures:
        current_edge = _find_edge(current, signature)
        if current_edge is None:
            skipped.append(
                f"edge@({signature[0]:.2f},{signature[1]:.2f},{signature[2]:.2f})"
            )
            continue
        try:
            current = _blend_one(current, current_edge, kind, size, propagate)
            applied.append(
                f"edge@({signature[0]:.2f},{signature[1]:.2f},{signature[2]:.2f})"
            )
        except Exception:
            skipped.append(
                f"edge@({signature[0]:.2f},{signature[1]:.2f},{signature[2]:.2f})"
            )
    if not applied:
        raise FeatureError(
            "BLEND_FAILED",
            f"{kind} failed for every selected edge",
            hint="inspect the edge geometry and reduce the radius/length",
        )
    return FeatureOutput(
        current,
        {
            "blend": {
                "kind": kind,
                "applied": len(applied),
                "skipped": len(skipped),
                "skipped_edges": skipped,
            }
        },
    )


def _check_blend_group(
    value: Any, params: dict[str, Any], inputs: dict[str, Any]
) -> list[CheckResult]:
    return [
        checks.valid(value),
        checks.solid(value),
        checks.watertight(value),
        checks.volume_gt(value, 0.0),
    ]


BLEND_GROUP = FeatureSpec(
    type="blend_group",
    summary="Round or bevel a set of edges; a failed group is retried per edge "
    "with independent topology reselection, so one bad edge cannot "
    "abort the whole set.",
    inputs=(InputRole("target", "part"), InputRole("edges", "edges")),
    params={
        "kind": Param("enum", "fillet", choices=("fillet", "chamfer")),
        "size": Param(
            "float",
            None,
            required=True,
            unit="mm",
            description="fillet radius or chamfer setback",
        ),
        "propagate": Param("bool", True),
        "on_failure": Param("enum", "fail", choices=("fail", "skip")),
    },
    build=_build_blend_group,
    check=_check_blend_group,
    tier="adapter",
    origin="adapter:blend_group",
    return_kind="part",
)


def _build_cavity(inputs: dict[str, Any], params: dict[str, Any]) -> FeatureOutput:
    target = inputs["target"]
    box = target.bbox()
    size = box.size
    center = box.center
    radius = max(float(size[0]), float(size[1])) / 2.0 + float(params["r_env"])
    height = float(size[2]) + 2.0 * float(params["z_pad"])
    envelope = S.Cylinder(radius, height).translate(center)
    return FeatureOutput(envelope.cut(target))


def _check_cavity(
    value: Any, params: dict[str, Any], inputs: dict[str, Any]
) -> list[CheckResult]:
    return [
        checks.valid(value),
        checks.solid(value),
        checks.watertight(value),
        checks.volume_gt(value, 0.0),
    ]


CAVITY = FeatureSpec(
    type="cavity",
    summary="The fluid domain around a body: a padded cylindrical envelope minus the body.",
    inputs=(InputRole("target", "part"),),
    params={
        "r_env": Param(
            "float", 2.0, 0.0, 1e5, unit="mm", description="radial pad around the body"
        ),
        "z_pad": Param(
            "float", 2.0, 0.0, 1e5, unit="mm", description="axial pad above and below"
        ),
    },
    build=_build_cavity,
    check=_check_cavity,
    tier="adapter",
    origin="adapter:cavity",
    return_kind="part",
)


def _build_thread(inputs: dict[str, Any], params: dict[str, Any]) -> FeatureOutput:
    target = inputs.get("target")
    pitch = float(params["pitch"])
    length = float(params["length"])
    diameter = float(params["diameter"])
    depth = params.get("depth")
    if depth is None:
        depth = 0.6 * pitch
    depth = float(depth)
    center = tuple(float(value) for value in params["center"])
    # The tooth is drawn in the sweep frame: X is radial, Y is along the axis.
    # Putting the helix one half tooth below the major radius makes the tool
    # cut a helical groove; without a target the same body is a reusable tool.
    tooth = S.Polygon((0.0, -pitch / 3.0), (0.0, pitch / 3.0), (depth, 0.0))
    helix = S.Helix(
        pitch=pitch,
        height=length,
        radius=diameter / 2.0 - depth / 2.0,
        center=center,
        left_handed=bool(params["left_handed"]),
    )
    tool = S.sweep(tooth, helix)
    if target is not None:
        tool = target.cut(tool)
    return FeatureOutput(
        tool,
        {
            "thread": {
                "pitch": pitch,
                "length": length,
                "diameter": diameter,
                "depth": depth,
                "cut": target is not None,
            }
        },
    )


def _check_thread(
    value: Any, params: dict[str, Any], inputs: dict[str, Any]
) -> list[CheckResult]:
    return [checks.valid(value), checks.watertight(value), checks.volume_gt(value, 0.0)]


THREAD = FeatureSpec(
    type="thread",
    summary="Cut a helical external thread groove into a target, or produce the "
    "thread tool when no target is given. The axis is the target's Z axis.",
    inputs=(InputRole("target", "part", optional=True),),
    params={
        "diameter": Param("float", None, required=True, unit="mm"),
        "pitch": Param("float", None, required=True, unit="mm"),
        "length": Param("float", None, required=True, unit="mm"),
        "depth": Param(
            "float",
            None,
            unit="mm",
            description="radial thread depth; default 0.6 × pitch",
        ),
        "center": Param("vector", [0.0, 0.0, 0.0], unit="mm"),
        "left_handed": Param("bool", False),
    },
    build=_build_thread,
    check=_check_thread,
    tier="adapter",
    origin="adapter:thread",
    return_kind="part",
)


def _axis_vector(axis: str) -> tuple[float, float, float]:
    return {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}[axis]


def _build_stepped_bore(
    inputs: dict[str, Any], params: dict[str, Any]
) -> FeatureOutput:
    target = inputs["target"]
    center = tuple(float(value) for value in params["center"])
    axis = params["axis"]
    directions = _axis_vector(axis)
    box = target.bbox()
    diagonal = sum(float(size) ** 2 for size in box.size) ** 0.5
    tools = []
    start = 0.0
    for index in (1, 2):
        diameter = params.get(f"diameter_{index}")
        if diameter is None:
            continue
        depth = params.get(f"depth_{index}")
        through = bool(params.get("through")) and index == 2
        if through:
            depth = diagonal + 20.0
            start = -depth / 2.0
        elif depth is None:
            depth = diagonal + 20.0
        depth = float(depth)
        center_i = tuple(
            center[axis_index] + directions[axis_index] * (start + depth / 2.0)
            for axis_index in range(3)
        )
        tool = S.Cylinder(float(diameter) / 2.0, depth)
        if axis == "X":
            tool = tool.rotate(S.Y, 90.0)
        elif axis == "Y":
            tool = tool.rotate(S.X, 90.0)
        tool = tool.translate(*center_i)
        tools.append(tool)
        start += depth
    if not tools:
        raise FeatureError("BORE_EMPTY", "stepped_bore needs diameter_1")
    result = target.cut(tools)
    return FeatureOutput(
        result,
        {
            "bore": {
                "axis": axis,
                "stages": len(tools),
                "through": bool(params.get("through")),
            }
        },
    )


def _check_stepped_bore(
    value: Any, params: dict[str, Any], inputs: dict[str, Any]
) -> list[CheckResult]:
    return [
        checks.valid(value),
        checks.solid(value),
        checks.watertight(value),
        checks.volume_gt(value, 0.0),
    ]


STEPPED_BORE = FeatureSpec(
    type="stepped_bore",
    summary="Cut one or two coaxial bores along X, Y or Z, with independent "
    "diameters and depths; the second stage can be through.",
    inputs=(InputRole("target", "part"),),
    params={
        "diameter_1": Param("float", None, required=True, unit="mm"),
        "depth_1": Param("float", None, unit="mm"),
        "diameter_2": Param("float", None, unit="mm"),
        "depth_2": Param("float", None, unit="mm"),
        "through": Param("bool", False),
        "center": Param("vector", [0.0, 0.0, 0.0], unit="mm"),
        "axis": Param("enum", "Z", choices=("X", "Y", "Z")),
    },
    build=_build_stepped_bore,
    check=_check_stepped_bore,
    tier="adapter",
    origin="adapter:stepped_bore",
    return_kind="part",
)


ADAPTERS = ADAPTERS + (CAVITY, BLEND_GROUP, THREAD, STEPPED_BORE)
