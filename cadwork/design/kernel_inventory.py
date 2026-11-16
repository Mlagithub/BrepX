"""Inventory of every public ``smlibpy`` callable and its destination.

``kernel_actions`` generates one document action per bindable kernel call, a
few adapters cover operators and document metadata, and everything else enters
the document through ``refs``/``verify``/``service`` or is deliberately
deferred.

This module is the auditable map of that split.  It enumerates the installed
``smlibpy`` API at import time (top-level public functions plus every public
callable method of every public class) and classifies each callable with one
destination:

``GEN``
    A single kernel call registered as a ``k_<name>`` document action.
``ADAPTER``
    Enters through an adapter (``pattern``, ``tag_boundary``, ``import_base``,
    ``place_on``).
``TEMPLATE``
    A plan template, never a document type.
``REF``
    A ``ShapeList`` selector or topology query consumed by ``refs.py``.
``MEASURE``
    A measurement/query consumed by ``verify.py`` or the probe.
``SERVICE``
    IO / render / export / import / mesh path owned by ``service/``.
``DEFER``
    A signature the document action layer cannot bind: non-scalar, variadic,
    list or callback.
``N/A``
    Not a modeling capability (data class, error, builder or metadata).
``EXCLUDED``
    An internal/dunder callable; enumeration skips these.

The classification tables are explicit.  The six large classes (``Part``,
``Sketch``, ``Profile``, ``ShapeList``, ``Face`` and ``Shape``) have a complete
per-method table so a kernel upgrade that adds a method surfaces it as
*unclassified* instead of silently defaulting it; other classes use a
class-level default.  ``scripts/kernel_inventory.py --check`` turns any
unclassified callable into a non-zero exit code.
"""

from __future__ import annotations

import argparse
import inspect
import json
from collections.abc import Iterable
from typing import Any

import smlibpy

SCHEMA_VERSION = 1

GEN = "GEN"
ADAPTER = "ADAPTER"
TEMPLATE = "TEMPLATE"
REF = "REF"
MEASURE = "MEASURE"
SERVICE = "SERVICE"
DEFER = "DEFER"
NA = "N/A"
EXCLUDED = "EXCLUDED"

DESTINATIONS: tuple[str, ...] = (
    GEN,
    ADAPTER,
    TEMPLATE,
    REF,
    MEASURE,
    SERVICE,
    DEFER,
    NA,
    EXCLUDED,
)

_REASONS: dict[str, str] = {
    GEN: "single kernel call; exposed as a k_* document action",
    ADAPTER: "adapter-level operation (pattern/tag_boundary/import_base/place_on)",
    TEMPLATE: "plan template, not a document action",
    REF: "ShapeList selector / topology query consumed by refs.py",
    MEASURE: "measurement or query consumed by verify.py / probe",
    SERVICE: "IO / render / export / import / mesh path owned by service/",
    DEFER: "non-scalar, variadic, list or callback signature",
    NA: "not a modeling capability (data class, error, builder or metadata)",
    EXCLUDED: "internal / dunder callable",
}


def _table(*groups: tuple[str, Iterable[str]]) -> dict[str, str]:
    """Merge ``(destination, names)`` groups into one dispatch table.

    Duplicates are a classification bug, so they raise instead of silently
    letting the last group win.
    """

    merged: dict[str, str] = {}
    for destination, names in groups:
        for name in names:
            if name in merged:
                raise RuntimeError(f"{name!r} classified twice in kernel inventory")
            merged[name] = destination
    return merged


