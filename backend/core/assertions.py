"""Physical postcondition assertion evaluators for geometric states."""

from __future__ import annotations

from typing import Any, Callable

from backend.core.command import Assertion


def _check_is_valid(geometry: Any, prev_geometry: Any, args: tuple[Any, ...]) -> str | None:
    if geometry is None:
        return "Geometry is None, cannot satisfy is_valid."
    valid_fn = getattr(geometry, "is_valid", None)
    if callable(valid_fn):
        if not valid_fn():
            return "Geometry manifold validation failed (is_valid returned False)."
    return None


def _check_is_solid(geometry: Any, prev_geometry: Any, args: tuple[Any, ...]) -> str | None:
    if geometry is None:
        return "Geometry is None, cannot satisfy is_solid."
    vol = getattr(geometry, "volume", None)
    if vol is None or vol <= 1e-6:
        return f"Geometry is not a closed solid (volume={vol!r} <= 1e-6)."
    return None


def _check_volume_gt(geometry: Any, prev_geometry: Any, args: tuple[Any, ...]) -> str | None:
    if geometry is None:
        return "Geometry is None, cannot satisfy volume_gt."
    target_vol = float(args[0])
    actual_vol = float(getattr(geometry, "volume", 0.0))
    if actual_vol <= target_vol:
        return f"Volume {actual_vol:.6f} is not strictly greater than expected threshold {target_vol:.6f}."
    return None


def _check_volume_delta_sign(geometry: Any, prev_geometry: Any, args: tuple[Any, ...]) -> str | None:
    if prev_geometry is None:
        return None
    if geometry is None:
        return "Current geometry is None while evaluating volume_delta_sign."

    expected_sign = int(args[0])
    curr_vol = float(getattr(geometry, "volume", 0.0))
    prev_vol = float(getattr(prev_geometry, "volume", 0.0))
    delta = curr_vol - prev_vol

    if expected_sign > 0 and delta <= 1e-4:
        return f"Expected volume increase (+1), but volume changed by {delta:.6f} (prev={prev_vol:.4f}, curr={curr_vol:.4f})."
    if expected_sign < 0 and delta >= -1e-4:
        return f"Expected volume decrease (-1), but volume changed by {delta:.6f} (prev={prev_vol:.4f}, curr={curr_vol:.4f})."
    if expected_sign == 0 and abs(delta) > 1e-4:
        return f"Expected unchanged volume (0), but volume changed by {delta:.6f}."

    return None


def _check_face_count_delta(geometry: Any, prev_geometry: Any, args: tuple[Any, ...]) -> str | None:
    if prev_geometry is None:
        return None
    if geometry is None:
        return "Current geometry is None while evaluating face_count_delta."

    expected_delta = int(args[0])
    curr_faces = len(list(getattr(geometry, "faces")()))
    prev_faces = len(list(getattr(prev_geometry, "faces")()))
    actual_delta = curr_faces - prev_faces

    if actual_delta != expected_delta:
        return f"Face count delta mismatch: expected {expected_delta:+d}, observed {actual_delta:+d} (from {prev_faces} to {curr_faces})."

    return None


def _check_no_degenerate_faces(geometry: Any, prev_geometry: Any, args: tuple[Any, ...]) -> str | None:
    if geometry is None:
        return "Geometry is None, cannot evaluate no_degenerate_faces."

    min_area = float(args[0])
    faces_fn = getattr(geometry, "faces", None)
    if not callable(faces_fn):
        return None

    degenerate: list[str] = []
    for face in faces_fn():
        area = float(getattr(face, "area", 0.0))
        if area < min_area:
            degenerate.append(f"{face!r}(area={area:.8f})")

    if degenerate:
        return f"Degenerate faces detected (area < {min_area}): {', '.join(degenerate)}."

    return None


def _check_bbox_within(geometry: Any, prev_geometry: Any, args: tuple[Any, ...]) -> str | None:
    if geometry is None:
        return "Geometry is None, cannot evaluate bbox_within."

    min_x, min_y, min_z, max_x, max_y, max_z = (float(v) for v in args)
    bbox_fn = getattr(geometry, "bbox", None)
    if not callable(bbox_fn):
        return "Geometry lacks bbox() method."

    bb = bbox_fn()
    actual_min = getattr(bb, "min", None)
    actual_max = getattr(bb, "max", None)
    if actual_min is None or actual_max is None:
        return "Unable to determine bounding box boundaries."

    tol = 1e-3
    if (
        actual_min[0] < min_x - tol
        or actual_min[1] < min_y - tol
        or actual_min[2] < min_z - tol
        or actual_max[0] > max_x + tol
        or actual_max[1] > max_y + tol
        or actual_max[2] > max_z + tol
    ):
        return (
            f"Bounding box {actual_min}..{actual_max} overflows permitted region "
            f"({min_x}, {min_y}, {min_z})..({max_x}, {max_y}, {max_z})."
        )

    return None


def _check_patches_preserved(geometry: Any, prev_geometry: Any, args: tuple[Any, ...]) -> str | None:
    if not args or geometry is None:
        return None

    patch_store = args[0]
    if not hasattr(patch_store, "all"):
        return None

    from backend.core.patches import rebind
    _, failed_names = rebind(patch_store, geometry)
    if failed_names:
        return f"Boundary patches lost during operation: {', '.join(failed_names)}."

    return None


_HANDLERS: dict[str, Callable[[Any, Any, tuple[Any, ...]], str | None]] = {
    "is_valid": _check_is_valid,
    "is_solid": _check_is_solid,
    "volume_gt": _check_volume_gt,
    "volume_delta_sign": _check_volume_delta_sign,
    "face_count_delta": _check_face_count_delta,
    "no_degenerate_faces": _check_no_degenerate_faces,
    "bbox_within": _check_bbox_within,
    "patches_preserved": _check_patches_preserved,
}


def run(geometry: Any, prev_geometry: Any, assertions: tuple[Assertion, ...]) -> list[str]:
    failures: list[str] = []
    for ast in assertions:
        if ast.name not in _HANDLERS:
            raise ValueError(f"Unknown assertion name '{ast.name}'. Registered handlers: {sorted(_HANDLERS.keys())}")
        result = _HANDLERS[ast.name](geometry, prev_geometry, ast.args)
        if result is not None:
            failures.append(result)
    return failures
