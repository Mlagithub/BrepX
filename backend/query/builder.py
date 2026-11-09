"""Read-only query snapshot models and builder for geometric states supporting multi-body."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from backend.selector.canonicalizer import canonicalize_edge, canonicalize_face


@dataclass(frozen=True)
class FaceInfo:
    selector: str
    geom_type: str
    area: float
    normal: list[float]
    center: list[float]
    is_planar: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EdgeInfo:
    selector: str
    geom_type: str
    length: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BodyInfo:
    volume: float
    area: float
    bbox: list[float]
    is_valid: bool
    face_count: int
    edge_count: int
    faces: list[FaceInfo]
    edges: list[EdgeInfo]
    body_id: str = "body_1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_single_part_body(part: Any, body_id: str = "body_1", selector_prefix: str = "") -> BodyInfo:
    if part is None:
        return BodyInfo(
            volume=0.0,
            area=0.0,
            bbox=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            is_valid=False,
            face_count=0,
            edge_count=0,
            faces=[],
            edges=[],
            body_id=body_id,
        )

    vol = round(float(getattr(part, "volume", 0.0)), 4)
    total_area = round(float(getattr(part, "area", 0.0)), 4)

    bb = getattr(part, "bbox")() if hasattr(part, "bbox") else None
    if bb is not None and hasattr(bb, "min") and hasattr(bb, "max"):
        bbox_coords = [
            round(float(bb.min[0]), 4),
            round(float(bb.min[1]), 4),
            round(float(bb.min[2]), 4),
            round(float(bb.max[0]), 4),
            round(float(bb.max[1]), 4),
            round(float(bb.max[2]), 4),
        ]
    else:
        bbox_coords = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    valid_fn = getattr(part, "is_valid", lambda: False)
    valid = bool(valid_fn())

    faces_list = list(getattr(part, "faces")()) if hasattr(part, "faces") else []
    edges_list = list(getattr(part, "edges")()) if hasattr(part, "edges") else []

    face_infos: list[FaceInfo] = []
    for face in faces_list:
        raw_sel = canonicalize_face(face, part)
        selector = f"{selector_prefix}{raw_sel}" if selector_prefix else raw_sel
        geom_type = str(getattr(face, "geom_type", "unknown"))
        f_area = round(float(getattr(face, "area", 0.0)), 4)

        if hasattr(face, "normal_at") and callable(face.normal_at):
            try:
                norm_v = face.normal_at()
                norm = [round(float(norm_v[0]), 4), round(float(norm_v[1]), 4), round(float(norm_v[2]), 4)]
            except Exception:
                norm = [0.0, 0.0, 1.0]
        else:
            norm = [0.0, 0.0, 1.0]

        if hasattr(face, "center") and callable(face.center):
            c_v = face.center()
            center = [round(float(c_v.x), 4), round(float(c_v.y), 4), round(float(c_v.z), 4)]
        else:
            center = [0.0, 0.0, 0.0]

        is_planar = bool(getattr(face, "is_planar", False))

        face_infos.append(
            FaceInfo(
                selector=selector,
                geom_type=geom_type,
                area=f_area,
                normal=norm,
                center=center,
                is_planar=is_planar,
            )
        )

    edge_infos: list[EdgeInfo] = []
    for edge in edges_list:
        raw_sel = canonicalize_edge(edge, part)
        selector = f"{selector_prefix}{raw_sel}" if selector_prefix else raw_sel
        geom_type = str(getattr(edge, "geom_type", "unknown"))
        length = round(float(getattr(edge, "length", 0.0)), 4)
        edge_infos.append(
            EdgeInfo(
                selector=selector,
                geom_type=geom_type,
                length=length,
            )
        )

    return BodyInfo(
        volume=vol,
        area=total_area,
        bbox=bbox_coords,
        is_valid=valid,
        face_count=len(face_infos),
        edge_count=len(edge_infos),
        faces=face_infos,
        edges=edge_infos,
        body_id=body_id,
    )


def build_body(target: Any) -> BodyInfo:
    if target is None:
        return build_single_part_body(None)

    if hasattr(target, "bodies") and isinstance(target.bodies, dict):
        if not target.bodies:
            return build_single_part_body(None)

        if len(target.bodies) == 1:
            bid, p = next(iter(target.bodies.items()))
            return build_single_part_body(p, body_id=bid)

        tot_vol = 0.0
        tot_area = 0.0
        all_faces: list[FaceInfo] = []
        all_edges: list[EdgeInfo] = []
        is_valid = True
        min_x = min_y = min_z = float("inf")
        max_x = max_y = max_z = float("-inf")

        for bid, part in target.bodies.items():
            if part is None:
                continue
            b_info = build_single_part_body(part, body_id=bid, selector_prefix=f"bodies['{bid}'].")
            tot_vol += b_info.volume
            tot_area += b_info.area
            all_faces.extend(b_info.faces)
            all_edges.extend(b_info.edges)
            if not b_info.is_valid:
                is_valid = False
            if b_info.bbox != [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]:
                min_x = min(min_x, b_info.bbox[0])
                min_y = min(min_y, b_info.bbox[1])
                min_z = min(min_z, b_info.bbox[2])
                max_x = max(max_x, b_info.bbox[3])
                max_y = max(max_y, b_info.bbox[4])
                max_z = max(max_z, b_info.bbox[5])

        if min_x == float("inf"):
            bbox_coords = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        else:
            bbox_coords = [min_x, min_y, min_z, max_x, max_y, max_z]

        return BodyInfo(
            volume=round(tot_vol, 4),
            area=round(tot_area, 4),
            bbox=bbox_coords,
            is_valid=is_valid,
            face_count=len(all_faces),
            edge_count=len(all_edges),
            faces=all_faces,
            edges=all_edges,
            body_id="multi_bodies",
        )

    return build_single_part_body(target)