# The expected top-level surface is 156 names.  The table follows smlibpy
# 0.6.2 spellings: it lists ``Hull`` (there is no ``hull``), omits ``heal``
# (it exists only as ``Part.heal``), and includes ``fit_curve`` (a public
# top-level callable).
_TOP_LEVEL: dict[str, str] = _table(
    (
        GEN,
        {
            "AnnularSector",
            "ArcSlot",
            "Bezier",
            "Box",
            "CenterArc",
            "Circle",
            "Cone",
            "ConicArc",
            "CounterBoreHole",
            "CounterSinkHole",
            "Cylinder",
            "Ellipse",
            "EllipticalArc",
            "FilletPolyline",
            "Helix",
            "Hole",
            "HyperbolicArc",
            "Line",
            "ParabolicArc",
            "PolarLine",
            "Polygon",
            "Polyline",
            "Pyramid",
            "RadiusArc",
            "Rectangle",
            "RegularPolygon",
            "RoundedRectangle",
            "SagittaArc",
            "Slot",
            "Sphere",
            "Spiral",
            "Spline",
            "Stroke",
            "TangentArc",
            "ThreePointArc",
            "Text",
            "Torus",
            "Trapezoid",
            "Triangle",
            "Wedge",
            "bend",
            "blend",
            "chamfer",
            "cut",
            "draft",
            "extrude",
            "extend",
            "fill",
            "fillet",
            "fit_curve",
            "flange",
            "fold",
            "fuse",
            "imprint",
            "intersect",
            "loft",
            "make_face",
            "match_edge",
            "merge",
            "merge_faces",
            "mirror",
            "move_faces",
            "network",
            "offset",
            "offset_faces",
            "remove_faces",
            "remove_fillets",
            "revolve",
            "ruled",
            "scale",
            "section",
            "shell",
            "split",
            "stitch",
            "surface_fillet",
            "sweep",
            "swing",
            "taper",
            "thicken",
            "twist",
            "unfold",
            "unroll",
            "xor",
            "Hull",
        },
    ),
    (
        MEASURE,
        {
            "bend_allowance",
            "bend_deduction",
            "developed_length",
            "fillet_preview",
            "flat_pattern",
            "intersection_curves",
            "outline",
            "parting_line",
            "project",
            "silhouette",
            "slices",
        },
    ),
    (
        SERVICE,
        {
            "diff_images",
            "drawing_views",
            "export",
            "export_brep",
            "export_dxf",
            "export_glb",
            "export_gltf",
            "export_obj",
            "export_step",
            "export_stl",
            "export_svg",
            "export_usd",
            "from_brep",
            "from_dxf",
            "from_dxf_wires",
            "from_file",
            "from_iges",
            "from_smb",
            "from_smp",
            "from_step",
            "from_step_model",
            "from_stl",
            "from_usd",
            "import_brep",
            "import_dxf",
            "import_dxf_wires",
            "import_iges",
            "import_step",
            "import_stl",
            "import_usd",
            "load",
            "read_step",
            "render",
            "save",
            "show",
            "tessellate",
            "to_brep",
            "to_dxf",
            "to_file",
            "to_glb",
            "to_gltf",
            "to_obj",
            "to_smb",
            "to_smp",
            "to_step",
            "to_stl",
            "to_svg",
            "to_usd",
        },
    ),
    (
        DEFER,
        {
            "deform",
            "flatten",
            "make_compatible",
            "nurbs_surface",
            "push",
            "surface",
            "trim",
            "warp",
        },
    ),
    (
        NA,
        {
            "GridLocations",
            "HexLocations",
            "PolarLocations",
            "Pos",
            "Rot",
        },
    ),
)

_TOP_LEVEL_NOTES: dict[str, str] = {
    "fit_curve": "curve fit; public top-level callable in smlibpy 0.6.2",
    "Hull": "exported spelling is Hull; there is no top-level hull",
}

_PART: dict[str, str] = _table(
    (
        GEN,
        {
            "bend",
            "chamfer",
            "cut",
            "draft",
            "fillet",
            "flange",
            "fold",
            "fuse",
            "heal",
            "imprint",
            "intersect",
            "merge",
            "mirror",
            "move_faces",
            "offset",
            "offset_faces",
            "remove_faces",
            "remove_fillets",
            "rotate",
            "scale",
            "section",
            "shell",
            "split",
            "taper",
            "translate",
            "twist",
            "unfold",
            "unroll",
        },
    ),
    (
        REF,
        {
            "cell_at",
            "cells",
            "edges",
            "faces",
            "shells",
            "solids",
            "vertices",
            "voids",
            "wires",
        },
    ),
    (
        MEASURE,
        {
            "bbox",
            "bends",
            "center",
            "check",
            "classify",
            "closest_point",
            "closest_points",
            "contains",
            "distance_to",
            "draft_analysis",
            "fillet_preview",
            "flat_pattern",
            "info",
            "intersection_curves",
            "is_valid",
            "mass_properties",
            "outline",
            "parting_line",
            "project",
            "raycast",
            "raycast_many",
            "silhouette",
            "slices",
        },
    ),
    (SERVICE, {"export", "from_mesh", "mesh", "show", "to_nurbs"}),
    (NA, {"colored", "compact", "named"}),
    (DEFER, {"deform", "flatten", "moved", "push", "warp"}),
    (ADAPTER, {"on"}),
)

