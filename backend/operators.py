"""Selection-Aware Native SMLib Geometry Operators for BrepX.

Generates reproducible and idempotent Python code acting on active topological
selections or base entities for parametric modeling and CFD flow domain construction.
"""

from __future__ import annotations

from typing import Any


def _num(params: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(params.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def _int(params: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(params.get(key, default))
    except (TypeError, ValueError):
        return int(default)


def _str(params: dict[str, Any], key: str, default: str) -> str:
    val = params.get(key)
    return str(val) if val is not None else default


def _parse_indices(selections: list[str] | None, kind: str) -> list[int]:
    """Extract integer topological indices from expressions like 'part.faces()[3]'."""
    if not selections:
        return []
    token = f".{kind}()["
    indices: list[int] = []
    for expr in selections:
        if token in expr:
            try:
                tail = expr.split(token, 1)[1]
                idx = int(tail.split("]", 1)[0])
                if idx >= 0 and idx not in indices:
                    indices.append(idx)
            except (ValueError, IndexError):
                continue
    return indices


def build_operator_code(
    operator_id: str,
    params: dict[str, Any],
    selections: list[str] | None = None,
    has_existing_part: bool = False,
) -> tuple[str, str, bool]:
    """Generate (python_code, label, replace_all) for an operator invocation."""
    op = operator_id.lower()
    face_ids = _parse_indices(selections, "faces")
    edge_ids = _parse_indices(selections, "edges")
    if "face_indices" in params and isinstance(params["face_indices"], list):
        face_ids = [int(i) for i in params["face_indices"]]
    if "edge_indices" in params and isinstance(params["edge_indices"], list):
        edge_ids = [int(i) for i in params["edge_indices"]]

    # 基础三维解析图元与典型特征板
    if op == "box":
        l, w, h = _num(params, "length", 60), _num(params, "width", 40), _num(params, "height", 20)
        return f"part = Box({l}, {w}, {h})", f"长方体 ({l}×{w}×{h})", not has_existing_part

    if op == "cylinder":
        r, h = _num(params, "radius", 15), _num(params, "height", 40)
        return f"part = Cylinder({r}, {h})", f"圆柱体 (R{r}×{h})", not has_existing_part

    if op == "sphere":
        r = _num(params, "radius", 25)
        return f"part = Sphere({r})", f"球体 (R{r})", not has_existing_part

    if op == "cone":
        r1, r2, h = _num(params, "radius1", 20), _num(params, "radius2", 10), _num(params, "height", 40)
        return f"part = Cone({r1}, {r2}, {h})", f"圆锥台 (R{r1}→R{r2}, H{h})", not has_existing_part

    if op == "torus":
        rmaj, rmin = _num(params, "radius_major", 30), _num(params, "radius_minor", 8)
        return f"part = Torus({rmaj}, {rmin})", f"圆环体 (R{rmaj}, r{rmin})", not has_existing_part

    if op == "wedge":
        l, w, h = _num(params, "length", 60), _num(params, "width", 40), _num(params, "height", 25)
        top_l = _num(params, "top_length", 20)
        return f"part = Wedge({l}, {w}, {h}, {top_l})", f"楔形体 ({l}×{w}×{h})", not has_existing_part

    if op in ("flange_plate", "new-parametric-part"):
        l, w, t = _num(params, "length", 100), _num(params, "width", 80), _num(params, "thickness", 12)
        fr, hr = _num(params, "fillet_r", 10), _num(params, "hole_r", 15)
        code = (
            f"part = Box({l}, {w}, {t})\n"
            f"if {fr} > 0:\n    part = part.fillet(part.edges().parallel_to(Z), {fr})\n"
            f"if {hr} > 0:\n    part = part - Cylinder({hr}, {t + 4})\n"
            f"for dx in [-{round(l*0.35, 1)}, {round(l*0.35, 1)}]:\n"
            f"    for dy in [-{round(w*0.31, 1)}, {round(w*0.31, 1)}]:\n"
            f"        part = part - Cylinder(4.0, {t + 4}).translate(dx, dy, 0)"
        )
        return code, f"带孔圆角法兰板 ({l}×{w}×{t})", True

    if op in ("feature_boss", "new-feature-graph"):
        l, w, h = _num(params, "length", 80), _num(params, "width", 50), _num(params, "height", 12)
        bd, bh = _num(params, "boss_d", 28), _num(params, "boss_h", 15)
        hd, fr = _num(params, "hole_d", 14), _num(params, "fillet_r", 6)
        code = (
            f"part = Box({l}, {w}, {h})\n"
            f"if {fr} > 0:\n    part = part.fillet(part.edges().parallel_to(Z), {fr})\n"
            f"part = part + Cylinder({bd / 2.0}, {bh}).translate(0, 0, {(h + bh) / 2.0})\n"
            f"if {hd} > 0:\n    part = part - Cylinder({hd / 2.0}, {h + bh + 6}).translate(0, 0, {bh / 2.0})"
        )
        return code, f"草图凸台驱动件 ({l}×{w})", True

    # 二维草图构造与工作平面映射
    if op in ("line", "rectangle", "circle", "arc", "polyline", "bspline", "spline", "sketch_draw"):
        sketch_kind = _str(params, "sketch_kind", op)
        plane_name = _str(params, "plane", "XY").upper()
        on_face_expr = f"part.faces()[{face_ids[0]}]" if (face_ids and has_existing_part) else f"Plane.{plane_name}"
        pts = params.get("points") or []
        extrude_h = _num(params, "extrude_height", 0.0)

        if sketch_kind == "circle":
            r = _num(params, "radius", _num(params, "dim1", 18))
            cx, cy = _num(params, "cx", 0.0), _num(params, "cy", 0.0)
            sk_expr = f"Circle({r}).translate({cx}, {cy}, 0).on({on_face_expr})"
            lbl = f"圆形草图 (R{r})"
        elif sketch_kind == "rectangle":
            w = _num(params, "width", _num(params, "dim1", 40))
            h = _num(params, "height", _num(params, "dim2", 25))
            cx, cy = _num(params, "cx", 0.0), _num(params, "cy", 0.0)
            sk_expr = f"Rectangle({w}, {h}).translate({cx}, {cy}, 0).on({on_face_expr})"
            lbl = f"矩形草图 ({w}×{h})"
        elif sketch_kind == "line":
            p1, p2 = (tuple(pts[0]), tuple(pts[1])) if len(pts) >= 2 else ((-20.0, 0.0, 0.0), (20.0, 0.0, 0.0))
            sk_expr = f"Line({p1}, {p2}).on({on_face_expr})"
            lbl = "直线草图"
        elif sketch_kind == "arc":
            p1, p2, p3 = (tuple(pts[0]), tuple(pts[1]), tuple(pts[2])) if len(pts) >= 3 else ((-20.0, 0.0, 0.0), (0.0, 10.0, 0.0), (20.0, 0.0, 0.0))
            sk_expr = f"ThreePointArc({p1}, {p2}, {p3}).on({on_face_expr})"
            lbl = "三点圆弧草图"
        elif sketch_kind in ("bspline", "spline"):
            closed = bool(params.get("closed", True))
            pts_str = ", ".join(str(tuple(p)) for p in pts) if len(pts) >= 3 else "(-20, 0, 0), (0, 15, 0), (20, 0, 0)"
            wire_expr = f"Spline({pts_str}, closed={closed})"
            sk_expr = f"make_face({wire_expr}).on({on_face_expr})" if closed else f"{wire_expr}.on({on_face_expr})"
            lbl = "样条曲线草图"
        else:
            closed = bool(params.get("closed", True))
            pts_str = ", ".join(str(tuple(p)) for p in pts) if len(pts) >= 3 else "(-15, -10, 0), (15, -10, 0), (15, 10, 0), (-15, 10, 0)"
            wire_expr = f"Polyline({pts_str}, close={closed})"
            sk_expr = f"make_face({wire_expr}).on({on_face_expr})" if closed else f"{wire_expr}.on({on_face_expr})"
            lbl = "多段折线草图"

        if extrude_h != 0.0:
            op_sym = "+" if extrude_h > 0 else "-"
            code = f"sketch = {sk_expr}\npart = part {op_sym} extrude(sketch, {abs(extrude_h)})" if has_existing_part and face_ids else f"sketch = {sk_expr}\npart = extrude(sketch, {abs(extrude_h)})"
            return code, f"{lbl} 并拉伸 ({extrude_h} mm)", False

        return (f"sketch = {sk_expr}", lbl, False) if has_existing_part else (f"sketch = {sk_expr}\npart = sketch", lbl, False)

    # 扫描成型与放样算子
    if op == "extrude":
        amount = _num(params, "height", _num(params, "amount", 20.0))
        mode = _str(params, "mode", "auto")
        taper = _num(params, "taper", 0.0)
        taper_arg = f", taper={taper}" if taper != 0 else ""

        if has_existing_part and face_ids:
            f_idx = face_ids[0]
            code = (
                f"_f = part.faces()[{f_idx}]\n"
                f"if not _f.is_planar:\n"
                f"    part = part.offset({amount})\n"
                f"else:\n"
                f"    _h = {amount}\n"
                f"    _cut = ({mode == 'cut'} or ({mode == 'auto'} and _h < 0))\n"
                f"    part = (part - extrude(_f, -abs(_h){taper_arg})) if _cut else (part + extrude(_f, abs(_h){taper_arg}))"
            )
            return code, f"选面拉伸 Face #{f_idx} ({amount} mm)", False

        prof = _str(params, "profile", "rectangle")
        d1, d2 = _num(params, "dim1", 40), _num(params, "dim2", 30)
        prof_code = f"Circle({d1})" if prof == "circle" else f"Rectangle({d1}, {d2})"
        return f"sketch = {prof_code}\npart = extrude(sketch, {amount}{taper_arg})", f"草图拉伸 ({amount} mm)", not has_existing_part

    if op == "revolve":
        angle = _num(params, "angle", 360.0)
        r, off_x = _num(params, "radius", 10.0), _num(params, "offset_x", 25.0)
        if has_existing_part and face_ids:
            return f"part = revolve(part.faces()[{face_ids[0]}], Z, {angle})", f"选面旋转 Face #{face_ids[0]} ({angle}°)", False
        return f"sketch = Circle({r}).on(Plane.XZ).translate({off_x}, 0, 0)\npart = revolve(sketch, Z, {angle})", f"旋转体 ({angle}°)", not has_existing_part

    if op == "sweep":
        r, hr = _num(params, "radius", 4.0), _num(params, "helix_radius", 25.0)
        p, h = _num(params, "pitch", 20.0), _num(params, "height", 60.0)
        return f"path = Helix(pitch={p}, height={h}, radius={hr})\npart = sweep(Circle({r}), path)", f"螺旋扫掠 (R{r})", not has_existing_part

    if op == "loft":
        r1, r2, h = _num(params, "bottom_radius", 25.0), _num(params, "top_radius", 12.0), _num(params, "height", 40.0)
        return f"s1 = Circle({r1})\ns2 = Circle({r2}).translate(0, 0, {h})\npart = loft([s1, s2])", f"放样体 (R{r1}→R{r2})", not has_existing_part

    # 拓扑边局部圆角与倒角
    if op == "fillet":
        r = max(0.1, _num(params, "radius", 4.0))
        if edge_ids:
            idx_list = ", ".join(f"_edges[{i}]" for i in edge_ids)
            return f"_edges = list(part.edges())\npart = part.fillet([{idx_list}], {r})", f"局部圆角 ({len(edge_ids)}边, R{r})", False
        return f"part = part.fillet(part.edges().parallel_to(Z), {r})", f"特征圆角 (R{r})", False

    if op == "chamfer":
        d = max(0.1, _num(params, "distance", _num(params, "radius", 3.0)))
        if edge_ids:
            idx_list = ", ".join(f"_edges[{i}]" for i in edge_ids)
            return f"_edges = list(part.edges())\npart = part.chamfer([{idx_list}], {d})", f"局部倒角 ({len(edge_ids)}边, D{d})", False
        return f"part = part.chamfer(part.edges().parallel_to(Z), {d})", f"特征倒角 (D{d})", False

    # 打孔、薄壁抽壳与拔模
    if op in ("hole", "counterbore", "countersink"):
        r, depth = _num(params, "radius", 6.0), _num(params, "depth", 40.0)
        x, y = _num(params, "x", 0.0), _num(params, "y", 0.0)
        if op == "counterbore":
            cb_r, cb_d = _num(params, "cb_radius", r * 1.8), _num(params, "cb_depth", 4.0)
            tool_expr = f"CounterBoreHole({r}, {cb_r}, {cb_d}, {depth})"
            lbl = f"沉头孔 (R{r}/R{cb_r})"
        elif op == "countersink":
            cs_r = _num(params, "cs_radius", r * 1.8)
            tool_expr = f"CounterSinkHole({r}, {cs_r}, {depth})"
            lbl = f"埋头孔 (R{r}/R{cs_r})"
        else:
            tool_expr = f"Hole({r}, {depth})"
            lbl = f"定位孔 (R{r})"

        if face_ids:
            f_idx = face_ids[0]
            code = (
                f"_f = part.faces()[{f_idx}]\n"
                f"if _f.is_planar:\n"
                f"    part = part - {tool_expr}.translate({x}, {y}, 0).on(_f)\n"
                f"else:\n"
                f"    _c = _f.center()\n"
                f"    part = part - Cylinder({r}, {depth}).translate(_c.x + {x}, _c.y + {y}, _c.z)"
            )
            return code, f"{lbl} @ Face #{f_idx}", False
        return f"part = part - Cylinder({r}, {depth}).translate({x}, {y}, 0)", lbl, False

    if op == "shell":
        t = _num(params, "thickness", 2.0)
        if face_ids:
            openings_str = ", ".join(f"_faces[{i}]" for i in face_ids)
            return f"_faces = list(part.faces())\npart = part.shell({t}, openings=[{openings_str}])", f"开口抽壳 ({t} mm)", False
        return f"part = part.shell({t}, openings=part.faces().top())", f"抽壳 ({t} mm)", False

    if op == "offset":
        dist = _num(params, "distance", 2.0)
        return f"part = part.offset({dist})", f"等距偏移 ({dist} mm)", False

    if op == "draft":
        angle = _num(params, "angle", 5.0)
        if face_ids:
            code = (
                f"_faces = list(part.faces())\n"
                f"_targets = [_faces[i] for i in {face_ids} if i < len(_faces)]\n"
                f"_norm = _targets[0].normal_at() if _targets else None\n"
                f"_plane = Plane.XZ if (_norm and abs(_norm.z) > 0.6) else Plane.XY\n"
                f"part = part.draft(_targets, {angle}, _plane) if _targets else part"
            )
            return code, f"选面拔模 ({angle}°)", False
        code = (
            f"_walls = [f for f in part.faces() if abs(f.normal_at().z) < 0.6]\n"
            f"part = part.draft(_walls, {angle}, Plane.XY) if _walls else part"
        )
        return code, f"侧壁拔模 ({angle}°)", False

    # 布尔与阵列变换
    if op in ("boolean-union", "boolean-subtract", "boolean-intersection", "boolean"):
        mode = _str(params, "operation", "union" if "union" in op else "difference" if "subtract" in op else "intersection")
        tk = _str(params, "tool_kind", "cylinder")
        tr, th = _num(params, "tool_r", 14.0), _num(params, "tool_h", 45.0)
        tx, ty, tz = _num(params, "x", 0.0), _num(params, "y", 0.0), _num(params, "z", 0.0)
        t_expr = f"Sphere({tr})" if tk == "sphere" else f"Box({tr*2}, {tr*2}, {th})" if tk == "box" else f"Cylinder({tr}, {th})"
        if tx or ty or tz:
            t_expr += f".translate({tx}, {ty}, {tz})"
        sym = "+" if mode == "union" else "-" if mode == "difference" else "&"
        return f"_tool = {t_expr}\npart = part {sym} _tool", f"布尔运算 ({mode})", False

    if op in ("slice", "split"):
        plane_name = _str(params, "plane", "YZ").upper()
        keep = _str(params, "keep", "above")
        return f"part = split(part, Plane.{plane_name}, keep='{keep}')", f"平面剖切 (Plane.{plane_name})", False

    if op == "mirror":
        plane_name = _str(params, "plane", "YZ").upper()
        join = bool(params.get("join", True))
        return (f"part = part + mirror(part, Plane.{plane_name})", f"镜像合并 (Plane.{plane_name})", False) if join else (f"part = mirror(part, Plane.{plane_name})", f"镜像 (Plane.{plane_name})", False)

    if op == "array":
        nx, ny = _int(params, "count_x", 2), _int(params, "count_y", 2)
        dx, dy = _num(params, "step_x", 35.0), _num(params, "step_y", 35.0)
        code = f"_items = list(GridLocations({dx}, {dy}, {nx}, {ny}) * part)\npart = _items[0]\nfor _it in _items[1:]:\n    part = part + _it"
        return code, f"矩形阵列 ({nx}×{ny})", False

    if op == "circular":
        n = _int(params, "count", 6)
        rad = _num(params, "radius", 30.0)
        code = f"_items = list(PolarLocations({rad}, {n}) * part)\npart = _items[0]\nfor _it in _items[1:]:\n    part = part + _it"
        return code, f"环形阵列 ({n}个, R{rad})", False

    if op in ("translate", "move"):
        dx, dy, dz = _num(params, "dx", 0.0), _num(params, "dy", 0.0), _num(params, "dz", 0.0)
        return f"part = part.translate({dx}, {dy}, {dz})", f"平移 ({dx}, {dy}, {dz})", False

    if op in ("rotate", "rotate3d"):
        axis = _str(params, "axis", "Z").upper()
        angle = _num(params, "angle", 45.0)
        return f"part = part.rotate({axis if axis in ('X', 'Y', 'Z') else 'Z'}, {angle})", f"旋转 ({axis}轴, {angle}°)", False

    if op == "scale":
        factor = max(0.01, _num(params, "factor", 1.25))
        return f"part = part.scale({factor})", f"等比缩放 ({factor}x)", False

    if op == "copy":
        dx, dy = _num(params, "offset_x", 50.0), _num(params, "offset_y", 0.0)
        return f"part = part + part.translate({dx}, {dy}, 0)", f"复制平移 ({dx}, {dy})", False

    # CFD 几何前处理与去特征化
    if op == "remove_fillets":
        if face_ids:
            f_str = ", ".join(f"_faces[{i}]" for i in face_ids)
            return f"_faces = list(part.faces())\npart = part.remove_fillets([{f_str}])", f"擦除圆角面 ({face_ids})", False
        code = "_fillets = [f for f in part.faces() if not f.is_planar]\nif _fillets:\n    part = part.remove_fillets(_fillets)"
        return code, "一键去圆角特征", False

    if op == "remove_faces":
        if not face_ids:
            raise ValueError("请先在视口中选择要移除并愈合的特征面")
        code = (
            f"_faces = list(part.faces())\n"
            f"_targets = [_faces[i] for i in {face_ids} if i < len(_faces)]\n"
            f"try:\n    part = part.remove_faces(_targets)\n"
            f"except Exception:\n    part = part.remove_faces(_targets, partial=True)"
        )
        return code, f"特征面消除与愈合 ({face_ids})", False

    if op == "cavity_extraction":
        code = (
            "_bb = part.bbox()\n"
            "_tight = Box(_bb.size[0], _bb.size[1], _bb.size[2]).translate(_bb.center.x, _bb.center.y, _bb.center.z)\n"
            "_flow = _tight - part\n"
            "if _flow.is_valid() and _flow.volume > 1e-4:\n"
            "    part = _flow\n"
            "else:\n"
            "    _pad = max(max(_bb.size) * 0.1, 5.0)\n"
            "    _env = Box(_bb.size[0] + _pad * 2, _bb.size[1] + _pad * 2, _bb.size[2] + _pad * 2).translate(_bb.center.x, _bb.center.y, _bb.center.z)\n"
            "    _cells = sorted(merge(_env, part).cells(), key=lambda c: c.volume)\n"
            "    part = _cells[0] if _cells else (_tight - part)"
        )
        return code, "CFD 流体域提取", False

    if op == "heal":
        return "part = part.heal()", "几何拓扑自动修复", False

    raise ValueError(f"未知的几何建模算子: {operator_id}")
