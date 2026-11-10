"""Project a built part into the JSON the viewport consumes."""

from __future__ import annotations

from typing import Any

from cadwork.design.document import Document

_EDGE_SAMPLES = 12


def display_feature(document: Document) -> str | None:
    """The body the viewport shows: last solid feature, skipping fluid domains."""
    for feature in reversed(document.features):
        if feature.enabled and feature.type != "cavity_extraction":
            return feature.id
    for feature in reversed(document.features):
        if feature.enabled:
            return feature.id
    return None


def _vec(value: Any) -> list[float]:
    return [float(value[0]), float(value[1]), float(value[2])]


def build_scene(part: Any, feature_id: str) -> dict[str, Any]:
    faces: list[dict[str, Any]] = []
    for index, face in enumerate(part.faces() if hasattr(part, "faces") else []):
        try:
            mesh = face.mesh()
            center = face.center()
            normal = face.normal_at(center)
            faces.append({
                "index": index,
                "area": float(face.area),
                "center": _vec(center),
                "normal": _vec(normal),
                "vertices": mesh.vertices.tolist(),
                "triangles": [int(item) for item in mesh.triangles.reshape(-1).tolist()],
            })
        except Exception:  # a face that cannot be tessellated is skipped
            continue

    edges: list[dict[str, Any]] = []
    for index, edge in enumerate(part.edges() if hasattr(part, "edges") else []):
        try:
            points = [_vec(edge.point_at(i / _EDGE_SAMPLES)) for i in range(_EDGE_SAMPLES + 1)]
            edges.append({"index": index, "length": float(edge.length), "points": points})
        except Exception:  # a degenerate edge is skipped
            continue

    return {
        "feature": feature_id,
        "faces": faces,
        "edges": edges,
        "metrics": {"volume": float(part.volume), "faces": len(faces), "edges": len(edges)},
    }
