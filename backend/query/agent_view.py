"""Agent observation snapshot view builder and token estimation."""

from __future__ import annotations

import json
from typing import Any, Sequence

from backend.core.design import Design
from backend.query.builder import build_body
from backend.selector.errors import SelectorResolutionError
from backend.selector.resolver import SelectorResolver

MAX_FACES_IN_VIEW = 40
MAX_EDGES_IN_VIEW = 40


def estimate_tokens(view_dict: dict[str, Any]) -> int:
    serialized = json.dumps(view_dict, ensure_ascii=False)
    return len(serialized) // 3


def build_agent_view(design: Design, selections: Sequence[str] | None = None) -> dict[str, Any]:
    part = design.geometry
    body_info = build_body(part)

    active_selections = list(selections) if selections is not None else []
    selection_facts: list[dict[str, Any]] = []

    if part is not None and active_selections:
        for expr in active_selections:
            try:
                handle = SelectorResolver.resolve(part, expr)
                is_face = hasattr(handle, "normal_at") or hasattr(handle, "area")
                if is_face:
                    norm = [0.0, 0.0, 1.0]
                    if hasattr(handle, "normal_at") and callable(handle.normal_at):
                        try:
                            n = handle.normal_at()
                            norm = [round(float(n[0]), 4), round(float(n[1]), 4), round(float(n[2]), 4)]
                        except Exception:
                            norm = [0.0, 0.0, 1.0]
                    c = [0.0, 0.0, 0.0]
                    if hasattr(handle, "center") and callable(handle.center):
                        cv = handle.center()
                        c = [round(float(cv.x), 4), round(float(cv.y), 4), round(float(cv.z), 4)]

                    selection_facts.append({
                        "selector": expr,
                        "entity_type": "face",
                        "geom_type": str(getattr(handle, "geom_type", "unknown")),
                        "area": round(float(getattr(handle, "area", 0.0)), 4),
                        "normal": norm,
                        "center": c,
                        "is_planar": bool(getattr(handle, "is_planar", False)),
                    })
                else:
                    length = round(float(getattr(handle, "length", 0.0)), 4)
                    selection_facts.append({
                        "selector": expr,
                        "entity_type": "edge",
                        "geom_type": str(getattr(handle, "geom_type", "unknown")),
                        "length": length,
                    })
            except SelectorResolutionError:
                selection_facts.append({
                    "selector": expr,
                    "error": "ResolutionFailed",
                })

    faces_data = body_info.faces
    truncated_faces = False
    omitted_faces_count = 0
    if len(faces_data) > MAX_FACES_IN_VIEW:
        truncated_faces = True
        omitted_faces_count = len(faces_data) - MAX_FACES_IN_VIEW
        sorted_faces = sorted(faces_data, key=lambda f: f.area, reverse=True)
        retained_faces = sorted_faces[:MAX_FACES_IN_VIEW]
    else:
        retained_faces = faces_data

    edges_data = body_info.edges
    truncated_edges = False
    omitted_edges_count = 0
    if len(edges_data) > MAX_EDGES_IN_VIEW:
        truncated_edges = True
        omitted_edges_count = len(edges_data) - MAX_EDGES_IN_VIEW
        sorted_edges = sorted(edges_data, key=lambda e: e.length, reverse=True)
        retained_edges = sorted_edges[:MAX_EDGES_IN_VIEW]
    else:
        retained_edges = edges_data

    return {
        "version": design.version,
        "summary": {
            "volume": body_info.volume,
            "area": body_info.area,
            "bbox": body_info.bbox,
            "is_valid": body_info.is_valid,
            "face_count": body_info.face_count,
            "edge_count": body_info.edge_count,
        },
        "selections": selection_facts,
        "faces": [f.to_dict() for f in retained_faces],
        "edges": [e.to_dict() for e in retained_edges],
        "truncated": truncated_faces or truncated_edges,
        "omitted_faces_count": omitted_faces_count,
        "omitted_edges_count": omitted_edges_count,
    }
