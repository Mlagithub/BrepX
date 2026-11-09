"""Turbomachinery domain operators for fluid machinery modeling in BrepX."""

from __future__ import annotations

import math
from typing import Any

from backend.core.command import is_solid, is_valid, volume_gt
from backend.core.errors import PreconditionError
from backend.core.params import ParamKind, ParamSpec
from backend.kernel import smlib_bridge
from backend.kernel.registry import OperatorSpec, default_registry

VOLUTE_DOC = """
用途: 生成离心泵与风机专用的阿基米德渐开线空间螺旋蜗壳水体或外壳
场景: 离心流体机械内部扩散腔道或蜗形集流管
区别: 自动依据螺旋膨胀系数与断面变化规则多截面平滑放样
参数: base_radius(基准起始半径), spiral_k(螺旋膨胀率), turns(回转圈数), throat_radius(截面喉道起始半径), height(流道轴向高)
约束: 半径与回转圈数必须严格大于零
示例: volute(base_radius=40.0, spiral_k=0.18, turns=1.0, throat_radius=12.0)
"""

BLADE_RUNNER_DOC = """
用途: 参数化一步生成离心或轴流流体机械的闭合多叶片转轮/叶轮水密实体
场景: 水轮机、离心泵叶轮、涡轮鼓风机转子
区别: 内部自动生成空间倾角叶片、执行圆周均布阵列并与中心轮毂刚性熔合成单一水密流体实体
参数: hub_radius(轮毂基准半径), tip_radius(叶片外缘半径), height(叶轮轴向高度), blade_count(叶片数，2~60), twist_deg(叶片安装扭转角), thickness(叶片厚度)
约束: 叶轮叶片数必须大于等于 2，外缘半径必须大于轮毂半径
示例: blade_runner(hub_radius=20.0, tip_radius=45.0, height=25.0, blade_count=6, twist_deg=25.0)
"""


def op_volute(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    base_radius = float(params.get("base_radius", 40.0))
    spiral_k = float(params.get("spiral_k", 0.18))
    turns = float(params.get("turns", 1.0))
    throat_radius = float(params.get("throat_radius", 12.0))
    height = float(params.get("height", 30.0))

    if base_radius <= 0 or throat_radius <= 0 or turns <= 0:
        raise PreconditionError("Volute radius and turns parameters must be strictly positive.")

    import smlibpy
    sections = []
    num_pts = 12

    for i in range(num_pts + 1):
        frac = i / float(num_pts)
        theta = frac * turns * 2.0 * math.pi
        r_center = base_radius + spiral_k * theta * 10.0
        r_section = throat_radius + frac * (throat_radius * 0.5)

        cx = r_center * math.cos(theta)
        cy = r_center * math.sin(theta)
        cz = (frac - 0.5) * height * 0.2

        c = smlibpy.Circle(r_section).on(smlibpy.Plane.XZ).rotate(smlibpy.Z, math.degrees(theta)).translate(cx, cy, cz)
        sections.append(c)

    return smlib_bridge.call(smlibpy.loft, sections)


def op_blade_runner(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    hub_radius = float(params.get("hub_radius", 20.0))
    tip_radius = float(params.get("tip_radius", 45.0))
    height = float(params.get("height", 25.0))
    blade_count = int(params.get("blade_count", 6))
    twist_deg = float(params.get("twist_deg", 25.0))
    thickness = float(params.get("thickness", 3.0))

    if blade_count < 2:
        raise PreconditionError(f"blade_count ({blade_count}) must be at least 2.")
    if tip_radius <= hub_radius:
        raise PreconditionError(
            f"tip_radius ({tip_radius}) must be strictly greater than hub_radius ({hub_radius})."
        )

    import smlibpy
    hub = smlib_bridge.call(smlibpy.Cylinder, hub_radius, height).translate(0, 0, height / 2.0)

    blade_span = tip_radius - hub_radius + 6.0
    blade_center_x = hub_radius + (blade_span / 2.0) - 3.0
    blade_height = height * 0.8

    single_blade = (
        smlib_bridge.call(smlibpy.Box, blade_span, thickness, blade_height)
        .translate(blade_center_x, 0, height / 2.0)
        .rotate(smlibpy.Z, twist_deg)
    )

    accum = hub
    step_angle = 360.0 / float(blade_count)
    for i in range(blade_count):
        blade_i = smlib_bridge.call(single_blade.rotate, smlibpy.Z, i * step_angle)
        accum = smlib_bridge.call(lambda a=accum, b=blade_i: a + b)

    return accum


spec_volute = OperatorSpec(
    op="volute",
    category="turbomachinery",
    produces="solid",
    params={
        "base_radius": ParamSpec(ParamKind.FLOAT, default=40.0, min=1e-6, unit="mm"),
        "spiral_k": ParamSpec(ParamKind.FLOAT, default=0.18, min=1e-6),
        "turns": ParamSpec(ParamKind.FLOAT, default=1.0, min=0.1, max=10.0),
        "throat_radius": ParamSpec(ParamKind.FLOAT, default=12.0, min=1e-6, unit="mm"),
        "height": ParamSpec(ParamKind.FLOAT, default=30.0, min=1e-6, unit="mm"),
    },
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid(), volume_gt(0.0)),
    doc=VOLUTE_DOC,
    call=op_volute,
)

spec_blade_runner = OperatorSpec(
    op="blade_runner",
    category="turbomachinery",
    produces="solid",
    params={
        "hub_radius": ParamSpec(ParamKind.FLOAT, default=20.0, min=1e-6, unit="mm"),
        "tip_radius": ParamSpec(ParamKind.FLOAT, default=45.0, min=1e-6, unit="mm"),
        "height": ParamSpec(ParamKind.FLOAT, default=25.0, min=1e-6, unit="mm"),
        "blade_count": ParamSpec(ParamKind.INT, default=6, min=2, max=60),
        "twist_deg": ParamSpec(ParamKind.FLOAT, default=25.0, min=-90.0, max=90.0, unit="deg"),
        "thickness": ParamSpec(ParamKind.FLOAT, default=3.0, min=1e-6, unit="mm"),
    },
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid(), volume_gt(0.0)),
    doc=BLADE_RUNNER_DOC,
    call=op_blade_runner,
)

default_registry().register(spec_volute)
default_registry().register(spec_blade_runner)
