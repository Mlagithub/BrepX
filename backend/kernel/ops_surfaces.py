"""NURBS freeform and profile surfacing operators for BrepX."""

from __future__ import annotations

from typing import Any

from backend.core.command import is_solid, is_valid, volume_gt
from backend.core.errors import PreconditionError
from backend.core.params import ParamKind, ParamSpec
from backend.kernel import smlib_bridge
from backend.kernel.registry import OperatorSpec, default_registry

REVOLVE_DOC = """
用途: 将选定截面轮廓绕指定主轴回转成型为三维实体
场景: 生成回转体、轮毂、盘盖或弯管管壁
区别: 围绕轴线角度扫描，与直线拉伸成型形成互补
参数: angle(回转角，1~360度), axis(回转主轴: X/Y/Z)
约束: 角度必须在 1 到 360 度之间
示例: revolve(angle=360.0, axis="Z")
"""

SWEEP_DOC = """
用途: 将截面轮廓沿指定的引导路径空间扫掠放样成体
场景: 弯曲管道、蛇形流道或异形螺旋流体导向管
区别: 沿任意三维导向线扫掠，不局限于平面直线或同轴圆周
参数: closed(路径是否首尾闭合)
约束: 需提供截面与导引路径
示例: sweep(closed=False)
"""

LOFT_DOC = """
用途: 在两个或多个空间截面之间放样平滑过渡实体
场景: 渐变截面喷嘴、叶轮叶片身段过渡或方圆异径接头
区别: 具有截面形态插值特性，可连接拓扑结构不同的轮廓面
参数: ruled(是否采用直纹连接而非光滑过渡)
约束: 截面数量必须至少为两个
示例: loft(ruled=False)
"""

DRAFT_DOC = """
用途: 为实体选定侧壁面施加拔模斜度
场景: 铸造件出模斜度设计或流道轻微收缩角调整
区别: 围绕中性基准面进行夹角旋转倾斜，顶底面通常保持不动
参数: angle(拔模角，-45~45度), neutral_plane(基准中性面: XY/YZ/XZ)
约束: 角度在-45到45度之间，目标面不得平行于中性面
示例: draft(angle=5.0, neutral_plane="XY")
"""

OFFSET_DOC = """
用途: 对实体整体表面施加等距外扩或内缩偏移
场景: 制造加工余量增加、密封间隙预留或几何等距膨胀
区别: 全表面法向等距膨胀，不改变曲面局部法向连续性
参数: distance(偏移距离，正向外扩，负向内缩)
约束: 偏移距离绝对值不得过大导致自交 (abs > 1e-6)
示例: offset(distance=2.0)
"""


def op_revolve(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    profile = target_handle or geometry
    if profile is None:
        raise PreconditionError("Revolve operator requires a profile geometry or target face.")

    angle = float(params.get("angle", 360.0))
    axis_str = str(params.get("axis", "Z")).upper()
    axis_const = getattr(smlib_bridge, axis_str, smlib_bridge.Z)
    return smlib_bridge.call(profile.revolve, axis_const, angle)


def op_sweep(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    profile = target_handle or geometry
    path = tool_handle
    if profile is None or path is None:
        raise PreconditionError("Sweep operator requires a profile (target) and a path (tool).")

    import smlibpy
    return smlib_bridge.call(smlibpy.sweep, profile, path)


def op_loft(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    sections = []
    if target_handle is not None:
        sections.extend(list(target_handle) if hasattr(target_handle, "__iter__") else [target_handle])
    if tool_handle is not None:
        sections.extend(list(tool_handle) if hasattr(tool_handle, "__iter__") else [tool_handle])
    if len(sections) < 2 and hasattr(geometry, "faces"):
        sections = list(geometry.faces())

    if len(sections) < 2:
        raise PreconditionError(f"Loft requires at least 2 profile sections, found {len(sections)}.")

    ruled = bool(params.get("ruled", False))
    import smlibpy
    return smlib_bridge.call(smlibpy.loft, sections, ruled=ruled)


def op_draft(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    if geometry is None or target_handle is None:
        raise PreconditionError("Draft operator requires base geometry and target face(s).")

    angle = float(params.get("angle", 5.0))
    plane_str = str(params.get("neutral_plane", "XY")).upper()
    import smlibpy
    plane_map = {"XY": smlibpy.Plane.XY, "YZ": smlibpy.Plane.YZ, "XZ": smlibpy.Plane.XZ}
    plane = plane_map.get(plane_str, smlibpy.Plane.XY)

    faces = list(target_handle) if hasattr(target_handle, "__iter__") else [target_handle]
    return smlib_bridge.call(geometry.draft, faces, angle, plane)


def op_offset(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    if geometry is None:
        raise PreconditionError("Offset operator requires an existing base geometry.")

    distance = float(params.get("distance", 2.0))
    if abs(distance) < 1e-6:
        raise PreconditionError("Offset distance magnitude must be strictly greater than 1e-6.")
    return smlib_bridge.call(geometry.offset, distance)


spec_revolve = OperatorSpec(
    op="revolve",
    category="surface",
    produces="solid",
    params={
        "angle": ParamSpec(ParamKind.FLOAT, default=360.0, min=1.0, max=360.0, unit="deg"),
        "axis": ParamSpec(ParamKind.ENUM, default="Z", choices=("X", "Y", "Z")),
    },
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid(), volume_gt(0.0)),
    doc=REVOLVE_DOC,
    call=op_revolve,
)

spec_sweep = OperatorSpec(
    op="sweep",
    category="surface",
    produces="solid",
    params={"closed": ParamSpec(ParamKind.BOOL, default=False)},
    needs_target=True,
    needs_tool=True,
    default_assertions=(is_valid(), is_solid(), volume_gt(0.0)),
    doc=SWEEP_DOC,
    call=op_sweep,
)

spec_loft = OperatorSpec(
    op="loft",
    category="surface",
    produces="solid",
    params={"ruled": ParamSpec(ParamKind.BOOL, default=False)},
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid(), volume_gt(0.0)),
    doc=LOFT_DOC,
    call=op_loft,
)

spec_draft = OperatorSpec(
    op="draft",
    category="surface",
    produces="solid",
    params={
        "angle": ParamSpec(ParamKind.FLOAT, default=5.0, min=-45.0, max=45.0, unit="deg"),
        "neutral_plane": ParamSpec(ParamKind.ENUM, default="XY", choices=("XY", "YZ", "XZ")),
    },
    needs_target=True,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=DRAFT_DOC,
    call=op_draft,
)

spec_offset = OperatorSpec(
    op="offset",
    category="surface",
    produces="solid",
    params={"distance": ParamSpec(ParamKind.FLOAT, default=2.0, unit="mm")},
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=OFFSET_DOC,
    call=op_offset,
)

default_registry().register(spec_revolve)
default_registry().register(spec_sweep)
default_registry().register(spec_loft)
default_registry().register(spec_draft)
default_registry().register(spec_offset)
