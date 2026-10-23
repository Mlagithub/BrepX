"""Selection-Aware Native SMLib Geometry Operators for SMLib Studio Next.

All operators generate clean, reproducible, idempotent `smlibpy` Python code
that acts directly on the user's B-Rep topological selections (`face_indices`,
`edge_indices`) or active workspace entities.
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

    # 1. 3D Primitives & Templates
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
            f"if {fr} > 0:\n"
            f"    part = part.fillet(part.edges().parallel_to(Z), {fr})\n"
            f"if {hr} > 0:\n"
            f"    part = part - Cylinder({hr}, {t + 4})\n"
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
            f"if {fr} > 0:\n"
            f"    part = part.fillet(part.edges().parallel_to(Z), {fr})\n"
            f"part = part + Cylinder({bd / 2.0}, {bh}).translate(0, 0, {(h + bh) / 2.0})\n"
            f"if {hd} > 0:\n"
            f"    part = part - Cylinder({hd / 2.0}, {h + bh + 6}).translate(0, 0, {bh / 2.0})"
        )
        return code, f"草图凸台驱动件 ({l}×{w})", True

    # 2. 2D Interactive Sketches (on plane or selected face)
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
            if len(pts) >= 2:
                p1, p2 = tuple(pts[0]), tuple(pts[1])
            else:
                d = _num(params, "dim1", 40)
                p1, p2 = (-d / 2.0, 0.0, 0.0), (d / 2.0, 0.0, 0.0)
            sk_expr = f"Line({p1}, {p2}).on({on_face_expr})"
            lbl = "直线草图 (Line)"
        elif sketch_kind == "arc":
            if len(pts) >= 3:
                p1, p2, p3 = tuple(pts[0]), tuple(pts[1]), tuple(pts[2])
            else:
                r = _num(params, "dim1", 20)
                p1, p2, p3 = (-r, 0.0, 0.0), (0.0, r, 0.0), (r, 0.0, 0.0)
            sk_expr = f"ThreePointArc({p1}, {p2}, {p3}).on({on_face_expr})"
            lbl = "三点圆弧草图 (ThreePointArc)"
        elif sketch_kind in ("bspline", "spline"):
            closed = bool(params.get("closed", True))
            if len(pts) >= 3:
                pts_str = ", ".join(str(tuple(p)) for p in pts)
            else:
                w, h = _num(params, "dim1", 35), _num(params, "dim2", 18)
                pts_str = f"(-{w}, 0, 0), (0, {h}, 0), ({w}, 0, 0), (0, -{h}, 0)"
            wire_expr = f"Spline({pts_str}, closed={closed})"
            sk_expr = f"make_face({wire_expr}).on({on_face_expr})" if closed else f"{wire_expr}.on({on_face_expr})"
            lbl = "样条曲线草图 (Spline)"
        else:  # polyline
            closed = bool(params.get("closed", True))
            if len(pts) >= 3:
                pts_str = ", ".join(str(tuple(p)) for p in pts)
            else:
                w, h = _num(params, "dim1", 35), _num(params, "dim2", 22)
                pts_str = f"(-{w/2}, -{h/2}, 0), ({w/2}, -{h/2}, 0), ({w/2}, {h/2}, 0), (0, {h*0.8}, 0), (-{w/2}, {h/2}, 0)"
            wire_expr = f"Polyline({pts_str}, close={closed})"
            sk_expr = f"make_face({wire_expr}).on({on_face_expr})" if closed else f"{wire_expr}.on({on_face_expr})"
            lbl = "多段折线草图 (Polyline)"

        if extrude_h != 0.0:
            if has_existing_part and face_ids:
                op_sym = "+" if extrude_h > 0 else "-"
                code = f"sketch = {sk_expr}\npart = part {op_sym} extrude(sketch, {extrude_h})"
            else:
                code = f"sketch = {sk_expr}\npart = extrude(sketch, {abs(extrude_h)})"
            return code, f"{lbl} 并拉伸 ({extrude_h} mm)", False

        if has_existing_part:
            return f"sketch = {sk_expr}", lbl, False
        return f"sketch = {sk_expr}\npart = sketch", lbl, False

    # 3. Selection-Sensitive Extrude, Revolve, Sweep, Loft
    if op == "extrude":
        amount = _num(params, "height", _num(params, "amount", 20.0))
        mode = _str(params, "mode", "auto")  # auto | join | cut | new
        taper = _num(params, "taper", 0.0)
        taper_arg = f", taper={taper}" if taper != 0 else ""

        if has_existing_part and face_ids:
            f_idx = face_ids[0]
            if mode == "new":
                code = f"part = extrude(part.faces()[{f_idx}], {amount}{taper_arg})"
            elif mode == "cut" or (mode == "auto" and amount < 0):
                code = f"part = part - extrude(part.faces()[{f_idx}], {-abs(amount)}{taper_arg})"
            else:
                code = f"part = part + extrude(part.faces()[{f_idx}], {abs(amount)}{taper_arg})"
            return code, f"选面拉伸 Face #{f_idx} ({amount} mm)", False

        shape = _str(params, "profile", "rectangle")
        d1, d2 = _num(params, "dim1", 40), _num(params, "dim2", 30)
        prof_code = f"Circle({d1})" if shape == "circle" else f"Rectangle({d1}, {d2})"
        code = f"sketch = {prof_code}\npart = extrude(sketch, {amount}{taper_arg})"
        return code, f"草图拉伸 ({amount} mm)", not has_existing_part

    if op == "revolve":
        angle = _num(params, "angle", 360.0)
        r = _num(params, "radius", 10.0)
        off_x = _num(params, "offset_x", 25.0)
        if has_existing_part and face_ids:
            code = f"part = revolve(part.faces()[{face_ids[0]}], Z, {angle})"
            return code, f"选面旋转 Face #{face_ids[0]} ({angle}°)", False
        code = f"sketch = Circle({r}).on(Plane.XZ).translate({off_x}, 0, 0)\npart = revolve(sketch, Z, {angle})"
        return code, f"旋转成型 ({angle}°)", not has_existing_part

    if op == "sweep":
        r = _num(params, "radius", 4.0)
        hr = _num(params, "helix_radius", 25.0)
        pitch = _num(params, "pitch", 20.0)
        h = _num(params, "height", 60.0)
        code = f"path = Helix(pitch={pitch}, height={h}, radius={hr})\npart = sweep(Circle({r}), path)"
        return code, f"螺旋扫掠 (R{r}, 螺距{pitch})", not has_existing_part

    if op == "loft":
        r1 = _num(params, "bottom_radius", 25.0)
        r2 = _num(params, "top_radius", 12.0)
        h = _num(params, "height", 40.0)
        code = f"s1 = Circle({r1})\ns2 = Circle({r2}).translate(0, 0, {h})\npart = loft([s1, s2])"
        return code, f"多截面放样 (R{r1}→R{r2}, H{h})", not has_existing_part

    # 4. Selection-Sensitive Edge Fillet & Chamfer
    if op == "fillet":
        r = max(0.1, _num(params, "radius", 4.0))
        if edge_ids:
            idx_list = ", ".join(f"_edges[{i}]" for i in edge_ids)
            code = f"_edges = list(part.edges())\npart = part.fillet([{idx_list}], {r})"
            return code, f"选边圆角 ({len(edge_ids)} 条边, R{r})", False
        code = f"part = part.fillet(part.edges().parallel_to(Z), {r})"
        return code, f"竖边倒圆角 (R{r})", False

    if op == "chamfer":
        d = max(0.1, _num(params, "distance", _num(params, "radius", 3.0)))
        if edge_ids:
            idx_list = ", ".join(f"_edges[{i}]" for i in edge_ids)
            code = f"_edges = list(part.edges())\npart = part.chamfer([{idx_list}], {d})"
            return code, f"选边倒角 ({len(edge_ids)} 条边, D{d})", False
        code = f"part = part.chamfer(part.edges().parallel_to(Z), {d})"
        return code, f"竖边倒角 (D{d})", False

    # 5. Selection-Sensitive Hole, Shell, Offset, Draft
    if op in ("hole", "counterbore", "countersink"):
        r = _num(params, "radius", 6.0)
        depth = _num(params, "depth", 40.0)
        x, y = _num(params, "x", 0.0), _num(params, "y", 0.0)
        if op == "counterbore":
            cb_r = _num(params, "cb_radius", r * 1.8)
            cb_d = _num(params, "cb_depth", 4.0)
            tool_expr = f"CounterBoreHole({r}, {cb_r}, {cb_d}, {depth})"
            lbl = f"沉头孔 (R{r}/R{cb_r})"
        elif op == "countersink":
            cs_r = _num(params, "cs_radius", r * 1.8)
            tool_expr = f"CounterSinkHole({r}, {cs_r}, {depth})"
            lbl = f"埋头孔 (R{r}/R{cs_r})"
        else:
            tool_expr = f"Hole({r}, {depth})"
            lbl = f"定位孔 (R{r}, 深{depth})"

        if face_ids:
            f_idx = face_ids[0]
            code = (
                f"_f = part.faces()[{f_idx}]\n"
                f"if _f.is_planar:\n"
                f"    part = part - {tool_expr}.translate({x}, {y}, 0).on(_f)\n"
                f"else:\n"
                f"    _c, _n = _f.center(), _f.normal_at()\n"
                f"    part = part - Cylinder({r}, {depth}).rotate(Z, 0).translate(_c.x + {x}, _c.y + {y}, _c.z)"
            )
            return code, f"{lbl} @ Face #{f_idx}", False
        code = f"part = part - Cylinder({r}, {depth}).translate({x}, {y}, 0)"
        return code, lbl, False

    if op == "shell":
        t = _num(params, "thickness", 2.0)
        if face_ids:
            openings_str = ", ".join(f"_faces[{i}]" for i in face_ids)
            code = f"_faces = list(part.faces())\npart = part.shell({t}, openings=[{openings_str}])"
            return code, f"开口抽壳 (壁厚 {t} mm, 开口面 {face_ids})", False
        code = f"part = part.shell({t}, openings=part.faces().top())"
        return code, f"顶面开口抽壳 (壁厚 {t} mm)", False

    if op == "offset":
        dist = _num(params, "distance", 2.0)
        return f"part = part.offset({dist})", f"实体等距偏移 ({dist} mm)", False

    if op == "draft":
        angle = _num(params, "angle", 5.0)
        if face_ids:
            faces_str = ", ".join(f"_faces[{i}]" for i in face_ids)
            code = f"_faces = list(part.faces())\npart = part.draft([{faces_str}], {angle}, Plane.XY)"
            return code, f"选面拔模 ({angle}°, 面 {face_ids})", False
        code = f"_walls = [f for f in part.faces() if abs(f.normal_at().z) < 0.1]\npart = part.draft(_walls, {angle}, Plane.XY)"
        return code, f"侧壁拔模斜度 ({angle}°)", False

    # 6. Booleans, Split, Mirror, Arrays, Transforms
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
        if join:
            return f"part = part + mirror(part, Plane.{plane_name})", f"对称镜像合并 (Plane.{plane_name})", False
        return f"part = mirror(part, Plane.{plane_name})", f"对称镜像 (Plane.{plane_name})", False

    if op == "array":
        nx, ny = _int(params, "count_x", 2), _int(params, "count_y", 2)
        dx, dy = _num(params, "step_x", 35.0), _num(params, "step_y", 35.0)
        code = (
            f"_items = list(GridLocations({dx}, {dy}, {nx}, {ny}) * part)\n"
            f"part = _items[0]\n"
            f"for _it in _items[1:]:\n"
            f"    part = part + _it"
        )
        return code, f"矩形阵列 ({nx}×{ny})", False

    if op == "circular":
        n = _int(params, "count", 6)
        rad = _num(params, "radius", 30.0)
        code = (
            f"_items = list(PolarLocations({rad}, {n}) * part)\n"
            f"part = _items[0]\n"
            f"for _it in _items[1:]:\n"
            f"    part = part + _it"
        )
        return code, f"圆周环形阵列 ({n} 个, R{rad})", False

    if op in ("translate", "move"):
        dx, dy, dz = _num(params, "dx", 0.0), _num(params, "dy", 0.0), _num(params, "dz", 0.0)
        return f"part = part.translate({dx}, {dy}, {dz})", f"平移 ({dx}, {dy}, {dz})", False

    if op in ("rotate", "rotate3d"):
        axis = _str(params, "axis", "Z").upper()
        if axis not in ("X", "Y", "Z"):
            axis = "Z"
        angle = _num(params, "angle", 45.0)
        return f"part = part.rotate({axis}, {angle})", f"绕 {axis} 轴旋转 ({angle}°)", False

    if op == "scale":
        factor = max(0.01, _num(params, "factor", 1.25))
        return f"part = part.scale({factor})", f"等比缩放 ({factor}x)", False

    if op == "copy":
        dx, dy = _num(params, "offset_x", 50.0), _num(params, "offset_y", 0.0)
        return f"part = part + part.translate({dx}, {dy}, 0)", f"复制并平移 ({dx}, {dy})", False

    # 7. CFD Direct Modeling & Defeaturing Operators
    if op == "remove_fillets":
        if face_ids:
            f_str = ", ".join(f"_faces[{i}]" for i in face_ids)
            code = f"_faces = list(part.faces())\npart = part.remove_fillets([{f_str}])"
            return code, f"擦除选定圆角面 ({face_ids})", False
        code = (
            "_fillets = [f for f in part.faces() if not f.is_planar]\n"
            "if _fillets:\n"
            "    part = part.remove_fillets(_fillets)"
        )
        return code, "一键去圆角特征 (Remove Fillets)", False

    if op == "remove_faces":
        if not face_ids:
            raise ValueError("请先在视口中选择要移除并愈合的特征面（如孔内壁面或凹槽面）")
        f_str = ", ".join(f"_faces[{i}]" for i in face_ids)
        code = f"_faces = list(part.faces())\npart = part.remove_faces([{f_str}])"
        return code, f"移除特征面并愈合 ({face_ids})", False

    if op == "cavity_extraction":
        code = (
            "_bb = part.bbox()\n"
            "_env = Box(_bb.size[0], _bb.size[1], _bb.size[2]).translate(_bb.center.x, _bb.center.y, _bb.center.z)\n"
            "part = _env - part"
        )
        return code, "CFD 内流体域水密提取 (Cavity Extraction)", False

    if op == "heal":
        return "part = part.heal()", "几何拓扑自动修复与缝合 (Heal)", False

    raise ValueError(f"未知的几何建模算子: {operator_id}")