_SKETCH: dict[str, str] = _table(
    (
        GEN,
        {
            "chamfer",
            "cut",
            "extend",
            "extrude",
            "fillet",
            "flipped",
            "fuse",
            "heal",
            "intersect",
            "match_edge",
            "merge_faces",
            "mirror",
            "offset",
            "revolve",
            "rotate",
            "scale",
            "sweep",
            "swing",
            "thicken",
            "translate",
            "xor",
        },
    ),
    (REF, {"edges", "faces", "vertices", "wires"}),
    (
        MEASURE,
        {
            "bbox",
            "center",
            "check",
            "closest_point",
            "closest_points",
            "distance_to",
            "info",
            "intersection_curves",
            "outline",
            "project",
            "raycast",
            "raycast_many",
            "section_properties",
            "silhouette",
        },
    ),
    (SERVICE, {"export", "mesh", "show", "to_nurbs"}),
    (NA, {"colored", "compact", "named"}),
    (DEFER, {"flatten", "from_nurbs", "moved", "push", "trim", "warp"}),
    (ADAPTER, {"on"}),
)

_PROFILE: dict[str, str] = _table(
    (
        NA,
        {
            "arc",
            "arc_to",
            "chamfer",
            "close",
            "fillet",
            "forward",
            "line_by",
            "line_to",
            "mirror",
            "turn",
            "turn_to",
            "wire",
        },
    ),
)

# ``first``/``last`` are properties on ShapeList (not callable), so they are
# not enumerated; refs.py reads them as REF selection properties.
_SHAPE_LIST: dict[str, str] = _table(
    (
        REF,
        {
            "at",
            "back",
            "bottom",
            "circles",
            "concave",
            "convex",
            "count",
            "cylinders",
            "derived_from",
            "edges",
            "facing",
            "faces",
            "fillets",
            "front",
            "g1",
            "g2",
            "group_by",
            "hit_by",
            "joining",
            "largest",
            "left",
            "lines",
            "max_by",
            "min_by",
            "nearest",
            "new",
            "of_type",
            "one",
            "parallel_to",
            "perpendicular_to",
            "planar",
            "right",
            "shared",
            "smallest",
            "smooth",
            "sort_by",
            "sort_by_distance",
            "tangent_chain",
            "top",
            "vertices",
            "wires",
        },
    ),
    (DEFER, {"filter", "filter_by", "within"}),
    (
        NA,
        {
            "append",
            "bbox",
            "center",
            "clear",
            "copy",
            "extend",
            "index",
            "insert",
            "moved",
            "on",
            "pop",
            "remove",
            "reverse",
            "rotate",
            "sort",
            "translate",
        },
    ),
)

_FACE: dict[str, str] = _table(
    (
        GEN,
        {
            "extend",
            "extrude",
            "flipped",
            "iso",
            "mirror",
            "offset",
            "project",
            "rotate",
            "scale",
            "split",
            "to_shell",
            "to_sketch",
            "translate",
            "untrimmed",
            "wrap",
        },
    ),
    (
        REF,
        {
            "edges",
            "faces",
            "inner_wires",
            "neighbors",
            "outer_wire",
            "vertices",
            "wires",
        },
    ),
    (
        MEASURE,
        {
            "bbox",
            "center",
            "closest_point",
            "curvature_at",
            "distance_to",
            "interior_point",
            "min_radius",
            "normal_at",
            "position_at",
            "raycast",
            "uv_at",
        },
    ),
    (SERVICE, {"export", "mesh", "show"}),
    (NA, {"nurbs"}),
    (ADAPTER, {"on"}),
    (DEFER, {"moved"}),
)

_SHAPE: dict[str, str] = _table(
    (GEN, {"mirror", "rotate", "scale", "translate"}),
    (REF, {"edges", "faces", "vertices", "wires"}),
    (MEASURE, {"bbox", "center"}),
    (SERVICE, {"export", "mesh", "show"}),
    (ADAPTER, {"on"}),
    (DEFER, {"moved"}),
)

