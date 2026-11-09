"""Topological selector expression parser and evaluator for SMLib geometries."""

from __future__ import annotations

import ast
import re
from typing import Any

from backend.selector.errors import SelectorResolutionError

METHOD_CALL_PATTERN = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\((.*)\)$")

AXIS_MAP = {
    "X": "X",
    "Y": "Y",
    "Z": "Z",
    "-X": "-X",
    "-Y": "-Y",
    "-Z": "-Z",
}


def _get_axis_constant(axis_name: str) -> Any:
    cleaned = axis_name.strip().strip("'\"")
    if cleaned not in AXIS_MAP:
        raise SelectorResolutionError(
            f"facing({axis_name})",
            "current",
            reason="bad_syntax",
        )
    import smlibpy

    constants = {
        "X": smlibpy.X,
        "Y": smlibpy.Y,
        "Z": smlibpy.Z,
        "-X": -smlibpy.X,
        "-Y": -smlibpy.Y,
        "-Z": -smlibpy.Z,
    }
    return constants[cleaned]


def _parse_nearest_args(arg_str: str) -> tuple[list[float], list[float] | None]:
    normal_vec = None
    pos_vec = None

    if "normal=" in arg_str:
        parts = arg_str.split("normal=", 1)
        first_part = parts[0].strip().rstrip(",")
        second_part = parts[1].strip()

        val_pos = ast.literal_eval(first_part)
        if isinstance(val_pos, (list, tuple)) and len(val_pos) == 3:
            pos_vec = [float(x) for x in val_pos]
        else:
            raise ValueError("Position must be a 3-element list or tuple")

        val_norm = ast.literal_eval(second_part)
        if isinstance(val_norm, (list, tuple)) and len(val_norm) == 3:
            normal_vec = [float(x) for x in val_norm]
        else:
            raise ValueError("Normal must be a 3-element list or tuple")
    else:
        val_pos = ast.literal_eval(arg_str)
        if isinstance(val_pos, (list, tuple)) and len(val_pos) == 3:
            pos_vec = [float(x) for x in val_pos]
        else:
            raise ValueError("Position must be a 3-element list or tuple")

    return pos_vec, normal_vec


def _parse_chain(expr: str) -> list[tuple[str, str]]:
    if "(" in expr and ")" not in expr:
        raise SelectorResolutionError(expr, "current", reason="bad_syntax")
    if ")" in expr and "(" not in expr:
        raise SelectorResolutionError(expr, "current", reason="bad_syntax")
    if expr.count("(") != expr.count(")"):
        raise SelectorResolutionError(expr, "current", reason="bad_syntax")

    tokens: list[str] = []
    current_token: list[str] = []
    paren_depth = 0
    bracket_depth = 0

    for ch in expr.strip():
        if ch == "(":
            paren_depth += 1
            current_token.append(ch)
        elif ch == ")":
            paren_depth -= 1
            current_token.append(ch)
        elif ch == "[":
            bracket_depth += 1
            current_token.append(ch)
        elif ch == "]":
            bracket_depth -= 1
            current_token.append(ch)
        elif ch == "." and paren_depth == 0 and bracket_depth == 0:
            tokens.append("".join(current_token).strip())
            current_token = []
        else:
            current_token.append(ch)

    if current_token:
        tokens.append("".join(current_token).strip())

    chain: list[tuple[str, str]] = []
    for token in tokens:
        match = METHOD_CALL_PATTERN.match(token.strip())
        if not match:
            raise SelectorResolutionError(expr, "current", reason="bad_syntax")
        chain.append((match.group(1), match.group(2).strip()))

    return chain


def _format_element_candidate(item: Any, root_name: str) -> str:
    center_fn = getattr(item, "center", None)
    if callable(center_fn):
        c = center_fn()
        return f"{root_name}().nearest([{c.x:.4f}, {c.y:.4f}, {c.z:.4f}])"
    return repr(item)


