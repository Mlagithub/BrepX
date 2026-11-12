"""Generate ``FeatureSpec`` objects from smlibpy callables.

This module is the semantic overlay: ``_ACTIONS`` says which kernel callable
becomes which document action, which arguments are shape roles, and how the
call is made.  Everything else (parameter names, defaults, kinds) is read from
the installed kernel's signatures, so kernel signature changes flow into the
catalogue without editing the action table.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Iterable

import smlibpy
from cadwork import smlib as S

from . import checks
from .checks import CheckResult
from .features import FeatureError, FeatureOutput, FeatureSpec, InputRole, Param


@dataclass(frozen=True)
class Action:
    type: str
    source: str                      # "Box" or "Part.fillet"
    return_kind: str                 # part|shell|profile|curve|shape_list
    inputs: tuple[InputRole, ...] = ()
    allow: tuple[str, ...] | None = None
    deny: tuple[str, ...] = ()
    call: str = "kwargs"             # kwargs|method|varargs|list|points
    domain: str = "general"


def I(role: str, kind: str, many: bool = False, optional: bool = False) -> InputRole:
    return InputRole(role, kind, many, optional)


_ACTIONS: tuple[Action, ...] = (
    Action("k_box", "Box", "part", allow=("length", "width", "height")),
    Action("k_cylinder", "Cylinder", "part", allow=("radius", "height", "arc_size")),
    Action("k_cone", "Cone", "part", allow=("bottom_radius", "top_radius", "height", "arc_size")),
    Action("k_sphere", "Sphere", "part", allow=("radius", "arc_size1", "arc_size2", "arc_size3")),
    Action("k_torus", "Torus", "part", allow=("major_radius", "minor_radius", "minor_start_angle", "minor_end_angle", "major_angle")),
    Action("k_wedge", "Wedge", "part", allow=("length", "width", "height", "top_length")),
    Action("k_pyramid", "Pyramid", "part", allow=("length", "width", "height")),
    Action("k_annular_sector", "AnnularSector", "part", allow=("inner_radius", "outer_radius", "height", "arc_size")),
    Action("k_hole", "Hole", "part", allow=("radius", "depth")),
    Action("k_counter_bore_hole", "CounterBoreHole", "part",
           allow=("radius", "counter_bore_radius", "counter_bore_depth", "depth")),
    Action("k_counter_sink_hole", "CounterSinkHole", "part",
           allow=("radius", "counter_sink_radius", "depth", "angle")),
    Action("k_rectangle", "Rectangle", "profile", allow=("width", "height", "fillet", "chamfer", "rotation")),
    Action("k_circle", "Circle", "profile", allow=("radius",)),
    Action("k_regular_polygon", "RegularPolygon", "profile",
           allow=("radius", "sides", "inscribed", "fillet", "chamfer", "rotation")),
    Action("k_polygon", "Polygon", "profile", allow=("fillet", "chamfer"), call="points"),
    Action("k_ellipse", "Ellipse", "profile", allow=("x_radius", "y_radius", "rotation")),
    Action("k_slot", "Slot", "profile", allow=("length", "width", "rotation")),
    Action("k_rounded_rectangle", "RoundedRectangle", "profile", allow=("width", "height", "radius")),
    Action("k_triangle", "Triangle", "profile", allow=("width", "height", "apex", "fillet", "chamfer", "rotation")),
    Action("k_trapezoid", "Trapezoid", "profile",
           allow=("width", "height", "left_angle", "right_angle", "fillet", "chamfer", "rotation")),
    Action("k_line", "Line", "curve", allow=("start", "end")),
    Action("k_polyline", "Polyline", "curve", allow=("close",), call="points"),
    Action("k_spline", "Spline", "curve", allow=("closed",), call="points"),
    Action("k_bezier", "Bezier", "curve", allow=("weights",), call="points"),
    Action("k_fillet_polyline", "FilletPolyline", "curve", allow=("radius", "close"), call="points"),
    Action("k_spiral", "Spiral", "curve", allow=("start_radius", "end_radius", "turns", "plane", "clockwise")),
    Action("k_helix", "Helix", "curve", allow=("pitch", "height", "radius", "end_radius", "left_handed")),
    Action("k_center_arc", "CenterArc", "curve", allow=("center", "radius", "start_angle", "arc_size", "plane")),
    Action("k_three_point_arc", "ThreePointArc", "curve", allow=("start", "through", "end")),
    Action("k_tangent_arc", "TangentArc", "curve", allow=("start", "end", "tangent")),
    Action("k_radius_arc", "RadiusArc", "curve", allow=("start", "end", "radius", "plane")),
    Action("k_sagitta_arc", "SagittaArc", "curve", allow=("start", "end", "sagitta", "plane")),
    Action("k_polar_line", "PolarLine", "curve", allow=("start", "length", "angle", "plane")),
    Action("k_extrude", "extrude", "part", (I("profile", "profile"),),
           allow=("amount", "both", "taper", "corners")),
    Action("k_revolve", "revolve", "part", (I("profile", "profile"),),
           allow=("angle",)),
    Action("k_loft", "loft", "part", (I("sections", "profile", many=True),),
           allow=("ruled", "smooth", "closed"), call="list"),
    Action("k_sweep", "sweep", "part", (I("profile", "profile"), I("path", "curve")),
           allow=("orient", "translational", "sharp_corners", "twist")),
    Action("k_swing", "swing", "part", (I("profile", "profile"), I("outline", "profile"))),
    Action("k_thicken", "thicken", "part", (I("surface", "shell"),), allow=("thickness", "both")),
    Action("k_fillet", "Part.fillet", "part", (I("target", "part"), I("edges", "edges")),
           allow=("radius", "continuity", "fullness", "propagate", "corners", "setback"), call="method"),
    Action("k_chamfer", "Part.chamfer", "part", (I("target", "part"), I("edges", "edges")),
           allow=("length", "length2", "angle", "propagate", "corners"), call="method"),
    Action("k_shell", "Part.shell", "part", (I("target", "part"), I("openings", "faces", optional=True)),
           allow=("thickness", "outward", "corners", "walls"), call="method"),
    Action("k_split", "Part.split", "part", (I("target", "part"),),
           allow=("plane", "keep"), call="method"),
    Action("k_offset", "Part.offset", "part", (I("target", "part"),),
           allow=("distance", "corners"), call="method"),
    Action("k_offset_faces", "Part.offset_faces", "part", (I("target", "part"), I("faces", "faces")),
           allow=("distance",), call="method"),
    Action("k_move_faces", "Part.move_faces", "part", (I("target", "part"), I("faces", "faces")),
           allow=("by",), call="method"),
    Action("k_remove_faces", "Part.remove_faces", "part", (I("target", "part"), I("faces", "faces")),
           allow=("partial",), call="method"),
    Action("k_remove_fillets", "Part.remove_fillets", "part",
           (I("target", "part"), I("faces", "faces", optional=True)),
           allow=("max_radius", "partial"), call="method"),
    Action("k_heal", "Part.heal", "part", (I("target", "part"),), call="method"),
    Action("k_draft", "Part.draft", "part", (I("target", "part"), I("faces", "faces")),
           allow=("angle", "neutral_plane"), call="method"),
    Action("k_imprint", "Part.imprint", "part", (I("target", "part"), I("tool", "shape")),
           allow=("nearest",), call="method"),
    Action("k_twist", "Part.twist", "part", (I("target", "part"),),
           allow=("angle", "axis", "start", "end", "tolerance"), call="method", domain="deform"),
    Action("k_taper", "Part.taper", "part", (I("target", "part"),),
           allow=("scale", "axis", "start", "end", "tolerance"), call="method", domain="deform"),
    Action("k_bend", "Part.bend", "part", (I("target", "part"),),
           allow=("angle", "radius", "plane", "start", "end", "tolerance"), call="method", domain="deform"),
    Action("k_unroll", "Part.unroll", "part", (I("target", "part"),),
           allow=("radius", "axis", "start", "tolerance"), call="method", domain="deform"),
    Action("k_translate", "Part.translate", "same", (I("target", "shape"),),
           allow=("x", "y", "z"), call="method"),
    Action("k_rotate", "Part.rotate", "same", (I("target", "shape"),),
           allow=("axis", "angle"), call="method"),
    Action("k_scale", "Part.scale", "same", (I("target", "shape"),),
           allow=("factor", "center"), call="method"),
    Action("k_mirror", "Part.mirror", "same", (I("target", "shape"),),
           allow=("plane",), call="method"),
    Action("k_fuse", "Part.fuse", "part", (I("target", "part"), I("others", "part", many=True)),
           call="method"),
    Action("k_cut", "Part.cut", "part", (I("target", "part"), I("others", "part", many=True)),
           call="method"),
    Action("k_intersect", "Part.intersect", "part", (I("target", "part"), I("others", "part", many=True)),
           call="method"),
    Action("k_merge", "merge", "part", (I("parts", "part", many=True),), call="varargs"),
    Action("k_section", "Part.section", "profile", (I("target", "part"),),
           allow=("plane",), call="method"),
    Action("k_extend", "extend", "shell", (I("shape", "shape"),), allow=("distance",)),
    Action("k_blend", "blend", "shell", (I("edge_a", "curve"), I("edge_b", "curve")),
           allow=("continuity", "join")),
    Action("k_fill", "fill", "shell", (I("boundary", "curve"),), allow=("tangent",)),
    Action("k_ruled", "ruled", "shell", (I("a", "curve"), I("b", "curve"))),
    Action("k_surface_fillet", "surface_fillet", "shell",
           (I("a", "shape"), I("b", "shape")),
           allow=("radius", "radius2", "shape", "trim")),
    Action("k_match_edge", "match_edge", "shell",
           (I("sheet", "shell"), I("edge", "curve"), I("target", "curve")),
           allow=("extent",)),
    Action("k_merge_faces", "merge_faces", "shell",
           (I("sheet", "shell"), I("a", "faces"), I("b", "faces"))),
    Action("k_fit_curve", "fit_curve", "curve", allow=("points", "degree", "closed")),
    Action("k_make_face", "make_face", "profile",
           (I("outer", "curve"), I("holes", "curve", many=True)), call="varargs"),
    Action("k_xor", "xor", "profile",
           (I("sketch", "profile"), I("others", "profile", many=True)), call="varargs"),
    Action("k_hull", "Hull", "profile", (I("items", "profile", many=True),), call="varargs"),
    Action("k_stitch", "stitch", "shell", (I("pieces", "shape", many=True),), call="varargs"),
    Action("k_network", "network", "shell",
           (I("u", "curve", many=True), I("v", "curve", many=True)), call="list"),
    Action("k_flange", "Part.flange", "part", (I("target", "part"), I("edge", "edges")),
           allow=("length", "angle", "radius", "k_factor"), call="method", domain="sheetmetal"),
    Action("k_fold", "Part.fold", "part", (I("target", "part"), I("line", "curve")),
           allow=("angle", "radius", "k_factor", "partial"), call="method", domain="sheetmetal"),
    Action("k_unfold", "Part.unfold", "part", (I("target", "part"),),
           allow=("k_factor",), call="method", domain="sheetmetal"),
    Action("k_sketch_fillet", "Sketch.fillet", "profile", (I("target", "profile"),),
           allow=("radius",), call="method"),
    Action("k_sketch_chamfer", "Sketch.chamfer", "profile", (I("target", "profile"),),
           allow=("length",), call="method"),
    Action("k_sketch_cut", "Sketch.cut", "profile", (I("target", "profile"), I("others", "profile", many=True)),
           call="method"),
    Action("k_sketch_fuse", "Sketch.fuse", "profile", (I("target", "profile"), I("others", "profile", many=True)),
           call="method"),
    Action("k_sketch_intersect", "Sketch.intersect", "profile", (I("target", "profile"), I("others", "profile", many=True)),
           call="method"),
    Action("k_sketch_xor", "Sketch.xor", "profile", (I("target", "profile"), I("others", "profile", many=True)),
           call="method"),
    Action("k_face_extrude", "Face.extrude", "part", (I("target", "face"),),
           allow=("amount", "both", "taper", "corners"), call="method"),
    Action("k_face_to_shell", "Face.to_shell", "shell", (I("target", "face"),), call="method"),
    Action("k_face_offset", "Face.offset", "shell", (I("target", "face"),),
           allow=("distance",), call="method"),
    Action("k_face_to_sketch", "Face.to_sketch", "profile", (I("target", "face"),), call="method"),
    Action("k_face_untrimmed", "Face.untrimmed", "shell", (I("target", "face"),), call="method"),
    Action("k_face_extend", "Face.extend", "shell", (I("target", "face"),),
           allow=("distance", "continuity"), call="method"),
    Action("k_face_wrap", "Face.wrap", "shape_list", (I("target", "face"), I("shape", "shape")),
           allow=("at",), call="method"),
    Action("k_face_project", "Face.project", "shape_list", (I("target", "face"), I("curve", "curve")),
           call="method"),
    Action("k_face_iso", "Face.iso", "shape_list", (I("target", "face"),),
           allow=("u", "v"), call="method"),
    Action("k_face_split", "Face.split", "shape_list", (I("target", "face"), I("curves", "curve", many=True)),
           call="method"),
)


_ENUM_PLANE = ("XY", "XZ", "YZ")
_ENUM_AXIS = ("X", "Y", "Z")


def _resolve(source: str) -> tuple[Any, bool]:
    if "." in source:
        owner, name = source.split(".", 1)
        obj = getattr(smlibpy, owner, None)
        if obj is None or not hasattr(obj, name):
            raise FeatureError("KERNEL_ACTION_MISSING", f"{source} is not in this smlibpy")
        return getattr(obj, name), True
    obj = getattr(smlibpy, source, None)
    if obj is None:
        raise FeatureError("KERNEL_ACTION_MISSING", f"{source} is not in this smlibpy")
    return obj, False


def _kind_for(name: str, annotation: str, default: Any) -> str | None:
    low = annotation.lower()
    if name == "plane" or name == "neutral_plane" or "plane" in low:
        return "enum"
    if name == "axis" or low.endswith("'axis'") or low == "axis":
        return "enum"
    if name in {"points", "control_points"}:
        return "points"
    if default is not inspect.Parameter.empty and default is not None:
        if isinstance(default, bool):
            return "bool"
        if isinstance(default, int):
            return "int"
        if isinstance(default, float):
            return "float"
        if isinstance(default, str):
            return "str"
    if "vectorlike" in low and "float" not in low and "int" not in low:
        return "vector"
    if "bool" in low:
        return "bool"
    if "int" in low:
        return "int"
    if "float" in low:
        return "float"
    if "str" in low or "literal" in low:
        return "str"
    if default is not None and not isinstance(default, (str, bool, int, float)):
        return None
    if isinstance(default, bool):
        return "bool"
    if isinstance(default, int):
        return "int"
    if isinstance(default, float):
        return "float"
    if isinstance(default, str):
        return "str"
    return None


def _enum_default(default: Any, choices: tuple[str, ...]) -> str | None:
    if default is None or default is inspect.Parameter.empty:
        return None
    text = getattr(default, "name", None) or str(default)
    tail = text.rsplit(".", 1)[-1]
    return tail if tail in choices else None


def _parameters(action: Action, fn: Any, is_method: bool) -> dict[str, Param]:
    signature = inspect.signature(fn)
    params: dict[str, Param] = {}
    for index, (name, parameter) in enumerate(signature.parameters.items()):
        if is_method and index == 0:
            continue
        if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if name in action.deny:
            continue
        if action.allow is not None and name not in action.allow:
            continue
        if any(role.role == name for role in action.inputs):
            continue
        annotation = str(parameter.annotation)
        kind = _kind_for(name, annotation, parameter.default)
        if kind is None:
            continue
        if kind == "enum":
            choices = _ENUM_PLANE if kind == "enum" and (name == "plane" or name == "neutral_plane") else _ENUM_AXIS
            default = _enum_default(parameter.default, choices)
            if parameter.default is inspect.Parameter.empty:
                params[name] = Param("enum", None, choices=choices, required=True)
            elif default is not None:
                params[name] = Param("enum", default, choices=choices)
            continue
        if parameter.default is inspect.Parameter.empty:
            if kind in {"vector", "points"}:
                params[name] = Param(kind, None, required=True)
            elif kind in {"float", "int", "bool", "str"}:
                params[name] = Param(kind, None, required=True)
            continue
        if parameter.default is None:
            continue
        if kind in {"vector", "points"}:
            params[name] = Param(kind, parameter.default)
        else:
            params[name] = Param(kind, parameter.default)
    if action.call == "points":
        params["points"] = Param("points", None, required=True,
                                 description="the point list of this curve or profile")
    if action.type == "k_revolve":
        params["axis"] = Param("enum", "Z", choices=_ENUM_AXIS,
                               description="axis of revolution; default Z")
    if action.type == "k_shell":
        params["corners"] = Param("enum", None, choices=("round", "sharp"),
                                  description="corner treatment of the shell")
    if action.type == "k_sweep":
        params["scale_start"] = Param("float", 1.0, 1e-3, 1e3, unit="x", description="profile scale at the path start")
        params["scale_end"] = Param("float", 1.0, 1e-3, 1e3, unit="x", description="profile scale at the path end")
    return params


def _enum_value(name: str, value: str) -> Any:
    if name in {"plane", "neutral_plane"}:
        return getattr(S.Plane, value)
    if name == "axis":
        return getattr(S, value)
    return value


def _build_value(name: str, value: Any, param: Param) -> Any:
    if param.kind == "enum" and isinstance(value, str):
        return _enum_value(name, value)
    return value


def _make_build(action: Action, fn: Any, is_method: bool):
    def build(inputs: dict[str, Any], provided: dict[str, Any]) -> FeatureOutput:
        kwargs: dict[str, Any] = {}
        for name, param in action_params(action, fn, is_method).items():
            if name in {"scale_start", "scale_end", "points"}:
                continue
            kwargs[name] = _build_value(name, provided[name], param)
        if action.type == "k_sweep":
            kwargs["scale"] = (provided["scale_start"], provided["scale_end"])
        if action.call == "method":
            for role in action.inputs:
                if role.role in {"target", "others"}:
                    continue
                bound = inputs.get(role.role)
                if bound is None and role.optional:
                    continue
                kwargs[role.role] = list(bound) if role.many else bound
            target = inputs["target"]
            method = getattr(target, action.source.split(".", 1)[1])
            others = inputs.get("others")
            if others:
                return FeatureOutput(method(*tuple(others), **kwargs))
            return FeatureOutput(method(**kwargs))
        if action.call == "varargs":
            prefix = None
            values: list[Any] = []
            for role in action.inputs:
                bound = inputs.get(role.role)
                if role.many:
                    values.extend(list(bound or ()))
                elif prefix is None:
                    prefix = bound
                else:
                    values.append(bound)
            if action.type in {"k_make_face", "k_xor"}:
                return FeatureOutput(fn(prefix, *values, **kwargs))
            return FeatureOutput(fn(*values, **kwargs))
        if action.call == "list":
            args = {role.role: list(inputs[role.role] or ()) if role.many else inputs[role.role]
                    for role in action.inputs}
            args.update(kwargs)
            return FeatureOutput(fn(**args))
        if action.call == "points":
            points = provided.get("points")
            if points is None:
                raise FeatureError("INVALID_PARAM", f"{action.type} requires points")
            return FeatureOutput(fn(*points, **kwargs))
        args = {role.role: inputs[role.role] for role in action.inputs}
        args.update(kwargs)
        return FeatureOutput(fn(**args))

    return build


_PARAM_CACHE: dict[str, dict[str, Param]] = {}


def action_params(action: Action, fn: Any, is_method: bool) -> dict[str, Param]:
    key = action.type
    if key not in _PARAM_CACHE:
        _PARAM_CACHE[key] = _parameters(action, fn, is_method)
    return _PARAM_CACHE[key]


def _check_for(return_kind: str):
    def check(value: Any, params: dict[str, Any], inputs: dict[str, Any]) -> list[CheckResult]:
        if return_kind == "part":
            return [checks.valid(value), checks.solid(value), checks.watertight(value),
                    checks.volume_gt(value, 0.0)]
        if return_kind in {"shell", "profile", "curve"}:
            return [checks.extent(value, 0.0)]
        if return_kind == "same":
            if hasattr(value, "is_valid"):
                return [checks.valid(value)]
            return [checks.extent(value, 0.0)]
        if return_kind == "shape_list":
            return [checks.items(value)]
        return [checks.valid(value)]

    return check


def _summary(fn: Any, action: Action) -> str:
    doc = inspect.getdoc(fn) or ""
    line = doc.splitlines()[0].strip() if doc else ""
    return line or action.type


def generated_actions() -> list[FeatureSpec]:
    specs: list[FeatureSpec] = []
    for action in _ACTIONS:
        fn, is_method = _resolve(action.source)
        specs.append(FeatureSpec(
            type=action.type,
            summary=_summary(fn, action),
            inputs=action.inputs,
            params=action_params(action, fn, is_method),
            build=_make_build(action, fn, is_method),
            check=_check_for(action.return_kind),
            tier="kernel",
            origin=f"kernel:smlibpy.{action.source}",
            return_kind=action.return_kind,
        ))
    return specs