_METHOD_TABLES: dict[str, dict[str, str]] = {
    "Part": _PART,
    "Sketch": _SKETCH,
    "Profile": _PROFILE,
    "ShapeList": _SHAPE_LIST,
    "Face": _FACE,
    "Shape": _SHAPE,
}

# Class-level defaults are used only for classes whose methods all share one
# destination; the six tables above are complete and must not fall back.
_CLASS_DEFAULTS: dict[str, tuple[str, str]] = {
    "Edge": (MEASURE, "edge topology/measurement query (Edge class default)"),
    "Wire": (MEASURE, "wire topology/measurement query (Wire class default)"),
    "Vertex": (MEASURE, "vertex measurement query (Vertex class default)"),
    "Shell": (MEASURE, "sheet topology/measurement query (Shell class default)"),
    "Mesh": (MEASURE, "tessellation measurement query (Mesh class default)"),
    "StepModel": (SERVICE, "STEP import model (service path)"),
    "KernelError": (NA, "error class"),
    "ModelingError": (NA, "error class"),
    "FontError": (NA, "error class"),
    "Plane": (NA, "geometry constant / builder"),
    "Axis": (NA, "geometry constant / builder"),
    "Vector": (NA, "geometry constant / builder"),
    "Location": (NA, "geometry constant / builder"),
    "Locations": (NA, "geometry constant / builder"),
    "BoundBox": (NA, "geometry constant / builder"),
    "Align": (NA, "geometry constant / builder"),
    "Lattice": (DEFER, "deformation lattice; deferred with deform"),
    "ClosestPoints": (MEASURE, "closest-points result"),
    "Continuity": (MEASURE, "continuity result"),
    "Curvature": (MEASURE, "curvature result"),
    "FitReport": (MEASURE, "curve-fit result"),
    "Hit": (MEASURE, "raycast result"),
    "MassProperties": (MEASURE, "mass-properties result"),
    "Problem": (MEASURE, "kernel validity result"),
    "RepairReport": (MEASURE, "repair result"),
    "StitchReport": (MEASURE, "stitch result"),
    "DrawingView": (SERVICE, "drawing view produced by the render service"),
    "Nurbs": (SERVICE, "NURBS data carrier (export path)"),
    "NurbsSurface": (SERVICE, "NURBS surface data carrier (export path)"),
    "Bend": (MEASURE, "bend analysis result"),
    "FlatPattern": (MEASURE, "flat-pattern result"),
    "SectionProperties": (MEASURE, "section-properties result"),
    "StepCurve": (SERVICE, "STEP import data"),
    "StepFrame": (SERVICE, "STEP import data"),
    "StepPoint": (SERVICE, "STEP import data"),
}

