from enum import Enum
from typing import List, Dict, Any, Optional
import uuid

class BoundarySemanticType(str, Enum):
    INLET = "inlet"           # 速度入口 / 质量入口
    OUTLET = "outlet"         # 压力出口 / 自由流出
    WALL = "wall"             # 固体壁面
    SYMMETRY = "symmetry"     # 对称面
    INTERFACE = "interface"   # 流固耦合或多相流交界面
    INTERNAL = "internal"     # 内部流道特征面

SEMANTIC_COLORS = {
    BoundarySemanticType.INLET: "#3a86ff",      # 亮蓝
    BoundarySemanticType.OUTLET: "#ff006e",     # 玫红
    BoundarySemanticType.WALL: "#8338ec",       # 浅紫灰
    BoundarySemanticType.SYMMETRY: "#06d6a0",   # 青绿
    BoundarySemanticType.INTERFACE: "#fb5607",  # 暖橙
    BoundarySemanticType.INTERNAL: "#ffbe0b",   # 明黄
}

class SemanticManager:
    """管理几何模型表面的 CFD 物理边界语义属性"""

    def __init__(self):
        self.patches: Dict[str, Dict[str, Any]] = {}

    def clear(self):
        self.patches.clear()

    def set_patch(self, face_index: int, semantic_type: str, name: Optional[str] = None,
                  normal: Optional[List[float]] = None, area: Optional[float] = 0.0) -> Dict[str, Any]:
        """将指定面打上物理边界标签"""
        try:
            sem_enum = BoundarySemanticType(semantic_type.lower())
        except ValueError:
            sem_enum = BoundarySemanticType.WALL

        # 检查是否已存在该面的标记，存在则覆盖更新
        target_id = None
        for pid, p in self.patches.items():
            if face_index in p.get("face_indices", []):
                target_id = pid
                break

        if not target_id:
            target_id = f"patch_{uuid.uuid4().hex[:6]}"

        if not name:
            # 自动生成名称，如 inlet_1, outlet_2
            count = sum(1 for p in self.patches.values() if p["semantic_type"] == sem_enum.value) + 1
            name = f"{sem_enum.value}_{count}"

        patch_data = {
            "id": target_id,
            "name": name,
            "semantic_type": sem_enum.value,
            "face_indices": [face_index],
            "color_hex": SEMANTIC_COLORS.get(sem_enum, "#3a86ff"),
            "normal": normal or [0, 0, 1],
            "area": area or 0.0
        }

        self.patches[target_id] = patch_data
        return patch_data

    def remove_patch(self, patch_id: str) -> bool:
        if patch_id in self.patches:
            del self.patches[patch_id]
            return True
        return False

    def get_all_patches(self) -> List[Dict[str, Any]]:
        return list(self.patches.values())

    def export_cfd_metadata(self) -> Dict[str, Any]:
        """生成标准 CFD 边界条件清单，可供 OpenFOAM/Fluent 网格与求解器直接映射"""
        boundaries = {}
        for p in self.patches.values():
            boundaries[p["name"]] = {
                "type": p["semantic_type"],
                "faces": p["face_indices"],
                "area_mm2": p["area"],
                "estimated_normal": p["normal"]
            }

        return {
            "standard": "OpenFOAM/CFD-Boundary-Dict",
            "unit": "mm",
            "patches_count": len(self.patches),
            "boundaries": boundaries
        }

semantic_manager = SemanticManager()
