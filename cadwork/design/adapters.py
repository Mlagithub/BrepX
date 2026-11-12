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
        "surface": str(getattr(face, "surface_type", None) or getattr(face, "geom_type", "face")),
    }


# ---------------------------------------------------------------- pattern


def _build_pattern(inputs: dict[str, Any], params: dict[str, Any]) -> FeatureOutput:
    target = inputs["target"]
    kind = params["kind"]
    count = int(params["count"])
    if kind == "circular":
        locations = S.PolarLocations(
            params["radius"], count,
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
            params["x_spacing"], params["y_spacing"],
            int(params["x_count"]), int(params["y_count"]),
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


def _check_pattern(value: Any, params: dict[str, Any], inputs: dict[str, Any]) -> list[CheckResult]:
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
        "radius": Param("float", 0.0, 0.0, 1e5, unit="mm", description="bolt-circle radius; 0 turns the copies"),
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


# ---------------------------------------------------------------- tag


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


def _check_tag(value: Any, params: dict[str, Any], inputs: dict[str, Any]) -> list[CheckResult]:
    return [checks.items(inputs["faces"])]


TAG = FeatureSpec(
    type="tag_boundary",
    summary="Name a set of faces as a CFD boundary (inlet/outlet/wall) and record their signatures.",
    inputs=(InputRole("target", "part"), InputRole("faces", "faces")),
    params={
        "name": Param("str", "wall", description="boundary name used by the exporter"),
        "kind": Param("enum", "wall", choices=("inlet", "outlet", "wall", "symmetry", "other")),
    },
    build=_build_tag,
    check=_check_tag,
    tier="annotation",
    origin="adapter:tag_boundary",
    return_kind="same",
)


# ---------------------------------------------------------------- import


_IMPORTERS = {
    "step": S.import_step,
    "iges": S.import_iges,
    "brep": S.import_brep,
    "stl": S.import_stl,
}


def _build_import(inputs: dict[str, Any], params: dict[str, Any]) -> FeatureOutput:
    importer = _IMPORTERS.get(params["format"])
    if importer is None:
        raise FeatureError("INVALID_PARAM", f"unsupported import format {params['format']!r}")
    part = importer(params["ref"])
    if params["heal"]:
        part = part.heal()
    return FeatureOutput(part, {"import": {"format": params["format"], "sha256": params["sha256"]}})


def _check_import(value: Any, params: dict[str, Any], inputs: dict[str, Any]) -> list[CheckResult]:
    return [checks.valid(value), checks.solid(value)]


IMPORT_BASE = FeatureSpec(
    type="import_base",
    summary="Freeze an external STEP/IGES/B-Rep file as a base body in the document.",
    inputs=(),
    params={
        "ref": Param("str", "", description="store-relative path of the frozen copy", required=True),
        "format": Param("enum", "step", choices=("step", "iges", "brep", "stl")),
        "sha256": Param("str", "", description="digest of the frozen bytes", required=True),
        "heal": Param("bool", False, description="run the kernel repair pass after import"),
    },
    build=_build_import,
    check=_check_import,
    tier="adapter",
    origin="adapter:import_base",
    return_kind="part",
)


# ---------------------------------------------------------------- place_on


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


def _check_place(value: Any, params: dict[str, Any], inputs: dict[str, Any]) -> list[CheckResult]:
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
        "plane": Param("enum", None, choices=("XY", "XZ", "YZ"),
                       description="world plane when no face is given"),
        "offset": Param("float", 0.0, -1e5, 1e5, unit="mm"),
    },
    build=_build_place,
    check=_check_place,
    tier="adapter",
    origin="adapter:place_on",
    return_kind="same",
)


ADAPTERS = (PATTERN, TAG, IMPORT_BASE, PLACE_ON)


# ---------------------------------------------------------------- cavity


def _build_cavity(inputs: dict[str, Any], params: dict[str, Any]) -> FeatureOutput:
    target = inputs["target"]
    box = target.bbox()
    size = box.size
    center = box.center
    radius = max(float(size[0]), float(size[1])) / 2.0 + float(params["r_env"])
    height = float(size[2]) + 2.0 * float(params["z_pad"])
    envelope = S.Cylinder(radius, height).translate(center)
    return FeatureOutput(envelope.cut(target))


def _check_cavity(value: Any, params: dict[str, Any], inputs: dict[str, Any]) -> list[CheckResult]:
    return [checks.valid(value), checks.solid(value), checks.watertight(value),
            checks.volume_gt(value, 0.0)]


CAVITY = FeatureSpec(
    type="cavity",
    summary="The fluid domain around a body: a padded cylindrical envelope minus the body.",
    inputs=(InputRole("target", "part"),),
    params={
        "r_env": Param("float", 2.0, 0.0, 1e5, unit="mm", description="radial pad around the body"),
        "z_pad": Param("float", 2.0, 0.0, 1e5, unit="mm", description="axial pad above and below"),
    },
    build=_build_cavity,
    check=_check_cavity,
    tier="adapter",
    origin="adapter:cavity",
    return_kind="part",
)

ADAPTERS = ADAPTERS + (CAVITY,)