_METHOD_NOTES: dict[tuple[str, str], str] = {
    ("Part", "bends"): "sheet-metal bend report",
    ("Part", "check"): "kernel validity probe",
    ("Part", "classify"): "point-in-body query",
    ("Part", "colored"): "display metadata",
    ("Part", "compact"): "cache/memory management",
    ("Part", "draft_analysis"): "draft analysis report",
    ("Part", "from_mesh"): "mesh -> part conversion (import path)",
    (
        "Part",
        "moved",
    ): "takes a Location builder; placement goes through the place_on adapter",
    ("Part", "named"): "display/export metadata",
    ("Part", "on"): "placement adapter place_on",
    ("Part", "to_nurbs"): "NURBS representation conversion",
    ("Sketch", "from_nurbs"): "NURBS surface data; deferred with nurbs_surface",
    (
        "Sketch",
        "moved",
    ): "takes a Location builder; placement goes through the place_on adapter",
    ("Sketch", "on"): "placement adapter place_on",
    (
        "Face",
        "moved",
    ): "takes a Location builder; placement goes through the place_on adapter",
    (
        "Face",
        "nurbs",
    ): "NURBS data export; consumed by the service/export path, not a document action",
    ("Face", "on"): "placement adapter place_on",
    (
        "Shape",
        "moved",
    ): "takes a Location builder; placement goes through the place_on adapter",
    ("Shape", "on"): "placement adapter place_on",
    ("ShapeList", "bbox"): "measurement-only; the ShapeList split is 40 REF / 20 N/A",
    ("ShapeList", "center"): "measurement-only; the ShapeList split is 40 REF / 20 N/A",
    ("ShapeList", "derived_from"): "Ref.extra provenance helper",
    (
        "ShapeList",
        "filter",
    ): "callable/ambiguous criterion; refs.py rejects callables, so deferred",
    (
        "ShapeList",
        "filter_by",
    ): "callable/ambiguous criterion; refs.py rejects callables, so deferred",
    ("ShapeList", "g1"): "continuity selector",
    ("ShapeList", "g2"): "continuity selector",
    ("ShapeList", "group_by"): "selector grouping helper",
    ("ShapeList", "hit_by"): "spatial pick filter with vector arguments",
    ("ShapeList", "joining"): "Ref.extra relationship helper",
    ("ShapeList", "max_by"): "selector ranking helper",
    ("ShapeList", "min_by"): "selector ranking helper",
    ("ShapeList", "new"): "Ref.since builder (starts a selection chain)",
    ("ShapeList", "on"): "list placement; place_on consumes a single shape",
    ("ShapeList", "shared"): "Ref.extra relationship helper",
    ("ShapeList", "sort_by"): "selector ordering helper",
    ("ShapeList", "sort_by_distance"): "selector ordering helper",
    ("ShapeList", "tangent_chain"): "topology continuity selector",
    (
        "ShapeList",
        "within",
    ): "BoundBox argument is not a scalar/vector filter, so deferred",
}


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _public_classes() -> tuple[str, ...]:
    return tuple(
        sorted(
            name
            for name in dir(smlibpy)
            if _is_public(name) and inspect.isclass(getattr(smlibpy, name))
        )
    )


def _top_level_functions() -> tuple[str, ...]:
    return tuple(
        sorted(
            name
            for name in dir(smlibpy)
            if _is_public(name) and inspect.isfunction(getattr(smlibpy, name))
        )
    )


def _public_methods(owner: str) -> tuple[str, ...]:
    cls = getattr(smlibpy, owner)
    return tuple(
        sorted(
            name
            for name in dir(cls)
            if _is_public(name) and callable(getattr(cls, name))
        )
    )


def public_classes() -> list[str]:
    """Public ``smlibpy`` classes (41 for smlibpy 0.6.2)."""

    return list(_public_classes())


def top_level_functions() -> list[str]:
    """Public top-level functions (156 for smlibpy 0.6.2)."""

    return list(_top_level_functions())


def public_methods(owner: str) -> list[str]:
    """Sorted public callable method names of one public class."""

    return list(_public_methods(owner))


def kernel_version() -> str:
    return str(getattr(smlibpy, "__version__", "unknown"))


def _reason(owner: str, name: str, destination: str) -> str:
    note = _METHOD_NOTES.get((owner, name))
    if note is None and owner == "smlibpy":
        note = _TOP_LEVEL_NOTES.get(name)
    return note or _REASONS[destination]


def _record(
    owner: str,
    name: str,
    destination: str | None,
    reason: str | None = None,
) -> dict[str, Any]:
    if destination is None:
        return {
            "owner": owner,
            "name": name,
            "destination": None,
            "reason": "unclassified; add it to the destination tables",
        }
    return {
        "owner": owner,
        "name": name,
        "destination": destination,
        "reason": reason or _reason(owner, name, destination),
    }


def inventory() -> list[dict[str, Any]]:
    """Return one sorted record per public callable.

    Each record is ``{owner, name, destination, reason}``; ``owner`` is
    ``"smlibpy"`` for top-level functions and the class name for methods.
    """

    records: list[dict[str, Any]] = []
    for name in _top_level_functions():
        records.append(_record("smlibpy", name, _TOP_LEVEL.get(name)))
    for owner in _public_classes():
        table = _METHOD_TABLES.get(owner)
        default = _CLASS_DEFAULTS.get(owner)
        for name in _public_methods(owner):
            reason: str | None = None
            if table is not None:
                destination = table.get(name)
            elif default is not None:
                destination, reason = default
            else:
                destination = None
            records.append(_record(owner, name, destination, reason))
    records.sort(key=lambda record: (record["owner"], record["name"]))
    return records


def unclassified() -> list[dict[str, Any]]:
    """Every enumerated callable that lacks a destination."""

    return [record for record in inventory() if record["destination"] is None]


