"""CFD defeaturing, cavity extraction, and topology healing operators for BrepX."""

from __future__ import annotations

from typing import Any

from backend.core.command import is_solid, is_valid, volume_delta_sign, volume_gt
from backend.core.errors import PreconditionError
from backend.core.params import ParamKind, ParamSpec
from backend.kernel import smlib_bridge
from backend.kernel.registry import OperatorSpec, default_registry

REMOVE_FILLETS_DOC = """
用途: 识别并一键擦除选定或全模型圆角过渡曲面，延伸相邻面恢复锐角棱边
场景: CFD 网格剖分前简化微小几何细节，避免边界层网格畸变严重
区别: 专门处理过渡曲面并执行相交几何延伸闭合，不同于单纯删面
参数: 无
约束: 若指定 target 则仅擦除 target 圆角，未指定则自动全局擦除
示例: remove_fillets()
"""

REMOVE_FACES_DOC = """
用途: 移除选定的特征面（如螺栓孔内壁、盲孔底面或凸台）并由内核自动延伸相邻面完成水密愈合
场景: 消除不需要关心的细小装配螺栓孔、顶针印或工艺槽
区别: 消除孔洞特征会使实体净体积发生增加，相当于特征填平
参数: 无
约束: 必须指定 target 拓扑面，且移除后几何必须仍可闭合愈合
示例: remove_faces()
"""

HEAL_DOC = """
用途: 调用 SMLib 拓扑缝合与容差修复引擎，修复间隙微小面缝隙重构水密性
场景: 外部导入 STEP 模型缝隙超差、微小自交或流形破损修复
区别: 全局公差缝合与破损修补，不改变宏观设计特征
参数: 无
约束: 模型必须具有实体潜质
示例: heal()
"""

CAVITY_EXTRACTION_DOC = """
用途: 自动计算并反向提取零件内部完全封闭的水密内流道流体域实体
场景: 泵阀水体提取、涡轮流动腔体、冷却管道水路直接提取
区别: 采用工业紧凑包围体布尔互补与连通胞拓扑分析，自动产出独立水密流体体
参数: 无
约束: 输入实体必须具有内封闭流道腔体
示例: cavity_extraction()
"""

TAG_BOUNDARY_DOC = """
用途: 为选定的拓扑边界几何表面绑定 CFD 物理流体边界属性条件
场景: 标识水流入口、压力出口、旋转固体壁面或滑移对称面
区别: 作为元数据语义标注操作，不改变几何物理拓扑与实体外形
参数: semantic_type(物理边界类别: inlet/outlet/wall/symmetry/interface/internal), name(物理边界命名标识)
约束: 必须指定 target 拓扑面
示例: tag_boundary(semantic_type="inlet", name="inlet_main")
"""


def op_remove_fillets(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    if geometry is None:
        raise PreconditionError("remove_fillets requires an existing geometry.")

    if target_handle is not None:
        faces = list(target_handle) if hasattr(target_handle, "__iter__") else [target_handle]
        return smlib_bridge.call(geometry.remove_faces, faces)

    return smlib_bridge.call(geometry.remove_fillets)


def op_remove_faces(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    if geometry is None or target_handle is None:
        raise PreconditionError("remove_faces requires base geometry and target face(s).")

    faces = list(target_handle) if hasattr(target_handle, "__iter__") else [target_handle]
    return smlib_bridge.call(geometry.remove_faces, faces)


def op_heal(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    if geometry is None:
        raise PreconditionError("heal requires an existing geometry.")
    return smlib_bridge.call(geometry.heal)


def op_cavity_extraction(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    if geometry is None:
        raise PreconditionError("cavity_extraction requires an existing geometry.")

    import smlibpy
    bb = geometry.bbox()
    envelope = smlib_bridge.call(smlibpy.Box, bb.size.x, bb.size.y, bb.size.z).translate(
        bb.center.x, bb.center.y, bb.center.z
    )

    try:
        flow = smlib_bridge.call(lambda: envelope - geometry)
        if flow.is_valid() and flow.volume > 1e-4:
            return flow
    except Exception as exc_sub:
        _ = type(exc_sub)

    merged = smlib_bridge.call(smlibpy.merge, envelope, geometry)
    cells = sorted(merged.cells(), key=lambda c: c.volume)
    if cells:
        return cells[0]

    raise PreconditionError("Unable to extract cavity: no internal closed fluid domain found.")


def op_tag_boundary(
    geometry: Any,
    target_handle: Any,
    tool_handle: Any,
    params: dict[str, Any],
) -> smlib_bridge.Part:
    if geometry is None or target_handle is None:
        raise PreconditionError("tag_boundary requires base geometry and a target face.")
    return geometry


spec_remove_fillets = OperatorSpec(
    op="remove_fillets",
    category="cfd",
    produces="solid",
    params={},
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=REMOVE_FILLETS_DOC,
    call=op_remove_fillets,
)

spec_remove_faces = OperatorSpec(
    op="remove_faces",
    category="cfd",
    produces="solid",
    params={},
    needs_target=True,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid(), volume_delta_sign(1)),
    doc=REMOVE_FACES_DOC,
    call=op_remove_faces,
)

spec_heal = OperatorSpec(
    op="heal",
    category="cfd",
    produces="solid",
    params={},
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=HEAL_DOC,
    call=op_heal,
)

spec_cavity_extraction = OperatorSpec(
    op="cavity_extraction",
    category="cfd",
    produces="solid",
    params={},
    needs_target=False,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid(), volume_gt(0.0)),
    doc=CAVITY_EXTRACTION_DOC,
    call=op_cavity_extraction,
)

spec_tag_boundary = OperatorSpec(
    op="tag_boundary",
    category="annotation",
    produces="solid",
    params={
        "semantic_type": ParamSpec(
            ParamKind.ENUM,
            default="inlet",
            choices=("inlet", "outlet", "wall", "symmetry", "interface", "internal"),
        ),
        "name": ParamSpec(ParamKind.ENUM, default="boundary_1", choices=None),
    },
    needs_target=True,
    needs_tool=False,
    default_assertions=(is_valid(), is_solid()),
    doc=TAG_BOUNDARY_DOC,
    call=op_tag_boundary,
)

default_registry().register(spec_remove_fillets)
default_registry().register(spec_remove_faces)
default_registry().register(spec_heal)
default_registry().register(spec_cavity_extraction)
default_registry().register(spec_tag_boundary)
