"""Geometric primitive operators for BrepX."""

from __future__ import annotations

from typing import Any

from backend.core.command import is_solid, is_valid, volume_gt
from backend.core.errors import PreconditionError
from backend.core.params import ParamKind, ParamSpec
from backend.kernel import smlib_bridge
from backend.kernel.registry import OperatorSpec, default_registry

BOX_DOC = """
用途: 创建规则长方体三维实心工件
场景: 初始化基准几何工件或毛坯体
区别: 与拉伸特征不同，作为无前序依赖的根部基础实体生成
参数: length(长度，X方向), width(宽度，Y方向), height(高度，Z方向)
约束: 所有尺寸数值必须严格大于零 (min=1e-6)
示例: box(length=60.0, width=40.0, height=20.0)
"""

CYLINDER_DOC = """
用途: 创建轴对称实心圆柱体工件
场景: 初始化轴类、法兰或管道回转基准工件
区别: 侧面为单一回转柱面，顶底面为成对平行圆面
参数: radius(底面半径), height(圆柱柱高，沿Z轴正向)
约束: 半径与柱高数值必须严格大于零 (min=1e-6)
示例: cylinder(radius=20.0, height=50.0)
"""

SPHERE_DOC = """
用途: 创建原点为中心的三维实心球体
场景: 阀门球体、轴承滚动体或流场扰流球
区别: 表面为单一封闭回转球面，无拓扑平面
参数: radius(球体半径)
约束: 半径数值必须严格大于零 (min=1e-6)
示例: sphere(radius=25.0)
"""

CONE_DOC = """
用途: 创建实心圆台或圆锥体工件
场景: 渐缩管、喷嘴喉道过渡或导向斜顶
区别: 具有不同大小的两个底面圆半径，半径为0时退化为顶点圆锥
参数: radius1(底面下半径), radius2(顶面上半径), height(圆台高)
约束: 半径与高度必须严格大于等于零，高度大于零
示例: cone(radius1=20.0, radius2=10.0, height=40.0)
"""

TORUS_DOC = """
用途: 创建实心圆环体工件
场景: 密封圈、环形流道或管道转弯夹套
区别: 具有主半径与截面圆副半径两个同轴回转参数
参数: radius_major(圆环中心线主回转半径), radius_minor(截面管径副半径)
约束: 副半径必须严格小于主半径 (radius_minor < radius_major)
示例: torus(radius_major=30.0, radius_minor=8.0)
"""

WEDGE_DOC = """
用途: 创建楔形斜切三维工件
场景: 导流板、分流斜块或三角基准支座
区别: 顶部平顶长度小于底部长度，形成平缓单向斜面
参数: length(底部X向长), width(底部Y向宽), height(Z向高), top_length(顶部平顶长)
约束: 顶部平顶长度不得大于底长 (top_length <= length)
示例: wedge(length=60.0, width=40.0, height=25.0, top_length=20.0)
"""


