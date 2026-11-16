"""Project a built part into the JSON the viewport consumes."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from cadwork.design.assembly import transform_to_json
from cadwork.design.assembly_build import AssemblyBuildResult
from cadwork.design.build import BuildCache, build
from cadwork.design.document import Document, canonical_json

_EDGE_SAMPLES = 12


def display_feature(document: Document) -> str | None:
    """The body the viewport shows: last solid feature, skipping fluid domains."""
    for feature in reversed(document.features):
        if feature.enabled and feature.type not in {"cavity_extraction", "cavity"}:
            return feature.id
    for feature in reversed(document.features):
        if feature.enabled:
            return feature.id
    return None


def _vec(value: Any) -> list[float]:
    return [float(value[0]), float(value[1]), float(value[2])]


def _edge_length(edge: Any) -> float:
    """Exact edge length; a straight edge needs no curve integration."""
    if edge.geom_type == "line":
        return float((edge.end - edge.start).length)
    return float(edge.length)


def _edge_points(edge: Any) -> list[list[float]]:
    """Polyline of an edge sampled in its own parameter space.

    ``point_at`` maps an arc-length fraction to a curve parameter, which costs a numeric
    inverse per sample; the viewport and edge picking only need a polyline, so uniform
    parameters are enough. A straight edge needs its two endpoints only: they describe it
    exactly, and the parameter range is linear there.

    Samples run start to end in the edge's displayed direction. Parameter spacing is not
    arc-length spacing on non-uniform curves, so the polyline is a display/picking input,
    never a measurement.
    """
    try:
        curve = edge._curve()
        t0, t1 = edge._range()
    except AttributeError:  # an older kernel: fall back to arc-length fractions
        return [
            _vec(edge.point_at(index / _EDGE_SAMPLES))
            for index in range(_EDGE_SAMPLES + 1)
        ]
    if getattr(edge, "_rev", False):
        first, last = t1, t0
    else:
        first, last = t0, t1
    if edge.geom_type == "line":
        return [_vec(curve.evaluate(first)), _vec(curve.evaluate(last))]
    step = (last - first) / _EDGE_SAMPLES
    return [
        _vec(curve.evaluate(first + step * index)) for index in range(_EDGE_SAMPLES + 1)
    ]


def _edge_entries(edges: Iterator[Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for index, edge in enumerate(edges):
        try:
            # The length is measured once per edge; every later use must read this value,
            # because the kernel computes it by integrating the curve.
            length = _edge_length(edge)
            entries.append(
                {"index": index, "length": length, "points": _edge_points(edge)}
            )
        except Exception:  # a degenerate edge is skipped
            continue
    return entries


def build_scene(
    part: Any, feature_id: str, bodies: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    faces: list[dict[str, Any]] = []
    for index, face in enumerate(part.faces() if hasattr(part, "faces") else []):
        try:
            mesh = face.mesh()
            center = face.center()
            normal = face.normal_at(center)
            faces.append(
                {
                    "index": index,
                    "area": float(face.area),
                    "center": _vec(center),
                    "normal": _vec(normal),
                    "vertices": mesh.vertices.tolist(),
                    "triangles": [
                        int(item) for item in mesh.triangles.reshape(-1).tolist()
                    ],
                }
            )
        except Exception:  # a face that cannot be tessellated is skipped
            continue

    edges = _edge_entries(part.edges() if hasattr(part, "edges") else [])

    return {
        "feature": feature_id,
        "faces": faces,
        "edges": edges,
        "bodies": list(bodies or []),
        "metrics": {
            "volume": float(part.volume),
            "faces": len(faces),
            "edges": len(edges),
        },
    }


def build_assembly_scene(
    result: AssemblyBuildResult, source: Any, cache: BuildCache
) -> dict[str, Any]:
    """Project placed instances once per definition; the viewport applies placements.

    A definition is keyed by its pinned document version and configuration, so
    repeated instances share one local mesh instead of duplicating geometry.
    """
    definitions: dict[str, dict[str, Any]] = {}
    instances: list[dict[str, Any]] = []
    for node in result.instances:
        entry: dict[str, Any] = {
            "path": node.path,
            "instance_id": node.instance_id,
            "definition_id": node.definition_id,
            "definition_kind": node.definition_kind,
            "version": node.version,
            "configuration": node.configuration,
            "placement": transform_to_json(node.placement),
            "local_placement": transform_to_json(node.local_placement),
            "name": node.name,
            "suppressed": node.suppressed,
            "visible": node.visible,
            "error": None
            if node.ok
            else {
                "code": node.error_code,
                "message": node.error_message,
            },
        }
        if node.part is not None:
            configuration = node.configuration or "default"
            override_key = canonical_json(dict(node.overrides))
            key = f"{node.definition_id}@{node.version}#{configuration}#{override_key}"
            entry["definition_key"] = key
            if key not in definitions:
                try:
                    if not result.placed and node.part is not None:
                        part = node.part
                    else:
                        document = source.get_version(node.definition_id, node.version)
                        part_result = build(
                            document,
                            cache,
                            configuration=configuration,
                            overrides=node.overrides,
                        )
                        if part_result.final is None:
                            raise ValueError("part has no final geometry")
                        part = part_result.final
                    definitions[key] = {
                        "definition_id": node.definition_id,
                        "version": node.version,
                        "configuration": configuration,
                        "overrides": dict(node.overrides),
                        **build_scene(part, key),
                    }
                except Exception as exc:
                    entry["error"] = {"code": "DEFINITION_FAILED", "message": str(exc)}
            entry["metrics"] = definitions.get(key, {}).get("metrics")
        instances.append(entry)
    bbox = None
    if result.bbox_min is not None and result.bbox_max is not None:
        bbox = {"min": list(result.bbox_min), "max": list(result.bbox_max)}
    return {
        "assembly": result.document_id,
        "version": result.version,
        "definitions": definitions,
        "instances": instances,
        "bom": [entry.summary() for entry in result.bom],
        "bbox": bbox,
        "metrics": {
            "definitions": len(definitions),
            "instances": len(instances),
            "parts": sum(1 for node in result.instances if node.part is not None),
            "failures": len(result.failures),
        },
    }
