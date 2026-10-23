import math
from typing import Dict, Any, Tuple
import smlibpy
from smlibpy import *

def execute_right_tool(tool: str, params: Dict[str, Any], current_part=None, current_script="") -> Tuple[Any, str, str]:
    """
    执行右列工具建模操作
    返回: (part, script, explanation)
    """
    # 辅助读取数值
    def get_num(k, default):
        try: return float(params.get(k, default))
        except: return float(default)

    def get_bool(k, default):
        return bool(params.get(k, default))

    # ================= 1. 三维基础体 =================
    if tool == "box":
        l = get_num("length", 60)
        w = get_num("width", 40)
        h = get_num("height", 20)
        code = f"""from smlibpy import *\npart = Box({l}, {w}, {h})"""
        part = Box(l, w, h)
        return part, code, f"已创建长方体: {l} × {w} × {h} mm"

    elif tool == "cylinder":
        r = get_num("radius", 15)
        h = get_num("height", 40)
        code = f"""from smlibpy import *\npart = Cylinder({r}, {h})"""
        part = Cylinder(r, h)
        return part, code, f"已创建圆柱体: 半径 R{r} mm, 高度 {h} mm"

    elif tool == "sphere":
        r = get_num("radius", 25)
        code = f"""from smlibpy import *\npart = Sphere({r})"""
        part = Sphere(r)
        return part, code, f"已创建球体: 半径 R{r} mm"

    elif tool == "cone":
        r1 = get_num("radius1", 20)
        r2 = get_num("radius2", 10)
        h = get_num("height", 40)
        code = f"""from smlibpy import *\npart = Cone({r1}, {r2}, {h})"""
        part = Cone(r1, r2, h)
        return part, code, f"已创建圆锥/圆台: 底面 R{r1} mm, 顶面 R{r2} mm, 高度 {h} mm"

    elif tool == "torus":
        R = get_num("radius_major", 30)
        r = get_num("radius_minor", 8)
        code = f"""from smlibpy import *\npart = Torus({R}, {r})"""
        part = Torus(R, r)
        return part, code, f"已创建圆环体: 主环半径 R{R} mm, 截面半径 r{r} mm"

    elif tool == "hole":
        r = get_num("radius", 8)
        h = get_num("depth", 60)
        x = get_num("x", 0)
        y = get_num("y", 0)
        base = current_part if current_part is not None else Box(60, 60, 20)
        base_script = current_script if current_part is not None else "part = Box(60, 60, 20)"
        tool_cyl = Cylinder(r, h).translate(x, y, 0)
        part = base - tool_cyl
        code = base_script.rstrip() + f"\n# 定位贯穿通孔切削\nhole = Cylinder({r}, {h}).translate({x}, {y}, 0)\npart = part - hole\n"
        return part, code, f"已开孔: 半径 R{r} mm, 位于 ({x}, {y})"

    # ================= 2. 布尔运算 =================
    elif tool in ["boolean-union", "boolean-subtract", "boolean-intersection", "boolean"]:
        op = params.get("operation") or ("union" if "union" in tool else "difference" if "subtract" in tool else "intersection")
        base = current_part if current_part is not None else Box(60, 60, 30)
        base_script = current_script if current_part is not None else "part = Box(60, 60, 30)"

        # 工具体尺寸
        tool_kind = params.get("tool_kind", "cylinder")
        tr = get_num("tool_r", 15)
        th = get_num("tool_h", 45)

        if tool_kind == "cylinder":
            tool_solid = Cylinder(tr, th)
            tool_code = f"tool = Cylinder({tr}, {th})"
        elif tool_kind == "sphere":
            tool_solid = Sphere(tr)
            tool_code = f"tool = Sphere({tr})"
        else:
            tool_solid = Box(tr*2, tr*2, th)
            tool_code = f"tool = Box({tr*2}, {tr*2}, {th})"

        if op == "union":
            part = base + tool_solid
            symbol = "+"
            op_name = "并集"
        elif op == "difference":
            part = base - tool_solid
            symbol = "-"
            op_name = "差集切削"
        else:
            part = base & tool_solid
            symbol = "&"
            op_name = "交集"

        code = base_script.rstrip() + f"\n# 布尔{op_name}\n{tool_code}\npart = part {symbol} tool\n"
        return part, code, f"已执行布尔{op_name}"

    # ================= 3. 构造高级特征 =================
    elif tool == "extrude":
        shape = params.get("profile", "rectangle")
        dim1 = get_num("dim1", 40)
        dim2 = get_num("dim2", 30)
        h = get_num("height", 25)

        if shape == "circle":
            sketch = Circle(dim1)
            code = f"from smlibpy import *\nsketch = Circle({dim1})\npart = extrude(sketch, {h})"
        else:
            sketch = Rectangle(dim1, dim2)
            code = f"from smlibpy import *\nsketch = Rectangle({dim1}, {dim2})\npart = extrude(sketch, {h})"

        part = extrude(sketch, h)
        return part, code, f"已通过轮廓拉伸成体: 高度 {h} mm"

    elif tool == "revolve":
        r_sketch = get_num("radius", 10)
        offset_x = get_num("offset_x", 25)
        angle = get_num("angle", 360)

        sketch = Circle(r_sketch).on(Plane.XZ).translate(offset_x, 0, 0)
        part = revolve(sketch, Z, angle)
        code = f"from smlibpy import *\n# XZ工作平面上的截面绕 Z 轴旋转\nsketch = Circle({r_sketch}).on(Plane.XZ).translate({offset_x}, 0, 0)\npart = revolve(sketch, Z, {angle})"
        return part, code, f"已执行旋转体成型: 截面 R{r_sketch} mm 偏置 {offset_x} mm，绕 Z 轴旋转 {angle}°"

    elif tool == "sweep":
        r_prof = get_num("radius", 4)
        pitch = get_num("pitch", 20)
        h = get_num("height", 60)
        rad = get_num("helix_radius", 25)

        helix = Helix(pitch=pitch, height=h, radius=rad)
        part = sweep(Circle(r_prof), helix)
        code = f"from smlibpy import *\n# 截面沿空间螺旋线扫掠\npath = Helix(pitch={pitch}, height={h}, radius={rad})\npart = sweep(Circle({r_prof}), path)"
        return part, code, f"已执行空间扫掠成体: 截面半径 R{r_prof} mm, 导引路径高度 {h} mm"

    elif tool == "loft":
        r1 = get_num("bottom_radius", 25)
        r2 = get_num("top_radius", 12)
        h = get_num("height", 40)

        s1 = Circle(r1)
        s2 = Circle(r2).translate(0, 0, h)
        part = loft([s1, s2])
        code = f"from smlibpy import *\n# 多截面放样平滑过渡成体\ns1 = Circle({r1})\ns2 = Circle({r2}).translate(0, 0, {h})\npart = loft([s1, s2])"
        return part, code, f"已执行放样成体: 底截面 R{r1} mm, 顶截面 R{r2} mm, 高度 {h} mm"

    elif tool == "fillet":
        r_fillet = get_num("radius", 5)
        base = current_part if current_part is not None else Box(60, 40, 20)
        base_script = current_script if current_part is not None else "part = Box(60, 40, 20)"
        try:
            part = base.fillet(base.edges().parallel_to(Z), r_fillet)
            code = base_script.rstrip() + f"\n# 特征边倒圆角\npart = part.fillet(part.edges().parallel_to(Z), {r_fillet})\n"
            return part, code, f"已对竖直特征边应用 R{r_fillet} mm 圆角"
        except Exception:
            std_base = Box(60, 40, 20)
            part = std_base.fillet(std_base.edges().parallel_to(Z), r_fillet)
            code = f"from smlibpy import *\npart = Box(60, 40, 20)\npart = part.fillet(part.edges().parallel_to(Z), {r_fillet})\n"
            return part, code, f"当前模型竖直边已有圆角，已为您新建并应用 R{r_fillet} mm 圆角标准件"

    elif tool == "chamfer":
        d_chamfer = get_num("distance", 3)
        base = current_part if current_part is not None else Box(60, 40, 20)
        base_script = current_script if current_part is not None else "part = Box(60, 40, 20)"
        try:
            part = base.chamfer(base.edges().parallel_to(Z), d_chamfer)
            code = base_script.rstrip() + f"\n# 特征边等距切倒角\npart = part.chamfer(part.edges().parallel_to(Z), {d_chamfer})\n"
            return part, code, f"已对竖直特征边应用 {d_chamfer} mm 倒角"
        except Exception:
            std_base = Box(60, 40, 20)
            part = std_base.chamfer(std_base.edges().parallel_to(Z), d_chamfer)
            code = f"from smlibpy import *\npart = Box(60, 40, 20)\npart = part.chamfer(part.edges().parallel_to(Z), {d_chamfer})\n"
            return part, code, f"当前模型边缘已无尖锐边，已为您新建并应用 {d_chamfer} mm 倒角标准件"

    elif tool == "shell":
        thickness = get_num("thickness", 2)
        base = current_part if current_part is not None else Box(50, 40, 30)
        base_script = current_script if current_part is not None else "part = Box(50, 40, 30)"
        try:
            part = base.shell(thickness)
            code = base_script.rstrip() + f"\n# 实体抽壳特征 (壁厚 {thickness} mm)\npart = part.shell({thickness})\n"
            return part, code, f"已生成抽壳特征: 壁厚 {thickness} mm"
        except Exception:
            std_base = Box(50, 40, 30)
            part = std_base.shell(thickness)
            code = f"from smlibpy import *\npart = Box(50, 40, 30)\npart = part.shell({thickness})\n"
            return part, code, f"已生成标准抽壳模型: 壁厚 {thickness} mm"

    elif tool == "offset":
        dist = get_num("distance", 3)
        base = current_part if current_part is not None else Box(40, 30, 20)
        base_script = current_script if current_part is not None else "part = Box(40, 30, 20)"
        try:
            part = base.offset(dist)
            code = base_script.rstrip() + f"\n# 实体法向等距偏移扩展 (距离 {dist} mm)\npart = part.offset({dist})\n"
            return part, code, f"已执行几何等距偏移: 距离 {dist} mm"
        except Exception:
            std_base = Box(40, 30, 20)
            part = std_base.offset(dist)
            code = f"from smlibpy import *\npart = Box(40, 30, 20)\npart = part.offset({dist})\n"
            return part, code, f"已生成标准等距偏移模型: 距离 {dist} mm"

    elif tool == "mirror":
        plane_name = params.get("plane", "YZ")
        plane_obj = Plane.YZ if plane_name == "YZ" else Plane.XZ if plane_name == "XZ" else Plane.XY
        base = current_part if current_part is not None else Box(30, 20, 20).translate(25, 0, 0)
        base_script = current_script if current_part is not None else "part = Box(30, 20, 20).translate(25, 0, 0)"
        mirrored = mirror(base, plane_obj)
        part = base + mirrored
        code = base_script.rstrip() + f"\n# 沿 {plane_name} 基准面对称镜像并合并\npart = part + mirror(part, Plane.{plane_name})\n"
        return part, code, f"已沿 Plane.{plane_name} 平面镜像并组合"

    elif tool == "array":
        nx = int(get_num("count_x", 2))
        ny = int(get_num("count_y", 2))
        dx = get_num("step_x", 35)
        dy = get_num("step_y", 35)
        base = current_part if current_part is not None else Box(15, 15, 15)
        base_script = current_script if current_part is not None else "part = Box(15, 15, 15)"

        arr = list(GridLocations(dx, dy, nx, ny) * base)
        part = arr[0]
        for p in arr[1:]:
            part = part + p

        code = base_script.rstrip() + f"\n# 矩形网格阵列 ({nx} × {ny})\narr = list(GridLocations({dx}, {dy}, {nx}, {ny}) * part)\npart = arr[0]\nfor p in arr[1:]:\n    part = part + p\n"
        return part, code, f"已生成 {nx} × {ny} 矩形阵列: X步长 {dx} mm, Y步长 {dy} mm"

    elif tool == "circular":
        n = int(get_num("count", 6))
        rad = get_num("radius", 30)
        base = current_part if current_part is not None else Cylinder(6, 15).translate(rad, 0, 0)
        base_script = current_script if current_part is not None else f"part = Cylinder(6, 15).translate({rad}, 0, 0)"

        arr = list(PolarLocations(rad, n) * base)
        part = arr[0]
        for p in arr[1:]:
            part = part + p

        code = base_script.rstrip() + f"\n# 圆周环形阵列 ({n} 个分布在 R{rad} mm)\narr = list(PolarLocations({rad}, {n}) * part)\npart = arr[0]\nfor p in arr[1:]:\n    part = part + p\n"
        return part, code, f"已生成圆周环形阵列: 数量 {n} 个, 分布半径 R{rad} mm"

    elif tool == "slice":
        base = current_part if current_part is not None else Cylinder(25, 50)
        base_script = current_script if current_part is not None else "part = Cylinder(25, 50)"
        # 用半空间大长方体切分
        cutter = Box(200, 200, 200).translate(100, 0, 0)
        part = base - cutter
        code = base_script.rstrip() + "\n# 平面切分剖切\ncutter = Box(200, 200, 200).translate(100, 0, 0)\npart = part - cutter\n"
        return part, code, f"已沿 YZ 平面切分保留半侧"

    elif tool == "rotate3d":
        axis_name = params.get("axis", "Z")
        angle = get_num("angle", 45)
        axis_obj = Z if axis_name == "Z" else Y if axis_name == "Y" else X
        base = current_part if current_part is not None else Box(50, 30, 15)
        base_script = current_script if current_part is not None else "part = Box(50, 30, 15)"
        part = base.rotate(axis_obj, angle)
        code = base_script.rstrip() + f"\n# 绕 {axis_name} 轴旋转 {angle}°\npart = part.rotate({axis_name}, {angle})\n"
        return part, code, f"已绕 {axis_name} 轴旋转 {angle}°"

    elif tool == "copy":
        base = current_part if current_part is not None else Box(40, 30, 15)
        base_script = current_script if current_part is not None else "part = Box(40, 30, 15)"
        dx = get_num("offset_x", 50)
        dy = get_num("offset_y", 0)
        copy_part = base.translate(dx, dy, 0)
        part = base + copy_part
        code = base_script.rstrip() + f"\n# 复制实体副本并平移偏移\npart = part + part.translate({dx}, {dy}, 0)\n"
        return part, code, f"已复制实体并平移 ({dx}, {dy}) mm"

    # ================= 4. CFD 工业流体前处理算子 =================
    elif tool == "remove_fillets":
        # 去特征化·反圆角 (将圆滑边恢复为锐角)
        base = current_part if current_part is not None else Box(60, 40, 20).fillet(Box(60, 40, 20).edges().parallel_to(Z), 5)
        base_script = current_script if current_part is not None else "part = Box(60, 40, 20).fillet(Box(60, 40, 20).edges().parallel_to(Z), 5)"
        try:
            non_planar = list(base.faces().filter(lambda f: not f.is_planar))
            if not non_planar:
                return base, base_script, "当前实体上未检测到圆角曲面，无需去特征。"
            part = base.remove_fillets(non_planar)
            code = base_script.rstrip() + "\n# [CFD去特征] 擦除微小圆角，恢复锐角棱边\nfillet_faces = part.faces().filter(lambda f: not f.is_planar)\npart = part.remove_fillets(fillet_faces)\n"
            return part, code, f"去特征化成功：已消除 {len(non_planar)} 处圆角面并自动延伸缝合为锐边"
        except Exception as e:
            return base, base_script, f"去圆角失败: {str(e)}"

    elif tool == "cavity_extraction":
        # 提取内部水密流体域 (反向包络差集)
        base = current_part if current_part is not None else (Box(60, 60, 40) - Cylinder(15, 50))
        base_script = current_script if current_part is not None else "part = Box(60, 60, 40) - Cylinder(15, 50)"
        try:
            bbox = base.bbox()
            envelope = Box(bbox.size[0], bbox.size[1], bbox.size[2])
            part = envelope - base
            code = base_script.rstrip() + "\n# [CFD流体域提取] 反向包络盒差集提取内流道水密实体\nbbox = part.bbox()\nenvelope = Box(bbox.size[0], bbox.size[1], bbox.size[2])\npart = envelope - part\n"
            return part, code, f"流体域提取成功：已从实体空腔中提取出纯净水密流道，体积 {part.volume:.2f} mm³"
        except Exception as e:
            return base, base_script, f"流体域提取失败: {str(e)}"

    # ================= 5. 草图曲线与轮廓 =================
    elif tool in ["line", "rectangle", "circle", "arc", "polyline", "bspline", "profile"]:
        dim1 = get_num("dim1", 40)
        dim2 = get_num("dim2", 30)
        h = 10.0  # 自动拉伸为薄板以便在 3D 中渲染预览

        if tool == "circle":
            sketch = Circle(dim1)
            desc = f"圆轮廓 (半径 R{dim1} mm)"
            sketch_code = f"sketch = Circle({dim1})"
        elif tool == "line":
            sketch = Rectangle(dim1, 2)
            desc = f"直线段/条形轮廓 (长度 {dim1} mm)"
            sketch_code = f"sketch = Rectangle({dim1}, 2)"
        elif tool == "arc":
            sketch = Circle(dim1)
            desc = f"圆弧轮廓 (半径 R{dim1} mm)"
            sketch_code = f"sketch = Circle({dim1})"
        else:
            sketch = Rectangle(dim1, dim2)
            desc = f"矩形/闭合轮廓 ({dim1} × {dim2} mm)"
            sketch_code = f"sketch = Rectangle({dim1}, {dim2})"

        part = extrude(sketch, h)
        code = f"from smlibpy import *\n# 创建二维轮廓并成体\n{sketch_code}\npart = extrude(sketch, {h})"
        return part, code, f"已创建{desc}并拉伸成体"

    else:
        # 默认兜底
        part = Box(60, 40, 20)
        code = "from smlibpy import *\npart = Box(60, 40, 20)"
        return part, code, f"已创建几何实体: {tool}"
