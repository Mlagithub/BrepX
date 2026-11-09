"""Boolean combinations, mirror, and pattern array operators for BrepX."""

from __future__ import annotations

from typing import Any

from backend.core.command import is_solid, is_valid, volume_delta_sign, volume_gt
from backend.core.errors import PreconditionError
from backend.core.params import ParamKind, ParamSpec
from backend.kernel import smlib_bridge
from backend.kernel.registry import OperatorSpec, default_registry

BOOLEAN_CUT_DOC = """
用途: 用工具实体对目标基准实体执行三维布尔减运算
场景: 开挖复杂内腔、型槽切削或外域轮廓抠除
区别: 产生体积净减少，两体必须在空间上具有实体相交交集
参数: 无
约束: 必须同时提供 target 与 tool 实体，两者必须空间相交
示例: boolean_cut()
"""

BOOLEAN_JOIN_DOC = """
用途: 将工具实体与目标基准实体执行三维布尔求并融合运算
场景: 多零部件刚性焊接合并或多特征熔合为一个单一水密实体
区别: 产生体积净增加，接触或相交面内部拓扑被消除融合
参数: 无
约束: 必须同时提供 target 与 tool 实体
示例: boolean_join()
"""

BOOLEAN_INTERSECT_DOC = """
用途: 计算工具实体与目标基准实体的空间共有相交实体
场景: 提取重叠干涉体积、交集模具或有限区域界定
区别: 仅保留两者的空间共同重叠部分，丢弃所有外围部分
参数: 无
约束: 必须同时提供 target 与 tool 实体，且交集体积必须大于零
示例: boolean_intersect()
"""

MIRROR_DOC = """
用途: 将实体沿指定的三维坐标基准面进行对称镜像
场景: 轴对称或左右对称零件的半边建模与整体镜像复制
区别: 产生镜像翻转后的全新实体，坐标关于基准面对称
参数: plane(基准对称面: XY/YZ/XZ)
约束: 基准面必须为合法正交主平面
示例: mirror(plane="YZ")
"""

POLAR_ARRAY_DOC = """
用途: 将实体围绕指定轴向按均布角度进行圆周环形阵列
场景: 叶轮叶片、均匀分布法兰螺栓孔或回转轮盘齿系
区别: 内部自动完成角度步进与实体融合，无需上层写循环
参数: count(阵列总数量，2~360), axis(阵列回转轴: X/Y/Z), total_angle(阵列总跨度角), merge(是否熔合成一体)
约束: count 必须大于等于 2
示例: polar_array(count=6, axis="Z", total_angle=360.0, merge=True)
"""

GRID_ARRAY_DOC = """
用途: 将实体沿正交网格方向进行二维线性矩形阵列
场景: 散热器翅片阵列、孔板网格或蜂窝排列结构
区别: 沿 X 与 Y 轴等间距多重复制分布
参数: count_x(X向个数), count_y(Y向个数), spacing_x(X向间距), spacing_y(Y向间距), merge(是否融合)
约束: 各方向计数必须至少为 1
示例: grid_array(count_x=2, count_y=2, spacing_x=30.0, spacing_y=30.0, merge=True)
"""


