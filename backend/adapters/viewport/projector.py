"""Viewport projection generator for B-Rep meshes and boundary curves across multiple bodies."""

from __future__ import annotations

from typing import Any

from backend.selector.canonicalizer import canonicalize_edge, canonicalize_face


def project_faces(part: Any, body_prefix: str = "") -> list[dict[str, Any]]:
    if part is None:
        return []

    faces_list = list(getattr(part, "faces")()) if hasattr(part, "faces") else []
    projected: list[dict[str, Any]] = []

    for face in faces_list:
        try:
            raw_selector = canonicalize_face(face, part)
            selector = f"{body_prefix}{raw_selector}" if body_prefix else raw_selector
        except Exception as exc:
            selector = f"faces().error({exc})"

        geom_type = str(getattr(face, "geom_type", "unknown"))
        area = round(float(getattr(face, "area", 0.0)), 4)

        if hasattr(face, "normal_at") and callable(face.normal_at):
            try:
                norm_v = face.normal_at()
                normal = [round(float(norm_v[0]), 4), round(float(norm_v[1]), 4), round(float(norm_v[2]), 4)]
            except Exception:
                normal = [0.0, 0.0, 1.0]
        else:
            normal = [0.0, 0.0, 1.0]

        if hasattr(face, "center") and callable(face.center):
            c_v = face.center()
            center = [round(float(c_v.x), 4), round(float(c_v.y), 4), round(float(c_v.z), 4)]
        else:
            center = [0.0, 0.0, 0.0]

        try:
            mesh = face.mesh()
            raw_verts = mesh.vertices
            raw_indices = mesh.triangles

            vertices_flat: list[float] = []
            for v in raw_verts:
                vertices_flat.extend([round(float(v[0]), 5), round(float(v[1]), 5), round(float(v[2]), 5)])

            indices_flat: list[int] = []
            for tri in raw_indices:
                indices_flat.extend([int(tri[0]), int(tri[1]), int(tri[2])])

            projected.append({
                "selector": selector,
                "geom_type": geom_type,
                "area": area,
                "normal": normal,
                "center": center,
                "vertices": vertices_flat,
                "indices": indices_flat,
            })
        except Exception as exc:
            projected.append({
                "selector": selector,
                "error": str(exc),
            })

    return projected


def project_edges(part: Any, body_prefix: str = "") -> list[dict[str, Any]]:
    if part is None:
        return []

    edges_list = list(getattr(part, "edges")()) if hasattr(part, "edges") else []
    projected: list[dict[str, Any]] = []

    for edge in edges_list:
        if getattr(edge, "is_seam", False):
            continue

        try:
            raw_selector = canonicalize_edge(edge, part)
            selector = f"{body_prefix}{raw_selector}" if body_prefix else raw_selector
        except Exception as exc:
            selector = f"edges().error({exc})"

        geom_type = str(getattr(edge, "geom_type", "unknown"))
        length = round(float(getattr(edge, "length", 0.0)), 4)

        points: list[list[float]] = []
        if geom_type == "line":
            start_v = edge.start
            end_v = edge.end
            points = [
                [round(float(start_v[0]), 5), round(float(start_v[1]), 5), round(float(start_v[2]), 5)],
                [round(float(end_v[0]), 5), round(float(end_v[1]), 5), round(float(end_v[2]), 5)],
            ]
        else:
            num_samples = 24 if getattr(edge, "is_closed", False) else 16
            for step in range(num_samples + 1):
                t = step / float(num_samples)
                try:
                    pt = edge.point_at(t)
                    points.append([round(float(pt[0]), 5), round(float(pt[1]), 5), round(float(pt[2]), 5)])
                except Exception:
                    break

        projected.append({
            "selector": selector,
            "geom_type": geom_type,
            "length": length,
            "points": points,
        })

    return projected


def project_scene(target: Any) -> dict[str, Any]:
    if target is None:
        return {"bodies": []}

    if hasattr(target, "bodies") and isinstance(target.bodies, dict):
        bodies_list: list[dict[str, Any]] = []
        for body_id, part in target.bodies.items():
            if part is None:
                continue
            prefix = f"bodies['{body_id}']." if len(target.bodies) > 1 else ""
            faces_data = project_faces(part, prefix)
            edges_data = project_edges(part, prefix)
            bodies_list.append({
                "body_id": body_id,
                "faces": faces_data,
                "edges": edges_data,
            })
        return {"bodies": bodies_list}

    faces_data = project_faces(target)
    edges_data = project_edges(target)

    return {
        "bodies": [
            {
                "body_id": "body_1",
                "faces": faces_data,
                "edges": edges_data,
            }
        ]
    }
