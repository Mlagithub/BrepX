"""Spatial transformation and geometric slicing operators for BrepX."""

from __future__ import annotations

from typing import Any

from backend.core.command import is_solid, is_valid
from backend.core.errors import PreconditionError
from backend.core.params import ParamKind, ParamSpec
from backend.kernel import smlib_bridge
from backend.kernel.registry import OperatorSpec, default_registry

TRANSLATE_DOC = """
用途: 将实体沿空间三维向量进行刚体平移
场景: 工件空间对齐、相对装配定位或间隙调整
区别: 纯粹刚体平移，拓扑连接关系与体积面积严格保持不变
参数: dx(X向位移), dy(Y向位移), dz(Z向位移)
约束: 位移可为任意实数
示例: translate(dx=10.0, dy=0.0, dz=5.0)
"""

ROTATE_DOC = """
用途: 将实体绕指定空间轴向与角度进行刚体旋转
场景: 工件姿态调整、配合面对齐或角度偏转
区别: 纯粹刚体旋转，拓扑关系与体积保持守恒
参数: angle(旋转角度), axis(旋转主轴: X/Y/Z)
约束: 角度在-360到360度之间
示例: rotate(angle=45.0, axis="Z")
"""

SCALE_DOC = """
用途: 对实体以原点或局部几何中心为基准进行等比例缩放
场景: 单位换算、热膨胀收缩率补偿或几何模具缩放
区别: 整体等比放大或缩小，体积按比例系数的三次方缩放
参数: factor(缩放系数，严格大于零)
约束: 缩放系数必须严格大于零 (factor > 1e-6)
示例: scale(factor=2.0)
"""

SECTION_DOC = """
用途: 使用指定基准面对三维实体进行截面切割提取二维截面草图
场景: 流道特征截面分析、水力截线提取或二维轮廓投影
区别: 产物为二维平面草图/面，而非三维实心体
参数: plane(切分基准面: XY/YZ/XZ), offset(基准面沿法向偏移距)
约束: 切割面必须穿过实体内部产生相交截面
示例: section(plane="XY", offset=0.0)
"""

SPLIT_DOC = """
用途: 使用指定基准面对实体进行剖切并保留选定侧的半部分
场景: 半剖观察内部流道、分模面剖切或对称半模构建
区别: 切除指定侧实体并对剖截面自动封盖保持水密
参数: plane(剖切面: XY/YZ/XZ), offset(剖切面偏移距), keep(保留侧: positive/negative/both)
约束: 剖切基准面必须与实体发生物理相交
示例: split(plane="XY", offset=0.0, keep="positive")
"""


def op_translate(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    part = target_handle or geometry
    if part is None:
        raise PreconditionError("Translate operator requires an existing geometry.")

    dx = float(params.get("dx", 0.0))
    dy = float(params.get("dy", 0.0))
    dz = float(params.get("dz", 0.0))
    return smlib_bridge.call(part.translate, dx, dy, dz)


def op_rotate(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    part = target_handle or geometry
    if part is None:
        raise PreconditionError("Rotate operator requires an existing geometry.")

    angle = float(params.get("angle", 0.0))
    axis_str = str(params.get("axis", "Z")).upper()
    axis_const = getattr(smlib_bridge, axis_str, smlib_bridge.Z)
    return smlib_bridge.call(part.rotate, axis_const, angle)


def op_scale(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    part = target_handle or geometry
    if part is None:
        raise PreconditionError("Scale operator requires an existing geometry.")

    factor = float(params.get("factor", 1.0))
    if factor < 1e-6:
        raise PreconditionError("Scale factor must be strictly greater than 1e-6.")
    return smlib_bridge.call(part.scale, factor)


def op_section(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> Any:
    part = target_handle or geometry
    if part is None:
        raise PreconditionError("Section operator requires an existing geometry.")

    plane_str = str(params.get("plane", "XY")).upper()
    offset = float(params.get("offset", 0.0))

    import smlibpy
    plane_map = {"XY": smlibpy.Plane.XY, "YZ": smlibpy.Plane.YZ, "XZ": smlibpy.Plane.XZ}
    plane = plane_map.get(plane_str, smlibpy.Plane.XY)
    if abs(offset) > 1e-6:
        plane = plane.offset(offset)

    return smlib_bridge.call(part.section, plane)


def op_split(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    part = target_handle or geometry
    if part is None:
        raise PreconditionError("Split operator requires an existing geometry.")

    plane_str = str(params.get("plane", "XY")).upper()
    offset = float(params.get("offset", 0.0))

    import smlibpy
    plane_map = {"XY": smlibpy.Plane.XY, "YZ": smlibpy.Plane.YZ, "XZ": smlibpy.Plane.XZ}
    plane = plane_map.get(plane_str, smlibpy.Plane.XY)
    if abs(offset) > 1e-6:
        plane = plane.offset(offset)

    return smlib_bridge.call(part.split, plane)


spec_translate = OperatorSpec(
    op="translate",
    category="pattern",
    produces="solid",
    params={
        "dx": ParamSpec(ParamKind.FLOAT, default=0.0, unit="mm"),
        "dy": ParamSpec(ParamKind.FLOAT, default=0.0, unit="mm"),
        "dz": ParamSpec(ParamKind.FLOAT, default=0.0, unit="mm"),
    },
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=TRANSLATE_DOC,
    call=op_translate,
)

spec_rotate = OperatorSpec(
    op="rotate",
    category="pattern",
    produces="solid",
    params={
        "angle": ParamSpec(ParamKind.FLOAT, default=0.0, min=-360.0, max=360.0, unit="deg"),
        "axis": ParamSpec(ParamKind.ENUM, default="Z", choices=("X", "Y", "Z")),
    },
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=ROTATE_DOC,
    call=op_rotate,
)

spec_scale = OperatorSpec(
    op="scale",
    category="pattern",
    produces="solid",
    params={"factor": ParamSpec(ParamKind.FLOAT, default=1.0, min=1e-6)},
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=SCALE_DOC,
    call=op_scale,
)

spec_section = OperatorSpec(
    op="section",
    category="pattern",
    produces="surface",
    params={
        "plane": ParamSpec(ParamKind.ENUM, default="XY", choices=("XY", "YZ", "XZ")),
        "offset": ParamSpec(ParamKind.FLOAT, default=0.0, unit="mm"),
    },
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(),),
    doc=SECTION_DOC,
    call=op_section,
)

spec_split = OperatorSpec(
    op="split",
    category="pattern",
    produces="solid",
    params={
        "plane": ParamSpec(ParamKind.ENUM, default="XY", choices=("XY", "YZ", "XZ")),
        "offset": ParamSpec(ParamKind.FLOAT, default=0.0, unit="mm"),
        "keep": ParamSpec(ParamKind.ENUM, default="positive", choices=("positive", "negative", "both")),
    },
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=SPLIT_DOC,
    call=op_split,
)

default_registry().register(spec_translate)
default_registry().register(spec_rotate)
default_registry().register(spec_scale)
default_registry().register(spec_section)
default_registry().register(spec_split)
