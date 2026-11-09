"""Geometric feature modification operators for BrepX."""

from __future__ import annotations

from typing import Any

from backend.core.command import is_solid, is_valid, volume_delta_sign
from backend.core.errors import PreconditionError
from backend.core.params import ParamKind, ParamSpec
from backend.kernel import smlib_bridge
from backend.kernel.registry import OperatorSpec, default_registry

EXTRUDE_DOC = """
用途: 选定平面拓扑面沿其法向拉伸增加凸台或反向切削挖槽
场景: 在已有实体表面增减特征或构筑台阶结构
区别: 依赖现有拓扑平面作为截面基准，正值并集，负值差集
参数: height(拉伸高度，正值凸台，负值挖槽)
约束: 目标面必须为严格平面(is_planar=True)，高度绝对值必须大于零 (abs > 1e-6)
示例: extrude(height=10.0)
"""

HOLE_DOC = """
用途: 在指定平面面上打出指定半径与深度的圆柱沉孔
场景: 在阀体、法兰或端盖表面开设螺栓孔或流通通道
区别: 几何位置自动对齐目标面中心并贴合减去，非平面无法贴合
参数: radius(孔半径), depth(孔深度)
约束: 目标面必须为平面面，半径与深度必须大于零
示例: hole(radius=6.0, depth=40.0)
"""

FILLET_DOC = """
用途: 对选中的拓扑特征边施加圆弧过渡平滑倒圆角
场景: 降低机械工件应力集中或符合流动边界层光滑需求
区别: 产生过渡 NURBS 圆角面，区别于斜切倒角
参数: radius(圆角过渡半径)
约束: 半径值必须严格大于零且不得超过局部几何曲率上限
示例: fillet(radius=4.0)
"""

CHAMFER_DOC = """
用途: 对选中的拓扑特征边施加对称斜切倒角
场景: 去除机械毛刺或制作装配引导斜边
区别: 产生平面斜切面，区别于曲面圆角过渡
参数: distance(倒角沿各相邻面的切削距离)
约束: 距离值必须严格大于零且不得超过局部几何尺寸
示例: chamfer(distance=3.0)
"""

SHELL_DOC = """
用途: 掏空实体内部并以指定面作为开口，保留等厚均匀壳体
场景: 制作管道外壁、壳体零件或薄壁流体流动夹套
区别: 整体等厚掏空并消除开口面，不同于局部沉孔切削
参数: thickness(均匀壳体壁厚)
约束: 目标面必须作为开口指定，壁厚必须大于零且小于实体尺寸
示例: shell(thickness=2.0)
"""


def op_extrude(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    if geometry is None:
        raise PreconditionError("Extrude operator requires an existing base geometry.")
    if target_handle is None:
        raise PreconditionError("Extrude operator requires a target face.")

    is_planar = getattr(target_handle, "is_planar", False)
    if not is_planar:
        raise PreconditionError("Extrude target must be a planar face.")

    height = float(params.get("height", -1e-9))
    if abs(height) < 1e-6:
        raise PreconditionError("Extrude height magnitude must be strictly greater than 1e-6.")

    ext_tool = smlib_bridge.call(target_handle.extrude, height)
    if height > 0:
        return smlib_bridge.call(lambda: geometry + ext_tool)
    return smlib_bridge.call(lambda: geometry - ext_tool)


def op_hole(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    if geometry is None:
        raise PreconditionError("Hole operator requires an existing base geometry.")
    if target_handle is None:
        raise PreconditionError("Hole operator requires a target face.")

    is_planar = getattr(target_handle, "is_planar", False)
    if not is_planar:
        raise PreconditionError("非平面面不可贴合，无法在非平面面上打孔。")

    radius = float(params.get("radius", 6.0))
    depth = float(params.get("depth", 40.0))

    hole_tool = smlib_bridge.call(lambda: smlib_bridge.Hole(radius, depth).on(target_handle))
    return smlib_bridge.call(lambda: geometry - hole_tool)


def op_fillet(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    if geometry is None:
        raise PreconditionError("Fillet operator requires an existing base geometry.")
    if target_handle is None:
        raise PreconditionError("Fillet operator requires target edge(s).")

    radius = float(params.get("radius", 4.0))
    edges = list(target_handle) if hasattr(target_handle, "__iter__") else [target_handle]
    return smlib_bridge.call(geometry.fillet, edges, radius)


def op_chamfer(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    if geometry is None:
        raise PreconditionError("Chamfer operator requires an existing base geometry.")
    if target_handle is None:
        raise PreconditionError("Chamfer operator requires target edge(s).")

    distance = float(params.get("distance", 3.0))
    edges = list(target_handle) if hasattr(target_handle, "__iter__") else [target_handle]
    return smlib_bridge.call(geometry.chamfer, edges, distance)


def op_shell(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    if geometry is None:
        raise PreconditionError("Shell operator requires an existing base geometry.")
    if target_handle is None:
        raise PreconditionError("Shell operator requires an opening target face.")

    thickness = float(params.get("thickness", 2.0))
    openings = list(target_handle) if hasattr(target_handle, "__iter__") else [target_handle]
    return smlib_bridge.call(geometry.shell, thickness, openings=openings)


spec_extrude = OperatorSpec(
    op="extrude",
    category="feature",
    produces="solid",
    params={"height": ParamSpec(ParamKind.FLOAT, default=10.0, unit="mm")},
    needs_target=True,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=EXTRUDE_DOC,
    call=op_extrude,
)

spec_hole = OperatorSpec(
    op="hole",
    category="feature",
    produces="solid",
    params={
        "radius": ParamSpec(ParamKind.FLOAT, default=6.0, min=1e-6, unit="mm"),
        "depth": ParamSpec(ParamKind.FLOAT, default=40.0, min=1e-6, unit="mm"),
    },
    needs_target=True,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid(), volume_delta_sign(-1)),
    doc=HOLE_DOC,
    call=op_hole,
)

spec_fillet = OperatorSpec(
    op="fillet",
    category="feature",
    produces="solid",
    params={"radius": ParamSpec(ParamKind.FLOAT, default=4.0, min=1e-6, unit="mm")},
    needs_target=True,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=FILLET_DOC,
    call=op_fillet,
)

spec_chamfer = OperatorSpec(
    op="chamfer",
    category="feature",
    produces="solid",
    params={"distance": ParamSpec(ParamKind.FLOAT, default=3.0, min=1e-6, unit="mm")},
    needs_target=True,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=CHAMFER_DOC,
    call=op_chamfer,
)

spec_shell = OperatorSpec(
    op="shell",
    category="feature",
    produces="solid",
    params={"thickness": ParamSpec(ParamKind.FLOAT, default=2.0, min=1e-6, unit="mm")},
    needs_target=True,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid(), volume_delta_sign(-1)),
    doc=SHELL_DOC,
    call=op_shell,
)

default_registry().register(spec_extrude)
default_registry().register(spec_hole)
default_registry().register(spec_fillet)
default_registry().register(spec_chamfer)
default_registry().register(spec_shell)
