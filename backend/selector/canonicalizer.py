"""Canonical topological selector generator with 5-level precedence rules."""

from __future__ import annotations

from typing import Any, Callable

from backend.selector.errors import SelectorResolutionError
from backend.selector.resolver import SelectorResolver


def _rule_face_facing(face: Any, part: Any) -> str | None:
    is_planar = getattr(face, "is_planar", False)
    if not is_planar:
        return None

    normal_fn = getattr(face, "normal_at", None)
    if not callable(normal_fn):
        return None

    norm = normal_fn()
    nx, ny, nz = float(norm[0]), float(norm[1]), float(norm[2])

    axis_cand = None
    if nz > 0.999:
        axis_cand = "Z"
    elif nz < -0.999:
        axis_cand = "-Z"
    elif nx > 0.999:
        axis_cand = "X"
    elif nx < -0.999:
        axis_cand = "-X"
    elif ny > 0.999:
        axis_cand = "Y"
    elif ny < -0.999:
        axis_cand = "-Y"

    if axis_cand is None:
        return None

    expr = f"faces().facing({axis_cand})"
    try:
        resolved = SelectorResolver.resolve(part, expr)
        if resolved == face:
            return expr
    except SelectorResolutionError as exc:
        _ = exc.reason

    return None


def _rule_face_planar_extremum(face: Any, part: Any) -> str | None:
    is_planar = getattr(face, "is_planar", False)
    if not is_planar:
        return None

    for ext in ("largest", "smallest"):
        expr = f"faces().planar().{ext}()"
        try:
            resolved = SelectorResolver.resolve(part, expr)
            if resolved == face:
                return expr
        except SelectorResolutionError as exc:
            _ = exc.reason
            continue

    return None


def _rule_face_cylinder_extremum(face: Any, part: Any) -> str | None:
    geom_type = getattr(face, "geom_type", "")
    if geom_type != "cylinder":
        return None

    expr_base = "faces().cylinders()"
    try:
        resolved = SelectorResolver.resolve(part, expr_base)
        if resolved == face:
            return expr_base
    except SelectorResolutionError as exc:
        _ = exc.reason

    for ext in ("largest", "smallest"):
        expr = f"faces().cylinders().{ext}()"
        try:
            resolved = SelectorResolver.resolve(part, expr)
            if resolved == face:
                return expr
        except SelectorResolutionError as exc:
            _ = exc.reason
            continue

    return None


def _rule_face_fillet_nearest(face: Any, part: Any) -> str | None:
    geom_type = getattr(face, "geom_type", "")
    if geom_type not in ("fillet", "torus", "cone"):
        return None

    center_fn = getattr(face, "center", None)
    if not callable(center_fn):
        return None

    c = center_fn()
    expr = f"faces().fillets().nearest([{c.x:.4f}, {c.y:.4f}, {c.z:.4f}])"
    try:
        resolved = SelectorResolver.resolve(part, expr)
        if resolved == face:
            return expr
    except SelectorResolutionError as exc:
        _ = exc.reason

    return None


def _rule_face_nearest_with_normal_fallback(face: Any, part: Any) -> str | None:
    center_fn = getattr(face, "center", None)
    if not callable(center_fn):
        return None
    c = center_fn()

    normal_fn = getattr(face, "normal_at", None)
    if callable(normal_fn):
        try:
            n = normal_fn()
            expr = f"faces().nearest([{c.x:.4f}, {c.y:.4f}, {c.z:.4f}], normal=[{n[0]:.4f}, {n[1]:.4f}, {n[2]:.4f}])"
            try:
                resolved = SelectorResolver.resolve(part, expr)
                if resolved == face:
                    return expr
            except SelectorResolutionError as exc_res:
                _ = exc_res.reason
        except Exception as exc_norm:
            _ = type(exc_norm)

    expr_pos_only = f"faces().nearest([{c.x:.4f}, {c.y:.4f}, {c.z:.4f}])"
    return expr_pos_only


FACE_RULES: tuple[Callable[[Any, Any], str | None], ...] = (
    _rule_face_facing,
    _rule_face_planar_extremum,
    _rule_face_cylinder_extremum,
    _rule_face_fillet_nearest,
    _rule_face_nearest_with_normal_fallback,
)


def _rule_edge_parallel(edge: Any, part: Any) -> str | None:
    for axis in ("X", "Y", "Z"):
        expr = f"edges().parallel_to({axis})"
        try:
            resolved = SelectorResolver.resolve(part, expr)
            if resolved == edge:
                return expr
        except SelectorResolutionError as exc:
            _ = exc.reason
            continue
    return None


def _rule_edge_lines(edge: Any, part: Any) -> str | None:
    geom_type = getattr(edge, "geom_type", "")
    if geom_type != "line":
        return None

    expr = "edges().lines()"
    try:
        resolved = SelectorResolver.resolve(part, expr)
        if resolved == edge:
            return expr
    except SelectorResolutionError as exc:
        _ = exc.reason
    return None


def _rule_edge_nearest_fallback(edge: Any, part: Any) -> str | None:
    center_fn = getattr(edge, "center", None)
    if callable(center_fn):
        c = center_fn()
        expr = f"edges().nearest([{c.x:.4f}, {c.y:.4f}, {c.z:.4f}])"
        return expr
    return None


EDGE_RULES: tuple[Callable[[Any, Any], str | None], ...] = (
    _rule_edge_parallel,
    _rule_edge_lines,
    _rule_edge_nearest_fallback,
)


def canonicalize_face(face: Any, part: Any) -> str:
    for rule in FACE_RULES:
        result = rule(face, part)
        if result is not None:
            return result
    raise SelectorResolutionError("faces()", "current", reason="unsupported")


def canonicalize_edge(edge: Any, part: Any) -> str:
    for rule in EDGE_RULES:
        result = rule(edge, part)
        if result is not None:
            return result
    raise SelectorResolutionError("edges()", "current", reason="unsupported")
