"""B-Rep topological graphic serializer for SMLib Studio Next.

Serializes SMLib Part, Shell, Sketch, Wire, and Edge objects into structured
B-Rep graphic containers with independent per-face meshes (face_index),
per-edge polylines (edge_index), per-vertex points (vertex_index), and
analytic geometric metadata.
"""

from __future__ import annotations

from typing import Any
import numpy as np
import smlibpy
from smlibpy import Edge, Face, Mesh, Part, Shape, ShapeList, Shell, Sketch, StepModel, Wire
from smlibpy._kernel import ext, k
from smlibpy.mesh import face_meshes, tessellate


def _round_val(val: float, scale: float = 1.0) -> float:
    val = float(val)
    if abs(val) < 1e-9 * scale:
        return 0.0
    return round(val, 4)


def _flat_list(arr: Any, digits: int = 4) -> list[float]:
    return [round(float(x), digits) for x in np.asarray(arr, dtype=float).ravel()]


def _shape_scale(shape: Any) -> float:
    try:
        bb = shape.bbox()
        return max(1.0, float(bb.diagonal))
    except Exception:
        return 1.0


def _vertex_normals(v: np.ndarray, tri: np.ndarray) -> np.ndarray:
    n = np.zeros_like(v)
    t = tri.reshape(-1, 3)
    if len(t):
        fn = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
        for i in range(3):
            np.add.at(n, t[:, i], fn)
    norm = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.where(norm > 0, norm, 1.0)


def extract_face_metadata(face: Face, face_idx: int, body_expr: str, scale: float) -> dict[str, Any]:
    """Extract analytic surface properties (type, area, center, normal, radius) for a B-Rep Face."""
    meta: dict[str, Any] = {
        "face_index": face_idx,
        "expr": f"{body_expr}.faces()[{face_idx}]",
        "geom_type": getattr(face, "geom_type", "nurbs"),
        "is_planar": bool(getattr(face, "is_planar", False)),
        "area": _round_val(getattr(face, "area", 0.0)),
        "center": [0.0, 0.0, 0.0],
        "normal": [0.0, 0.0, 1.0],
        "radius": None,
    }
    try:
        c = face.center().to_tuple()
        meta["center"] = [_round_val(x, scale) for x in c]
    except Exception:
        pass
    try:
        n = face.normal_at().to_tuple()
        meta["normal"] = [_round_val(x, 1.0) for x in n]
    except Exception:
        pass
    try:
        if meta["geom_type"] in ("cylinder", "cone", "sphere", "torus"):
            r = getattr(face, "radius", None)
            if r is not None:
                meta["radius"] = _round_val(r)
            if hasattr(face, "axis") and face.axis is not None:
                meta["axis_origin"] = [_round_val(x, scale) for x in face.axis.origin.to_tuple()]
                meta["axis_dir"] = [_round_val(x, 1.0) for x in face.axis.direction.to_tuple()]
    except Exception:
        pass
    return meta


def extract_edge_metadata(edge: Edge, edge_idx: int, body_expr: str, scale: float) -> dict[str, Any]:
    """Extract analytic curve properties (type, length, center, radius, endpoints) for a B-Rep Edge."""
    meta: dict[str, Any] = {
        "edge_index": edge_idx,
        "expr": f"{body_expr}.edges()[{edge_idx}]",
        "geom_type": getattr(edge, "geom_type", "bspline"),
        "length": _round_val(getattr(edge, "length", 0.0)),
        "center": [0.0, 0.0, 0.0],
        "radius": None,
        "is_convex": getattr(edge, "is_convex", None),
    }
    try:
        c = edge.center().to_tuple()
        meta["center"] = [_round_val(x, scale) for x in c]
    except Exception:
        pass
    try:
        if meta["geom_type"] == "circle":
            r = getattr(edge, "radius", None)
            if r is not None:
                meta["radius"] = _round_val(r)
    except Exception:
        pass
    try:
        meta["start"] = [_round_val(x, scale) for x in edge.start().to_tuple()]
        meta["end"] = [_round_val(x, scale) for x in edge.end().to_tuple()]
    except Exception:
        pass
    return meta