def op_box(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    length = float(params.get("length", 60.0))
    width = float(params.get("width", 40.0))
    height = float(params.get("height", 20.0))
    return smlib_bridge.call(smlib_bridge.Box, length, width, height)


def op_cylinder(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    radius = float(params.get("radius", 20.0))
    height = float(params.get("height", 50.0))
    return smlib_bridge.call(smlib_bridge.Cylinder, radius, height)


def op_sphere(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    radius = float(params.get("radius", 25.0))
    return smlib_bridge.call(smlib_bridge.Sphere, radius)


def op_cone(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    radius1 = float(params.get("radius1", 20.0))
    radius2 = float(params.get("radius2", 10.0))
    height = float(params.get("height", 40.0))
    return smlib_bridge.call(smlib_bridge.Cone, radius1, radius2, height)


def op_torus(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    radius_major = float(params.get("radius_major", 30.0))
    radius_minor = float(params.get("radius_minor", 8.0))
    if radius_minor >= radius_major:
        raise PreconditionError(
            f"Torus radius_minor ({radius_minor}) must be strictly less than radius_major ({radius_major})."
        )
    return smlib_bridge.call(smlib_bridge.Torus, radius_major, radius_minor)


def op_wedge(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    length = float(params.get("length", 60.0))
    width = float(params.get("width", 40.0))
    height = float(params.get("height", 25.0))
    top_length = float(params.get("top_length", 20.0))
    if top_length > length:
        raise PreconditionError(
            f"Wedge top_length ({top_length}) cannot exceed base length ({length})."
        )
    return smlib_bridge.call(smlib_bridge.Wedge, length, width, height, top_length)


spec_box = OperatorSpec(
    op="box",
    category="primitive",
    produces="solid",
    params={
        "length": ParamSpec(ParamKind.FLOAT, default=60.0, min=1e-6, unit="mm"),
        "width": ParamSpec(ParamKind.FLOAT, default=40.0, min=1e-6, unit="mm"),
        "height": ParamSpec(ParamKind.FLOAT, default=20.0, min=1e-6, unit="mm"),
    },
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid(), volume_gt(0.0)),
    doc=BOX_DOC,
    call=op_box,
)

spec_cylinder = OperatorSpec(
    op="cylinder",
    category="primitive",
    produces="solid",
    params={
        "radius": ParamSpec(ParamKind.FLOAT, default=20.0, min=1e-6, unit="mm"),
        "height": ParamSpec(ParamKind.FLOAT, default=50.0, min=1e-6, unit="mm"),
    },
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid(), volume_gt(0.0)),
    doc=CYLINDER_DOC,
    call=op_cylinder,
)

spec_sphere = OperatorSpec(
    op="sphere",
    category="primitive",
    produces="solid",
    params={"radius": ParamSpec(ParamKind.FLOAT, default=25.0, min=1e-6, unit="mm")},
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid(), volume_gt(0.0)),
    doc=SPHERE_DOC,
    call=op_sphere,
)

spec_cone = OperatorSpec(
    op="cone",
    category="primitive",
    produces="solid",
    params={
        "radius1": ParamSpec(ParamKind.FLOAT, default=20.0, min=0.0, unit="mm"),
        "radius2": ParamSpec(ParamKind.FLOAT, default=10.0, min=0.0, unit="mm"),
        "height": ParamSpec(ParamKind.FLOAT, default=40.0, min=1e-6, unit="mm"),
    },
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid(), volume_gt(0.0)),
    doc=CONE_DOC,
    call=op_cone,
)

spec_torus = OperatorSpec(
    op="torus",
    category="primitive",
    produces="solid",
    params={
        "radius_major": ParamSpec(ParamKind.FLOAT, default=30.0, min=1e-6, unit="mm"),
        "radius_minor": ParamSpec(ParamKind.FLOAT, default=8.0, min=1e-6, unit="mm"),
    },
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid(), volume_gt(0.0)),
    doc=TORUS_DOC,
    call=op_torus,
)

spec_wedge = OperatorSpec(
    op="wedge",
    category="primitive",
    produces="solid",
    params={
        "length": ParamSpec(ParamKind.FLOAT, default=60.0, min=1e-6, unit="mm"),
        "width": ParamSpec(ParamKind.FLOAT, default=40.0, min=1e-6, unit="mm"),
        "height": ParamSpec(ParamKind.FLOAT, default=25.0, min=1e-6, unit="mm"),
        "top_length": ParamSpec(ParamKind.FLOAT, default=20.0, min=0.0, unit="mm"),
    },
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid(), volume_gt(0.0)),
    doc=WEDGE_DOC,
    call=op_wedge,
)

default_registry().register(spec_box)
default_registry().register(spec_cylinder)
default_registry().register(spec_sphere)
default_registry().register(spec_cone)
default_registry().register(spec_torus)
default_registry().register(spec_wedge)
