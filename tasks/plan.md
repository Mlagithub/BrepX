# Implementation Plan: BrepX 深度架构重构 (B-Rep 拓扑管线、Blender 模态交互与统一 Agent 会话)

## Overview
本执行计划基于 [`docs/spec/REFACTORING_ARCHITECTURE_PLAN.md`](../docs/spec/REFACTORING_ARCHITECTURE_PLAN.md) 与 [`docs/CODE_STANDARDS.md`](../docs/CODE_STANDARDS.md) 制定，旨在将现有原型彻底重构为工业级 **AI + CAD + CAE (CFD)** 几何工作台。核心工作包含：清理所有过期文件与早期 Demo 痕迹、建立 `backend/` 与 `static/js/` 标准工程结构、落地基于 `smlibpy` 原生 `face_meshes` 与 `tessellate_boundaries` 的真实 B-Rep 拓扑级图形管线、实现真正的选区敏感几何算子与 Blender 式鼠标模态操作符（`E` 选面交互拉伸、`Ctrl+B` 选边交互倒角、3D 视口直接点击绘制 2D 草图、左下角 `Adjust Last Operation` 实时微调浮窗），以及打通人机共享 `WorkspaceSession` 的具身 Agent 协同架构。

---

## Architecture Decisions
1. **真实 B-Rep 拓扑图形容器代替合并 glTF 三角网格**：
   - *决策*：废除前端通过 `GLTFLoader` 加载无拓扑结构的合并网格的做法；后端 `backend/brep_graphic.py` 直接调用 `smlibpy` 原生 `face_meshes(shape)` 与 `k.tessellate_boundaries(shape._brep)`，按每个 `part.faces()[j]`、`part.edges()[n]`（过滤接缝边 seam）和 `part.vertices()[v]` 输出独立拓扑缓冲、几何解析属性（平面法向/中心/面积、圆柱半径/轴线、边长/圆心）及对应的 Python 表达式。
   - *理由*：唯有携带真实的 B-Rep `face_index` 与 `edge_index`，前端才能实现整张 CAD 曲面或整条特征边的精确悬停/多选高亮，并让倒角、抽壳、打孔、去特征化和 CFD 边界打标 100% 作用在用户真实选中的拓扑元素上。
2. **单一事实源的工作区会话 (`WorkspaceSession`) 与快照回滚**：
   - *决策*：后端 `backend/workspace.py` 维护持久化的 Python 命名空间 (`ns`) 与步骤历史列表 (`history`)；无论是前端模态算子、参数微调 (`Adjust Last Operation`)、脚本编辑还是 Agent 对话，均通过 `workspace.execute_step(code, label)` 统一执行，并经过 AST 白名单安全校验。
   - *理由*：彻底消除“鼠标操作”与“Agent 编程”的割裂感，天然支持多实体共存、Undo/Redo 以及左下角面板修改上一步参数时的无损回滚重算。
3. **Blender 式 `invoke -> modal -> execute / cancel` 前端模态状态机**：
   - *决策*：前端 `static/js/modal_ops.js` 与 `sketcher.js` 实现非阻塞的鼠标模态事件循环；在 `modal()` 鼠标移动期间仅在 WebGL 显存中更新动态预览网格/辅助标尺（0 网络请求，稳定 60 FPS），仅在左键点击或按 `Enter` 确认时触发一次后端 `execute()`。
   - *理由*：兼具 Blender 丝滑跟手的鼠标直接操作体验与 SMLib C++ 内核的严格 B-Rep 数学精度。

---

## Dependency Graph

```text
Phase 1: 仓库清理与统一工作区/B-Rep 拓扑底座
  ├── Task 1: 清理根目录过期文件并初始化 backend/ 与 tests/ 目录结构
  └── Task 2: 实现 backend/workspace.py 与 backend/brep_graphic.py (AST 沙盒 + 真实 B-Rep 拓扑容器序列化)
        │
        ▼
Phase 2: 选区敏感真实几何算子与统一 API 网关
  ├── Task 3: 实现 backend/operators.py (基于真实 face/edge 索引的拉伸/倒角/抽壳/草图/CFD 去特征与流道提取)
  └── Task 4: 实现 backend/semantic_patches.py, backend/agent_engine.py 与 backend/router.py
        │
        ▼
Phase 3: 前端 B-Rep 拓扑视口与真实点/线/面/体多选拾取
  ├── Task 5: 重构 static/index.html 与 static/style.css (清除旧痕迹，构建 Blender 风格布局与 F9 微调浮窗)
  └── Task 6: 实现 static/js/context.js, viewport.js 与 selection.js (真实 CAD 曲面/特征边渲染、悬停预高亮与 Shift 多选)
        │
        ▼
Phase 4: Blender 级鼠标模态交互、3D 视口直接草图绘制与具身 Agent 联调
  ├── Task 7: 实现 static/js/modal_ops.js (选面按 E 鼠标拉拽拉伸/挖槽、选边按 Ctrl+B 鼠标拉拽倒角、F9 实时重算)
  ├── Task 8: 实现 static/js/sketcher.js (在 3D 视口工作平面/选定面上直接用鼠标取点绘制 Line/Rect/Circle/Arc/Polyline/Spline)
  └── Task 9: 实现 static/js/boundary.js, agent_panel.js 与 static/app.js 并完成全链路 E2E 验收
```

---

## Task List

### Phase 1: 仓库清理与统一工作区 / B-Rep 拓扑底座
- [ ] **Task 1**: 清理根目录过期文件、彻底移除旧 Demo 痕迹并建立标准包结构 (`backend/`, `tests/`)
- [ ] **Task 2**: 实现统一工作区引擎 (`backend/workspace.py`) 与真实 B-Rep 拓扑图形序列化器 (`backend/brep_graphic.py`)