def stale_entries() -> list[dict[str, str]]:
    """Classification-table entries that the installed kernel does not expose.

    A stale entry is normally a typo (the real callable then shows up as
    unclassified instead), so this is a table-hygiene check.
    """

    actual = {("smlibpy", name) for name in _top_level_functions()}
    owners = _public_classes()
    for owner in owners:
        for name in _public_methods(owner):
            actual.add((owner, name))

    stale: list[dict[str, str]] = []
    for name in sorted(_TOP_LEVEL):
        if ("smlibpy", name) not in actual:
            stale.append(
                {"owner": "smlibpy", "name": name, "why": "not a top-level function"}
            )
    for owner, table in _METHOD_TABLES.items():
        for name in sorted(table):
            if (owner, name) not in actual:
                stale.append(
                    {"owner": owner, "name": name, "why": "not a method of this class"}
                )
    for owner in sorted(_CLASS_DEFAULTS):
        if owner not in owners:
            stale.append(
                {
                    "owner": owner,
                    "name": "<class>",
                    "why": "class default for a missing class",
                }
            )
    return stale


def destination_counts(
    records: Iterable[dict[str, Any]] | None = None,
) -> dict[str, int]:
    """Counts per destination (including ``None`` for unclassified)."""

    counts = {destination: 0 for destination in DESTINATIONS}
    counts["unclassified"] = 0
    for record in inventory() if records is None else records:
        destination = record["destination"]
        counts["unclassified" if destination is None else destination] += 1
    return counts


def check() -> int:
    """Print destination counts, report unclassified callables, return status."""

    records = inventory()
    counts = destination_counts(records)
    for destination in DESTINATIONS:
        print(f"  {destination:<10} {counts[destination]}")
    print(f"  {'total':<10} {len(records)}")

    stale = stale_entries()
    if stale:
        print(f"warning: {len(stale)} stale table entr(ies):")
        for entry in stale:
            print(f"  {entry['owner']}.{entry['name']} ({entry['why']})")

    missing = [record for record in records if record["destination"] is None]
    if missing:
        print(f"{len(missing)} unclassified callable(s):")
        for record in missing:
            print(f"  {record['owner']}.{record['name']}")
        return 1

    print(
        f"0 unclassified ({len(records)} callables, {len(_public_classes())} classes)"
    )
    return 0


def render_markdown(records: Iterable[dict[str, Any]] | None = None) -> str:
    """Render the inventory as markdown."""

    rows = inventory() if records is None else list(records)
    counts = destination_counts(rows)
    lines = [
        "# smlibpy kernel inventory",
        "",
        "Generated by `python scripts/kernel_inventory.py --write`; do not edit by hand.",
        "",
        f"- smlibpy: `{kernel_version()}`",
        f"- schema: `{SCHEMA_VERSION}`",
        f"- public classes: {len(_public_classes())}",
        f"- public callables: {len(rows)}",
        f"- unclassified: {counts['unclassified']}",
        "",
        "## Counts per destination",
        "",
        "| Destination | Count |",
        "|---|---:|",
    ]
    for destination in DESTINATIONS:
        lines.append(f"| {destination} | {counts[destination]} |")
    lines.append(f"| unclassified | {counts['unclassified']} |")
    lines.extend(
        [
            "",
            "## Callables",
            "",
            "| Owner | Name | Destination | Reason |",
            "|---|---|---|---|",
        ]
    )
    for record in rows:
        destination = record["destination"] or "unclassified"
        lines.append(
            f"| {record['owner']} | `{record['name']}` | {destination} | {record['reason']} |"
        )
    return "\n".join(lines) + "\n"


def baseline_document() -> dict[str, Any]:
    """The generated ``kernel_actions.baseline.json`` payload."""

    return {
        "schema_version": SCHEMA_VERSION,
        "smlibpy_version": kernel_version(),
        "records": inventory(),
    }


def baseline_json() -> str:
    """Canonical, byte-stable baseline JSON."""

    return (
        json.dumps(
            baseline_document(),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cadwork.design.kernel_inventory",
        description="Check the smlibpy kernel inventory for unclassified callables.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when any public callable is unclassified",
    )
    args = parser.parse_args(argv)
    if not args.check:
        parser.print_help()
        return 2
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
