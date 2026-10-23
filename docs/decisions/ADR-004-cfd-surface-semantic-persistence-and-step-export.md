# ADR-004: 面向 CFD 的拓扑面级物理边界语义绑定与 STEP AP242 / 字典双轨导出

## Status
Accepted

## Date
2026-10-23

## Context
在 AI + CAD + CAE (CFD) 工业软件全栈工作流中，CAD 阶段的最终目的是为下游网格划分器（如 snappyHexMesh、Fluent Meshing、Gmsh）与求解器提供**带物理边界语义的水密几何模型**。
根据产品愿景声明（[`docs/intent/statement_of_intent.md`](../intent/statement_of_intent.md)）与用户确认的交互规范：
1. 物理边界语义（`inlet`, `outlet`, `wall`, `symmetry`, `interface`, `internal`）由用户或 Agent 直接在视口中对 **真实 B-Rep 拓扑面 (`Face`)** 完成打标；
2. 视口在常规建模状态下保持纯净的 CAD 金属材质，**仅在开启“🌊 物理边界模式 (Boundary Mode)”时**以高饱和物理色块高亮展示各边界（入口深蓝、出口玫红、壁面冷灰、对称面青绿、交界面暖橙）；
3. 导出 STEP 文件或交付下游求解器时，边界名称与几何特征必须完整保留，杜绝下游工程师重新肉眼找面。

## Decision
在 `backend/semantic_patches.py` 与 `static/js/boundary.js` 中采用 **几何特征指纹绑定 + STEP AP242 / CFD 边界字典双轨导出** 机制：

1. **基于真实 B-Rep `Face` 与几何特征指纹的边界绑定**：
   - 当用户（或 Agent）将 `part.faces()[j]` 标记为 `inlet_1` 时，系统不仅记录当前的 `face_index = j`，还同步记录该拓扑面的 **几何特征指纹 (`Geometric Fingerprint`)**：`geom_type`、面积 `area`、法向矢量 `normal` 与中心坐标 `center`；
   - 当后续建模操作（如给其他边倒圆角）导致 B-Rep 面序号发生变动时，`semantic_patches.rebind_patches(part)` 自动通过法向与中心点距离匹配，将边界语义重新锚定到对应的真实拓扑面上。
2. **仅在“物理边界模式”下激活整面着色 (`static/js/boundary.js`)**：
   - 由于 ADR-001 已经将每个 `part.faces()[j]` 构建为独立的子 Mesh，当用户开启“🌊 边界模式”时，`boundary.js` 直接将对应 `faceIndex` 的整张拓扑面（无论包含多少个三角形）切换为对应物理边界的专用颜色材质；关闭“边界模式”时立即恢复标准 CAD 金属天蓝材质。
3. **STEP AP242 拓扑命名与 CFD 边界元数据双轨交付**：
   - **STEP AP242 导出**：在导出 STEP 时，将已标注的边界信息与实体关联命名写出（或将各命名边界壳体/面组写入 STEP 产品结构树），满足通用 CAD/CAE 软件直接识别；
   - **CFD 边界字典导出 (`cfd_boundaries.json`)**：同步提供包含每个 Patch 的名称、物理类型 (`inlet`/`outlet`/`wall` 等)、精确面积 ($\text{mm}^2$)、外法向矢量、中心点坐标及包围盒的结构化 JSON 描述文件，供自动化网格脚本与求解器零成本读取。

## Alternatives Considered

### 方案 A：始终在视口中把标记过边界的面染成红红绿绿的彩色
- **Pros**：无需模式切换开关。
- **Cons**：在进行常规机械特征建模（如观察圆角曲率、边缘过渡）时，花哨的红蓝斑块会严重干扰工程师对几何形体的视觉判断。
- **Rejected**：用户明确指定“仅在物理边界编辑模式下高亮显示，平时不用”。

### 方案 B：仅绑定死板的三角形序号 (`triangle_index`)
- **Pros**：前端无需关心 B-Rep 面结构。
- **Cons**：一个圆柱面或带孔平面包含数百个三角形，点击一次只能染色一个三角形，且一旦模型发生任何微调，三角形序号全部洗牌丢失。
- **Rejected**：无法满足工程级整面打标与属性保持要求。

## Consequences
- **正面影响**：
  - 点击一次即可对整张 CAD 拓扑面完成 `Inlet` / `Outlet` / `Wall` 打标；
  - 平时视口清爽专业，开启“边界模式”时整张拓扑面色彩分明；
  - 即使后续追加了局部倒角特征，几何特征指纹自动重绑定也能保护已标注的进出口边界不丢失。