### Checkpoint 1: 核心底座验证
- [ ] 根目录整洁度检查通过，全库搜索旧参考项目关键词结果为 0
- [ ] `python -m unittest tests/test_workspace_and_brep.py` 单元测试全部通过，验证 `Part` 能正确拆解为带真实 `face_index`/`edge_index`/`vertex_index` 与解析几何属性的图形容器

### Phase 2: 选区敏感真实几何算子与统一 API 网关
- [ ] **Task 3**: 实现选区敏感的真实 SMLib 几何算子库 (`backend/operators.py`)，覆盖图元、真实 2D 草图曲线、选面拉伸/打孔/抽壳/拔模、选边圆角/倒角、放样/扫掠/旋转及 CFD 去特征化 (`remove_fillets`/`remove_faces`/`cavity_extraction`)
- [ ] **Task 4**: 实现 CFD 拓扑表面语义管理 (`backend/semantic_patches.py`)、具身 Agent 引擎 (`backend/agent_engine.py`) 与 FastAPI 路由网关 (`backend/router.py`, `server.py`)

### Checkpoint 2: 后端全算子与 API 契约验证
- [ ] 针对全部几何算子、Undo/Redo、Adjust Last Operation 重算、CFD 边界标注及 Agent 选区感知的后端集成测试全部通过

### Phase 3: 前端 B-Rep 拓扑视口与真实点/线/面/体多选拾取
- [ ] **Task 5**: 重构前端主界面 (`static/index.html`) 与样式表 (`static/style.css`)，打造 Blender 5.1.2 风格沉浸式布局（左侧 T-Panel 工具箱 + 场景树、中央全屏视口 + 左下角 F9 微调面板、右侧属性/CFD 边界与 Agent 协同栏）
- [ ] **Task 6**: 实现前端状态总线 (`static/js/context.js`)、B-Rep 容器渲染管线 (`static/js/viewport.js`) 与真实拓扑级拾取器 (`static/js/selection.js`)，支持整张 CAD 曲面/整条特征边悬停预高亮与 `Shift` 多选

### Checkpoint 3: 视口渲染与真实 B-Rep 拾取验证
- [ ] 浏览器中加载模型后，鼠标点击顶面或圆柱面可整面高亮（非单个三角形），点击圆孔边可整圈高亮，状态栏准确展示后端返回的真实面积、法向、半径与 `part.faces()[j]` 表达式

### Phase 4: Blender 级鼠标模态交互、3D 视口草图绘制与具身 Agent 闭环
- [ ] **Task 7**: 实现 Blender 式模态操作符 (`static/js/modal_ops.js`)：选面按 `E` 鼠标沿法向实时拉拽拉伸/开槽、选边按 `Ctrl+B` 鼠标拉拽倒圆角/倒角、`G/R/S/X/Y/Z` 变换手柄、`X` 键特征消除 (`remove_faces`/`remove_fillets`) 及左下角 `Adjust Last Operation` 实时重算
- [ ] **Task 8**: 实现 3D 视口工作平面交互式草图绘制器 (`static/js/sketcher.js`)：支持在基准面或任意选中平面上直接用鼠标点击取点绘制 `Line`, `Rectangle`, `Circle`, `ThreePointArc`, `Polyline`, `Spline` 并实时预览
- [ ] **Task 9**: 实现 CFD 物理边界着色模块 (`static/js/boundary.js`)、具身 Agent 协同面板 (`static/js/agent_panel.js`) 与主入口装配 (`static/app.js`)，完成全套自动化与无头浏览器 E2E 验收

### Checkpoint 4: 全系统最终验收
- [ ] 所有单文件行数符合 `< 350` 行（前端）/ `< 400` 行（后端）的代码规范
- [ ] `python tests/test_workspace_and_brep.py` 与 `python tests/test_api_e2e.py` 100% 通过
- [ ] 真实无头浏览器验证 B-Rep 整面/整边拾取、`E` 交互拉伸、`Ctrl+B` 交互倒角、视口鼠标画草图、CFD 边界着色与 Agent 选区协同全部正常工作

---

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| 复杂曲面（或布尔切削后）个别面单独三角化失败 | High | 在 `backend/brep_graphic.py` 中优先使用 `smlibpy.mesh.face_meshes(shape, tol, 12.0)` 整体剖分后按面切分，单面异常时降级容错，绝不阻断其余面渲染 |
| 模态操作 (`E` 拉伸 / `Ctrl+B` 倒角) 鼠标屏幕位移向 3D 法向投影不准 | Med | 在 `modal_ops.js` 中将 3D 面中心与法向矢量投影到屏幕 2D 向量，计算鼠标位移在该 2D 投影向量上的点积 (Dot Product)，并支持键盘直接键入精确毫米数值 |
| `Adjust Last Operation` 修改参数时若直接叠加会导致重复建模 | High | `WorkspaceSession` 在每次执行算子前自动记录前置状态快照；触发 `adjust_last_operation` 时先无损回滚至前置快照，再用新参数执行算子 |
| 在选中斜面上绘制 2D 草图时的坐标系转换复杂 | Med | 前端使用选中平面的 `center` 与 `normal` 构建局部正交工作平面进行 Raycast 求交，将局部 $(u, v)$ 坐标传给后端，后端通过 `sketch.on(part.faces()[j])` 原生贴合到目标面 |

## Open Questions
- 所有架构约束、交互键位、CFD 边界着色规则与模块划分均已在 `docs/spec/REFACTORING_ARCHITECTURE_PLAN.md` 与 `docs/CODE_STANDARDS.md` 中对齐完毕，无阻塞性未决问题。