class SelectorResolver:
    @classmethod
    def resolve(cls, geometry: Any, expr: str) -> Any:
        if geometry is None:
            raise SelectorResolutionError(expr, "current", reason="unsupported")

        chain = _parse_chain(expr)
        if not chain:
            raise SelectorResolutionError(expr, "current", reason="bad_syntax")

        root_name, root_arg = chain[0]
        if root_arg:
            raise SelectorResolutionError(expr, "current", reason="bad_syntax")

        if root_name == "faces":
            if not hasattr(geometry, "faces"):
                raise SelectorResolutionError(expr, "current", reason="unsupported")
            current = geometry.faces()
        elif root_name == "edges":
            if not hasattr(geometry, "edges"):
                raise SelectorResolutionError(expr, "current", reason="unsupported")
            current = geometry.edges()
        elif root_name == "vertices":
            if not hasattr(geometry, "vertices"):
                raise SelectorResolutionError(expr, "current", reason="unsupported")
            current = geometry.vertices()
        else:
            raise SelectorResolutionError(expr, "current", reason="unsupported")

        for method_name, arg_str in chain[1:]:
            if root_name == "faces" and method_name == "parallel_to":
                raise SelectorResolutionError(expr, "current", reason="unsupported")
            if root_name == "edges" and method_name in ("facing", "planar", "cylinders", "fillets"):
                raise SelectorResolutionError(expr, "current", reason="unsupported")

            if not hasattr(current, method_name):
                raise SelectorResolutionError(expr, "current", reason="unsupported")

            target_fn = getattr(current, method_name)

            if method_name in ("facing", "parallel_to"):
                if not arg_str:
                    raise SelectorResolutionError(expr, "current", reason="bad_syntax")
                axis_const = _get_axis_constant(arg_str)
                current = target_fn(axis_const)
            elif method_name == "nearest":
                if not arg_str:
                    raise SelectorResolutionError(expr, "current", reason="bad_syntax")
                try:
                    pos_coords, normal_coords = _parse_nearest_args(arg_str)
                except Exception:
                    raise SelectorResolutionError(expr, "current", reason="bad_syntax")

                if normal_coords is not None and root_name == "faces":
                    import smlibpy
                    target_normal = smlibpy.Vector(*normal_coords).normalized()
                    matching_faces = []
                    for face in current:
                        if hasattr(face, "normal_at"):
                            try:
                                fnorm = face.normal_at()
                                if fnorm.dot(target_normal) > 0.99:
                                    matching_faces.append(face)
                            except Exception:
                                continue
                    if not matching_faces:
                        candidates = [_format_element_candidate(f, "faces") for f in list(geometry.faces())[:5]]
                        raise SelectorResolutionError(expr, "current", candidates=candidates, reason="no_match")
                    from smlibpy.shapes import ShapeList
                    current = ShapeList(matching_faces).nearest(pos_coords)
                else:
                    current = target_fn(pos_coords)
            elif method_name in ("top", "bottom", "planar", "cylinders", "fillets", "lines", "largest", "smallest"):
                if arg_str:
                    raise SelectorResolutionError(expr, "current", reason="bad_syntax")
                current = target_fn()
            else:
                raise SelectorResolutionError(expr, "current", reason="unsupported")

            curr_list = list(current) if hasattr(current, "__iter__") else [current]
            if not curr_list:
                cand_source = geometry.faces() if root_name == "faces" else geometry.edges()
                candidates = [_format_element_candidate(item, root_name) for item in list(cand_source)[:5]]
                raise SelectorResolutionError(expr, "current", candidates=candidates, reason="no_match")

        results = list(current) if hasattr(current, "__iter__") else [current]

        if not results:
            cand_source = geometry.faces() if root_name == "faces" else geometry.edges()
            candidates = [_format_element_candidate(item, root_name) for item in list(cand_source)[:5]]
            raise SelectorResolutionError(expr, "current", candidates=candidates, reason="no_match")

        if len(results) > 1:
            candidates = [_format_element_candidate(item, root_name) for item in results[:5]]
            raise SelectorResolutionError(
                expr,
                "current",
                candidates=candidates,
                reason="ambiguous",
            )

        return results[0]