def op_boolean_cut(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    base = target_handle or geometry
    tool = tool_handle
    if base is None or tool is None:
        raise PreconditionError("boolean_cut requires both a base target and a cutting tool.")
    return smlib_bridge.call(lambda: base - tool)


def op_boolean_join(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    base = target_handle or geometry
    tool = tool_handle
    if base is None or tool is None:
        raise PreconditionError("boolean_join requires both a base target and a joining tool.")
    return smlib_bridge.call(lambda: base + tool)


def op_boolean_intersect(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    base = target_handle or geometry
    tool = tool_handle
    if base is None or tool is None:
        raise PreconditionError("boolean_intersect requires both a base target and an intersecting tool.")
    return smlib_bridge.call(base.intersect, tool)


def op_mirror(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    part = target_handle or geometry
    if part is None:
        raise PreconditionError("Mirror operator requires an existing geometry.")

    plane_str = str(params.get("plane", "YZ")).upper()
    import smlibpy
    plane_map = {"XY": smlibpy.Plane.XY, "YZ": smlibpy.Plane.YZ, "XZ": smlibpy.Plane.XZ}
    plane = plane_map.get(plane_str, smlibpy.Plane.YZ)
    return smlib_bridge.call(part.mirror, plane)


def op_polar_array(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    part = target_handle or geometry
    if part is None:
        raise PreconditionError("polar_array operator requires an existing geometry.")

    count = int(params.get("count", 6))
    if count < 2:
        raise PreconditionError("polar_array count must be at least 2.")

    axis_str = str(params.get("axis", "Z")).upper()
    axis_const = getattr(smlib_bridge, axis_str, smlib_bridge.Z)

    total_angle = float(params.get("total_angle", 360.0))
    step_angle = total_angle / float(count)
    merge = bool(params.get("merge", True))

    clones = [part]
    for i in range(1, count):
        ang = step_angle * i
        clones.append(smlib_bridge.call(part.rotate, axis_const, ang))

    if not merge:
        return clones[-1]

    accum = clones[0]
    for item in clones[1:]:
        accum = smlib_bridge.call(lambda a=accum, b=item: a + b)
    return accum


def op_grid_array(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    part = target_handle or geometry
    if part is None:
        raise PreconditionError("grid_array operator requires an existing geometry.")

    count_x = max(1, int(params.get("count_x", 2)))
    count_y = max(1, int(params.get("count_y", 2)))
    spacing_x = float(params.get("spacing_x", 30.0))
    spacing_y = float(params.get("spacing_y", 30.0))
    merge = bool(params.get("merge", True))

    items = []
    for ix in range(count_x):
        for iy in range(count_y):
            dx = ix * spacing_x
            dy = iy * spacing_y
            items.append(smlib_bridge.call(part.translate, dx, dy, 0.0))

    if not merge or not items:
        return items[-1] if items else part

    accum = items[0]
    for item in items[1:]:
        accum = smlib_bridge.call(lambda a=accum, b=item: a + b)
    return accum


spec_boolean_cut = OperatorSpec(
    op="boolean_cut",
    category="pattern",
    produces="solid",
    params={},
    needs_target=True,
    needs_tool=True,
    default_assertions=(is_valid(), is_solid(), volume_delta_sign(-1)),
    doc=BOOLEAN_CUT_DOC,
    call=op_boolean_cut,
)

spec_boolean_join = OperatorSpec(
    op="boolean_join",
    category="pattern",
    produces="solid",
    params={},
    needs_target=True,
    needs_tool=True,
    default_assertions=(is_valid(), is_solid(), volume_delta_sign(1)),
    doc=BOOLEAN_JOIN_DOC,
    call=op_boolean_join,
)

spec_boolean_intersect = OperatorSpec(
    op="boolean_intersect",
    category="pattern",
    produces="solid",
    params={},
    needs_target=True,
    needs_tool=True,
    default_assertions=(is_valid(), is_solid(), volume_gt(0.0)),
    doc=BOOLEAN_INTERSECT_DOC,
    call=op_boolean_intersect,
)

spec_mirror = OperatorSpec(
    op="mirror",
    category="pattern",
    produces="solid",
    params={"plane": ParamSpec(ParamKind.ENUM, default="YZ", choices=("XY", "YZ", "XZ"))},
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=MIRROR_DOC,
    call=op_mirror,
)

spec_polar_array = OperatorSpec(
    op="polar_array",
    category="pattern",
    produces="solid",
    params={
        "count": ParamSpec(ParamKind.INT, default=6, min=2, max=360),
        "axis": ParamSpec(ParamKind.ENUM, default="Z", choices=("X", "Y", "Z")),
        "total_angle": ParamSpec(ParamKind.FLOAT, default=360.0, min=1.0, max=360.0, unit="deg"),
        "merge": ParamSpec(ParamKind.BOOL, default=True),
    },
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=POLAR_ARRAY_DOC,
    call=op_polar_array,
)

spec_grid_array = OperatorSpec(
    op="grid_array",
    category="pattern",
    produces="solid",
    params={
        "count_x": ParamSpec(ParamKind.INT, default=2, min=1, max=100),
        "count_y": ParamSpec(ParamKind.INT, default=2, min=1, max=100),
        "spacing_x": ParamSpec(ParamKind.FLOAT, default=30.0, unit="mm"),
        "spacing_y": ParamSpec(ParamKind.FLOAT, default=30.0, unit="mm"),
        "merge": ParamSpec(ParamKind.BOOL, default=True),
    },
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=GRID_ARRAY_DOC,
    call=op_grid_array,
)

default_registry().register(spec_boolean_cut)
default_registry().register(spec_boolean_join)
default_registry().register(spec_boolean_intersect)
default_registry().register(spec_mirror)
default_registry().register(spec_polar_array)
default_registry().register(spec_grid_array)