def serialize_body(name: str, expr: str, shape: Any) -> dict[str, Any]:
    """Serialize a single SMLib Shape (Part, Shell, Sketch, Wire, Edge) into a B-Rep container."""
    scale = _shape_scale(shape)
    bb = shape.bbox()
    bbox_info = {
        "min": [_round_val(c, scale) for c in bb.min.to_tuple()],
        "max": [_round_val(c, scale) for c in bb.max.to_tuple()],
        "size": [_round_val(c, scale) for c in bb.size.to_tuple()],
        "center": [_round_val(c, scale) for c in bb.center.to_tuple()],
    }

    faces_out: list[dict[str, Any]] = []
    edges_out: list[dict[str, Any]] = []
    vertices_out: list[dict[str, Any]] = []

    # 1. Vertices
    try:
        verts = list(shape.vertices())
        for v_idx, v in enumerate(verts):
            pt = v.center().to_tuple()
            vertices_out.append({
                "vertex_index": v_idx,
                "expr": f"{expr}.vertices()[{v_idx}]",
                "position": [_round_val(c, scale) for c in pt],
            })
    except Exception:
        verts = []

    # 2. Curve-only shapes (Wire / Edge) or 2D Sketches without faces
    has_faces = hasattr(shape, "faces") and len(list(shape.faces())) > 0
    if isinstance(shape, (Edge, Wire)) or (isinstance(shape, Sketch) and not has_faces):
        from smlibpy.exporters import _curve_points

        curves = list(shape.edges())
        for n, (e, pts) in enumerate(zip(curves, _curve_points(shape))):
            e_meta = extract_edge_metadata(e, n, expr, scale)
            e_meta["points"] = _flat_list(pts, 4)
            edges_out.append(e_meta)
    else:
        # 3. Solid / Shell / Face-backed Sketch
        actual_shape = shape.to_shell() if isinstance(shape, Face) else shape
        tol = max(bb.diagonal, 1e-6) * 1e-3

        # Extract non-seam edges using kernel boundary tessellation
        try:
            every_edge = list(actual_shape.edges(seams=True))
            seam_set = set(ext.seam_edges(actual_shape._brep))
            named_edges = list(actual_shape.edges())
            shown_map = {e._identity(): idx for idx, e in enumerate(named_edges)}
            flat_pts, counts, _ = k.tessellate_boundaries(actual_shape._brep, angle_tolerance_deg=5.0)
            pts_arr = np.asarray(flat_pts, dtype=np.float64).reshape(-1, 3)

            offset = 0
            for raw_idx, (e, cnt) in enumerate(zip(every_edge, counts)):
                polyline = pts_arr[offset:offset + cnt]
                offset += cnt
                if raw_idx in seam_set or cnt < 2 or e._identity() not in shown_map:
                    continue
                edge_idx = shown_map[e._identity()]
                e_meta = extract_edge_metadata(named_edges[edge_idx], edge_idx, expr, scale)
                e_meta["points"] = _flat_list(polyline, 4)
                edges_out.append(e_meta)
            edges_out.sort(key=lambda item: item["edge_index"])
        except Exception:
            pass

        # Extract per-face meshes
        faces_list = list(actual_shape.faces())
        try:
            cut_meshes = face_meshes(actual_shape, tol, 12.0)
        except Exception:
            cut_meshes = None

        for j, f in enumerate(faces_list):
            try:
                m = cut_meshes[j] if cut_meshes is not None else tessellate(f, tol, 12.0)
            except Exception:
                continue
            if not len(m.triangles):
                continue
            v_arr = np.asarray(m.vertices, dtype=float)
            tri_arr = np.asarray(m.triangles).ravel()
            if m.normals is not None and len(tri_arr):
                n_arr = np.zeros_like(v_arr)
                n_arr[tri_arr] = np.asarray(m.normals, dtype=float).reshape(-1, 3)
            else:
                n_arr = _vertex_normals(v_arr, tri_arr)

            f_meta = extract_face_metadata(f, j, expr, scale)
            f_meta["vertices"] = _flat_list(v_arr, 4)
            f_meta["normals"] = _flat_list(n_arr, 4)
            f_meta["indices"] = [int(i) for i in tri_arr]
            faces_out.append(f_meta)

    kind = type(shape).__name__.lower()
    volume = _round_val(getattr(shape, "volume", 0.0)) if isinstance(shape, Part) else 0.0
    area = _round_val(getattr(shape, "area", 0.0)) if hasattr(shape, "area") else 0.0
    is_valid = bool(shape.is_valid()) if isinstance(shape, Part) else True

    return {
        "name": name,
        "expr": expr,
        "kind": kind,
        "is_valid": is_valid,
        "volume": volume,
        "area": area,
        "bbox": bbox_info,
        "faces_count": len(faces_out),
        "edges_count": len(edges_out),
        "vertices_count": len(vertices_out),
        "faces": faces_out,
        "edges": edges_out,
        "vertices": vertices_out,
    }


def serialize_scene(items: list[tuple[str, str, Any]]) -> dict[str, Any]:
    """Serialize a list of (name, expr, shape) workspace items into a complete B-Rep scene."""
    bodies: list[dict[str, Any]] = []
    total_vol = 0.0
    total_area = 0.0
    total_faces = 0
    total_edges = 0
    total_verts = 0
    total_triangles = 0

    for name, expr, shape in items:
        try:
            body_data = serialize_body(name, expr, shape)
            bodies.append(body_data)
            total_vol += body_data["volume"]
            total_area += body_data["area"]
            total_faces += body_data["faces_count"]
            total_edges += body_data["edges_count"]
            total_verts += body_data["vertices_count"]
            for f in body_data["faces"]:
                total_triangles += len(f["indices"]) // 3
        except Exception:
            continue

    return {
        "bodies": bodies,
        "summary": {
            "body_count": len(bodies),
            "volume": round(total_vol, 2),
            "area": round(total_area, 2),
            "faces_count": total_faces,
            "edges_count": total_edges,
            "vertices_count": total_verts,
            "triangles_count": total_triangles,
        },
    }
