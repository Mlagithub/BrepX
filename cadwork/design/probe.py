"""Geometry, topology, reference, and spatial-pick probes over compiled parts."""

from __future__ import annotations

import math
from typing import Any, Mapping

from . import refs
from .build import BuildResult
from .document import Document, Ref, ref_from_json


def _vec3(value: Any) -> list[float]:
    return [round(float(value[0]), 4), round(float(value[1]), 4), round(float(value[2]), 4)]


def _dist(a: list[float] | tuple[float, ...], b: list[float] | tuple[float, ...]) -> float:
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def _display_feature_id(document: Document, result: BuildResult, feature_id: str | None = None) -> str | None:
    if feature_id:
        return feature_id
    for feature in reversed(document.features):
        if feature.enabled and feature.type != "cavity_extraction" and feature.id in result.outputs:
            return feature.id
    for feature in reversed(document.features):
        if feature.enabled and feature.id in result.outputs:
            return feature.id
    return None


def probe_geometry(
    document: Document,
    result: BuildResult,
    feature_id: str | None = None,
    max_faces: int = 12,
) -> dict[str, Any]:
    """Inspect exact bounding box, mass properties, and dominant faces of a built feature."""
    target_id = _display_feature_id(document, result, feature_id)
    if target_id is None or target_id not in result.outputs:
        return {
            "feature_id": target_id,
            "empty": True,
            "bbox": None,
            "mass": {"volume": 0.0, "area": 0.0, "solids": 0, "faces": 0, "edges": 0},
            "dominant_faces": [],
        }

    part = result.outputs[target_id]
    bbox_info = None
    if hasattr(part, "bbox"):
        box = part.bbox()
        low = _vec3(box.min)
        high = _vec3(box.max)
        size = _vec3(box.size)
        center = [round((low[i] + high[i]) / 2.0, 4) for i in range(3)]
        bbox_info = {"min": low, "max": high, "size": size, "center": center}

    faces_list = list(part.faces()) if hasattr(part, "faces") else []
    edges_list = list(part.edges()) if hasattr(part, "edges") else []
    solids_list = list(part.solids()) if hasattr(part, "solids") else []

    volume = round(float(getattr(part, "volume", 0.0)), 4)
    total_area = round(sum(float(getattr(f, "area", 0.0)) for f in faces_list), 4)

    face_records: list[dict[str, Any]] = []
    for index, face in enumerate(faces_list):
        try:
            center = _vec3(face.center())
            normal = _vec3(face.normal_at(face.center()))
            area = round(float(face.area), 4)
            surface_type = str(getattr(face, "surface_type", None) or getattr(face, "geom_type", "face"))
            face_records.append({
                "index": index,
                "area": area,
                "center": center,
                "normal": normal,
                "type": surface_type,
            })
        except Exception:
            continue

    dominant = sorted(face_records, key=lambda item: item["area"], reverse=True)[:max_faces]
    return {
        "feature_id": target_id,
        "empty": False,
        "bbox": bbox_info,
        "mass": {
            "volume": volume,
            "area": total_area,
            "solids": len(solids_list),
            "faces": len(faces_list),
            "edges": len(edges_list),
        },
        "dominant_faces": dominant,
    }


def probe_ref(
    result: BuildResult,
    ref_spec: Ref | Mapping[str, Any],
) -> dict[str, Any]:
    """Dry-run a semantic reference selector and return matched topology elements."""
    ref = ref_spec if isinstance(ref_spec, Ref) else ref_from_json(ref_spec)
    try:
        resolved = refs.resolve(ref, result.outputs)
    except refs.RefError as exc:
        return {
            "ok": False,
            "code": exc.code,
            "message": exc.message,
            "hint": exc.hint,
            "count": 0,
            "elements": [],
        }

    items = list(resolved) if hasattr(resolved, "__iter__") else [resolved]
    elements: list[dict[str, Any]] = []
    for index, item in enumerate(items[:24]):
        entry: dict[str, Any] = {"index": index}
        if hasattr(item, "area"):
            entry["area"] = round(float(item.area), 4)
        if hasattr(item, "length"):
            entry["length"] = round(float(item.length), 4)
        if hasattr(item, "center") and callable(item.center):
            try:
                c = item.center()
                entry["center"] = _vec3(c)
                if hasattr(item, "normal_at"):
                    entry["normal"] = _vec3(item.normal_at(c))
            except Exception:
                pass
        elif hasattr(item, "point_at") and callable(item.point_at):
            try:
                entry["center"] = _vec3(item.point_at(0.5))
            except Exception:
                pass
        elements.append(entry)

    return {
        "ok": True,
        "source": ref.source,
        "select": ref.select,
        "count": len(items),
        "elements": elements,
    }


def pick_to_ref(
    document: Document,
    result: BuildResult,
    point: list[float] | tuple[float, ...],
    normal: list[float] | tuple[float, ...] | None = None,
    area: float | None = None,
    feature_id: str | None = None,
) -> dict[str, Any]:
    """Map a 3D viewport pick coordinate to the closest B-Rep face and suggest a stable Ref."""
    target_id = _display_feature_id(document, result, feature_id)
    if target_id is None or target_id not in result.outputs:
        return {"ok": False, "message": "no built geometry available to pick"}

    part = result.outputs[target_id]
    faces_list = list(part.faces()) if hasattr(part, "faces") else []
    if not faces_list:
        return {"ok": False, "message": "target part has no faces"}

    pt = [float(point[0]), float(point[1]), float(point[2])]
    best_face = None
    best_score = float("inf")
    best_index = -1
    best_center: list[float] = pt
    best_normal: list[float] = [0.0, 0.0, 1.0]
    best_area = 0.0
    best_type = "face"

    for index, face in enumerate(faces_list):
        try:
            c = _vec3(face.center())
            n = _vec3(face.normal_at(face.center()))
            f_area = round(float(face.area), 4)
            f_type = str(getattr(face, "surface_type", None) or getattr(face, "geom_type", "face"))
            dist = _dist(pt, c)
            score = dist
            if area is not None and area > 0:
                rel_area = abs(f_area - float(area)) / max(float(area), 1.0)
                score += rel_area * 10.0
            if normal is not None and len(normal) == 3:
                dot = sum(float(normal[i]) * n[i] for i in range(3))
                score += (1.0 - max(-1.0, min(1.0, dot))) * 5.0
            if score < best_score:
                best_score = score
                best_face = face
                best_index = index
                best_center = c
                best_normal = n
                best_area = f_area
                best_type = f_type
        except Exception:
            continue

    if best_face is None:
        return {"ok": False, "message": "could not match picked point to any face"}

    suggested_ref = {
        "source": target_id,
        "select": "faces",
        "filters": [{"method": "nearest", "args": [best_center], "kwargs": {}}],
    }

    orientation = "angled"
    nx, ny, nz = best_normal
    if abs(nz) > 0.95:
        orientation = "top (+Z)" if nz > 0 else "bottom (-Z)"
    elif abs(nx) > 0.95:
        orientation = "right (+X)" if nx > 0 else "left (-X)"
    elif abs(ny) > 0.95:
        orientation = "back (+Y)" if ny > 0 else "front (-Y)"

    return {
        "ok": True,
        "feature_id": target_id,
        "face_index": best_index,
        "surface_type": best_type,
        "area": best_area,
        "center": best_center,
        "normal": best_normal,
        "orientation": orientation,
        "suggested_ref": suggested_ref,
        "tag": f"@Face#{best_index}({target_id}, {best_type}, {best_area:.1f}mm², {orientation})",
    }
