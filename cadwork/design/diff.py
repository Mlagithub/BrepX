"""Cross-version geometry and face-fingerprint comparison."""

from __future__ import annotations

from typing import Any


def _face_signature(face: Any) -> tuple[float, float, float, float, float, float, float]:
    area = round(float(getattr(face, "area", 0.0)), 1)
    try:
        center = face.center()
        cx, cy, cz = round(float(center[0]), 1), round(float(center[1]), 1), round(float(center[2]), 1)
        normal = face.normal_at(center)
        nx, ny, nz = round(float(normal[0]), 2), round(float(normal[1]), 2), round(float(normal[2]), 2)
    except Exception:
        cx, cy, cz, nx, ny, nz = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    return (area, cx, cy, cz, nx, ny, nz)


def compare_parts(before_part: Any | None, after_part: Any | None) -> dict[str, Any]:
    """Compare two compiled parts and identify unchanged vs modified/new faces on the target."""
    before_faces = list(before_part.faces()) if (before_part is not None and hasattr(before_part, "faces")) else []
    after_faces = list(after_part.faces()) if (after_part is not None and hasattr(after_part, "faces")) else []

    before_sigs: dict[tuple[float, ...], int] = {}
    for face in before_faces:
        sig = _face_signature(face)
        before_sigs[sig] = before_sigs.get(sig, 0) + 1

    unchanged_indices: list[int] = []
    changed_indices: list[int] = []
    changed_centers: list[list[float]] = []

    for index, face in enumerate(after_faces):
        sig = _face_signature(face)
        if before_sigs.get(sig, 0) > 0:
            before_sigs[sig] -= 1
            unchanged_indices.append(index)
        else:
            changed_indices.append(index)
            changed_centers.append([sig[1], sig[2], sig[3]])

    vol_before = round(float(getattr(before_part, "volume", 0.0)), 2) if before_part is not None else 0.0
    vol_after = round(float(getattr(after_part, "volume", 0.0)), 2) if after_part is not None else 0.0
    area_before = round(sum(float(getattr(f, "area", 0.0)) for f in before_faces), 2)
    area_after = round(sum(float(getattr(f, "area", 0.0)) for f in after_faces), 2)

    return {
        "unchanged_face_indices": unchanged_indices,
        "changed_face_indices": changed_indices,
        "changed_face_centers": changed_centers,
        "metrics_delta": {
            "volume_before": vol_before,
            "volume_after": vol_after,
            "volume_delta": round(vol_after - vol_before, 2),
            "area_before": area_before,
            "area_after": area_after,
            "area_delta": round(area_after - area_before, 2),
            "faces_before": len(before_faces),
            "faces_after": len(after_faces),
            "faces_delta": len(after_faces) - len(before_faces),
        },
    }
