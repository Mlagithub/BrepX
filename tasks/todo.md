# Implementation Task List: SMLib Studio Next 深度架构重构

> 本任务清单严格遵循 [`docs/spec/REFACTORING_ARCHITECTURE_PLAN.md`](../docs/spec/REFACTORING_ARCHITECTURE_PLAN.md) 与 [`docs/CODE_STANDARDS.md`](../docs/CODE_STANDARDS.md) 拆解，采用自底向上、垂直切片验证的方式执行。

---

## Phase 1: 仓库清理与统一工作区 / B-Rep 拓扑底座

### Task 1: 清理根目录过期文件、彻底移除旧 Demo 痕迹并建立标准包结构
**Description:** 删除根目录下所有早期抓包脚本、散落测试文件、临时截图 PNG、逆向参考目录 `cax_reverse/` 与 `test_outputs/`；创建规范的 `backend/` 与 `tests/` 目录结构；清理 `README.md` 与文档中的旧 Demo 字眼。

**Acceptance criteria:**
- [ ] `cax_reverse/`、`test_outputs/`、`fetch_*.py`、`inspect_cax.py`、根目录散落 `test_*.py`（保留并迁移至 `tests/`）及根目录所有 `*.png` 全部删除
- [ ] 创建 `backend/__init__.py` 与 `tests/__init__.py`
- [ ] 全仓库检索旧参考项目名称（排除 git 历史）结果为 0

**Verification:**
- [ ] Tests pass: `python -c "import os; assert not os.path.exists('cax_reverse')"`
- [ ] Manual check: 检查根目录文件列表，仅保留 `server.py`, `requirements.txt`, `start.bat`, `README.md`, `.gitignore` 及规范子目录

**Dependencies:** None

**Files likely touched:**
- `backend/__init__.py`
- `tests/__init__.py`
- `README.md`
- `.gitignore`

**Estimated scope:** Small (目录清理与初始化)

---

### Task 2: 实现统一工作区引擎 (`backend/workspace.py`) 与真实 B-Rep 拓扑图形序列化器 (`backend/brep_graphic.py`)
**Description:** 构建持久化 Python 命名空间会话 `WorkspaceSession`（含 AST 白名单安全沙盒、多实体变量追踪、步骤历史栈、`undo()`/`redo()` 及 `replay_for_adjust()`），并基于 `smlibpy` 原生 `face_meshes` 与 `tessellate_boundaries` 实现 `brep_graphic.py`，将任意 `Part`/`Shell`/`Sketch` 精确拆解为带真实 `face_index`、`edge_index`、`vertex_index`、解析几何属性（法向、面积、半径、边长）和 Python 拓扑表达式的结构化图形容器。

**Acceptance criteria:**
- [ ] `WorkspaceSession` 支持执行 `smlibpy` 脚本，并通过 AST 拦截 `os`/`sys`/`subprocess`/`open` 等危险调用
- [ ] `WorkspaceSession` 支持 `undo()`、`redo()` 以及针对最后一步操作的无损参数替换重算 (`adjust_last_step`)
- [ ] `brep_graphic.serialize_scene()` 能将 `Box(60, 40, 20)` 准确序列化为 6 个独立拓扑 `faces`、12 条拓扑 `edges` 和 8 个 `vertices`，每个元素均带有准确的测量数据与 `expr`（如 `"part.faces()[0]"`）

**Verification:**
- [ ] Tests pass: `python -m unittest tests/test_workspace_and_brep.py`
- [ ] Manual check: 验证带圆角与通孔的复杂零件序列化后，平面与圆柱面的 `geom_type`、`normal`、`radius` 完全准确

**Dependencies:** Task 1

**Files likely touched:**
- `backend/workspace.py`
- `backend/brep_graphic.py`
- `tests/test_workspace_and_brep.py`

**Estimated scope:** Medium (3 files)

---

## Checkpoint 1: 核心底座验证
- [ ] 根目录无任何过期文件与旧 Demo 字眼
- [ ] `python -m unittest tests/test_workspace_and_brep.py` 100% 通过
- [ ] B-Rep 拓扑面/边/点序列化耗时在常规零件上 < 50 ms

---

## Phase 2: 选区敏感真实几何算子与统一 API 网关

### Task 3: 实现选区敏感的真实 SMLib 几何算子库 (`backend/operators.py`)
**Description:** 彻底废除旧版硬编码假逻辑，基于 `WorkspaceSession` 与真实拓扑选区索引（`selected_faces`, `selected_edges`）实现全部几何算子：基础图元（`box`, `cylinder`, `sphere`, `cone`, `torus`, `wedge`）、真实 2D 草图曲线（`line`, `rectangle`, `circle`, `arc`, `polyline`, `spline` 支持在选定平面 `.on(face)` 上生成）、选面拉伸/切槽 (`extrude`)、选面打孔 (`hole`/`counterbore`/`countersink`)、选边圆角/倒角 (`fillet`/`chamfer` 精确作用于选定 `edge_indices`)、选开口面抽壳 (`shell` 精确传入 `openings`)、拔模 (`draft`)、旋转 (`revolve`)、扫掠 (`sweep`)、放样 (`loft`)、布尔 (`union`/`difference`/`intersection`)、切分/截面 (`split`/`section`)、镜像/阵列 (`mirror`/`grid_array`/`polar_array`)、空间变换 (`translate`/`rotate`/`scale`) 以及 CFD 专用前处理算子（`remove_fillets` 擦除选定或全部圆角、`remove_faces` 填平选定孔洞/特征、`cavity_extraction` 内流道提取、`heal` 拓扑修复）。

**Acceptance criteria:**
- [ ] 每个算子均生成干净、可读、标准化的 `smlibpy` Python 代码并交由 `WorkspaceSession` 执行
- [ ] `fillet` / `chamfer` 严格作用于传入的 `edge_indices`（如仅对选中的第 2、5 条边倒圆角）
- [ ] `shell` 严格将传入的 `face_indices` 作为开口面 `openings` 掏空实体
- [ ] `remove_faces` 能将选中的孔内壁面直接移除并自动闭合愈合实体
- [ ] 2D 草图工具真实调用 `Line`, `Rectangle`, `Circle`, `ThreePointArc`, `Polyline`, `Spline`

**Verification:**
- [ ] Tests pass: `python -m unittest tests/test_workspace_and_brep.py`（扩充算子测试用例）
- [ ] Manual check: 验证每个算子执行后 `part.is_valid()` 为 True 且体积变化符合几何预期

**Dependencies:** Task 2

**Files likely touched:**
- `backend/operators.py`
- `tests/test_workspace_and_brep.py`

**Estimated scope:** Medium (2 files)

---

### Task 4: 实现 CFD 表面语义管理 (`backend/semantic_patches.py`)、具身 Agent 引擎 (`backend/agent_engine.py`) 与路由网关 (`backend/router.py`, `server.py`)
**Description:** 实现绑定真实 B-Rep `face_index` 与法向/中心点特征的 CFD 边界语义管理器（支持导出带命名信息的 STEP AP242 与 OpenFOAM/Fluent 边界字典 JSON）；实现与 `WorkspaceSession` 深度集成的 `AgentEngine`（自动感知场景变量列表、用户当前选中的面/边拓扑详情及测量值，集成 `smlibpy.mcp.discovery` 原生 API 检索，支持几何报错自愈重试与反向视口高亮 `highlight_expressions`）；编写 `backend/router.py` 与极简入口 `server.py`，删除根目录旧后端文件（`tools_handler.py`, `agent.py`, `semantic_manager.py`, `session_manager.py`）。

**Acceptance criteria:**
- [ ] Agent 提示词上下文自动注入当前工作区变量摘要、当前选中面/边的 `expr` 与几何测量属性、以及 `smlibpy.mcp.discovery` 检索到的 API 签名
- [ ] 提供完整的 REST API：`/api/workspace/state`、`/api/workspace/execute_operator`、`/api/workspace/adjust_last`、`/api/workspace/run_script`、`/api/workspace/undo`、`/api/workspace/redo`、`/api/workspace/inspect_selection`、`/api/agent/chat`、`/api/semantic/*`、`/api/export/*`
- [ ] 根目录旧平面后端模块全部移除并由 `backend/*` 接管

**Verification:**
- [ ] Tests pass: `python -m unittest tests/test_api_e2e.py`
- [ ] Build succeeds: `python -c "import server; print('Server loaded OK')"`

**Dependencies:** Task 3

**Files likely touched:**
- `backend/semantic_patches.py`
- `backend/agent_engine.py`
- `backend/router.py`
- `server.py`
- `tests/test_api_e2e.py`

**Estimated scope:** Medium (5 files)

---

## Checkpoint 2: 后端全算子与 API 契约验证
- [ ] `python -m unittest discover -s tests` 全部绿灯通过
- [ ] 验证通过 API 执行算子 ➔ 调用 `adjust_last` 修改参数 ➔ 调用 `undo` / `redo` 状态流转完全正确
- [ ] 验证 Agent 在传入 `selected_exprs=["part.faces()[2]"]` 时能直接针对该面生成打孔或拉伸代码

---

## Phase 3: 前端 B-Rep 拓扑视口与真实点/线/面/体多选拾取

### Task 5: 重构前端主界面 (`static/index.html`) 与样式表 (`static/style.css`)
**Description:** 彻底移除旧版界面布局与残余字眼，打造对标 Blender 5.1.2 的现代化暗黑工业风界面：顶部模式与视图/CFD 边界/导出栏；左侧可折叠交互式工具箱 (T-Panel，按“草图绘制”、“特征构造”、“直接建模与 CFD”、“变换与阵列”分组)；中央全屏 3D 视口（含顶部模态操作引导栏、鼠标光标处 `Shift+A` 添加菜单、左下角可折叠 `Adjust Last Operation` 实时参数微调面板、选定面浮动快捷动作条）；右侧 Outliner 场景对象树、拓扑属性/CFD 边界列表与具身 Agent 协同面板 (N-Panel)。

**Acceptance criteria:**
- [ ] 界面无任何旧参考项目名称，视觉风格统一为 Blender 5.1.2 暗黑工业风
- [ ] 包含左下角 `#adjust-last-panel`（复刻 Blender F9 微调窗）、顶部模态状态提示条 `#modal-status-bar` 及 3D 视口草图绘制 HUD
- [ ] 右侧 Agent 面板包含“当前视口选区上下文标签栏”（实时展示用户选中的面/边 pills，可一键带入对话）

**Verification:**
- [ ] Manual check: 启动服务检查 HTML DOM 结构完整性与 CSS 响应式布局

**Dependencies:** Task 4

**Files likely touched:**
- `static/index.html`
- `static/style.css`

**Estimated scope:** Small (2 files)

---

### Task 6: 实现前端状态总线 (`static/js/context.js`)、B-Rep 容器渲染管线 (`static/js/viewport.js`) 与真实拓扑级拾取器 (`static/js/selection.js`)
**Description:** 实现单向数据流的全局 `CADContext` 状态总线；重构 `viewport.js` 以渲染后端返回的 B-Rep 拓扑容器（将每个真实 CAD `Face` 构建为带精确 `faceIndex` 与解析属性的 Mesh，将每条真实 CAD `Edge` 构建为高对比度折线，将每个 `Vertex` 构建为可捕捉节点，并在每次更新时严格 `.dispose()` 释放旧显存）；重构 `selection.js` 实现真实 B-Rep 级悬停预高亮（Hover Pre-highlight）、左键单选、`Shift + 左键` 多选（支持同时选中多条边或多个面）以及 Agent 反向高亮 (`set_selection`)。

**Acceptance criteria:**
- [ ] 鼠标在视口移动时，悬停的整张 CAD 拓扑面（如圆柱外表面或带孔顶面）或整条特征边呈现半透明预高亮
- [ ] 左键点击选中整张 CAD 曲面或整条特征边；按住 `Shift` 点击可累加选中多个拓扑面或多条边
- [ ] 选中状态实时同步至 `CADContext.selections`，右侧属性栏与 Agent 选区标签栏立即显示选中元素的表达式（如 `part.faces()[4]`）及精确面积/法向/半径/长度
- [ ] 每个 JS 模块严格控制在 350 行以内

**Verification:**
- [ ] Manual check: 在浏览器中加载带孔法兰盘，点击顶面验证整张顶面高亮（而非单个三角形），按住 Shift 点击 4 条竖边验证 4 条边同时高亮

**Dependencies:** Task 5

**Files likely touched:**
- `static/js/context.js`
- `static/js/viewport.js`
- `static/js/selection.js`

**Estimated scope:** Medium (3 files)

---

## Checkpoint 3: 视口渲染与真实 B-Rep 拾取验证
- [ ] 真实 B-Rep 整面、整边、顶点拾取与 `Shift` 多选在无头浏览器中验证通过
- [ ] 每次重建几何后 WebGL `renderer.info.memory` 几何体数量无泄漏增长

---

## Phase 4: Blender 级鼠标模态交互、3D 视口草图绘制与具身 Agent 闭环

### Task 7: 实现 Blender 式模态操作符状态机 (`static/js/modal_ops.js`) 与左下角 F9 实时微调
**Description:** 移除旧文件 `static/js/gizmo.js` 与 `static/js/tools.js`，统一构建符合 Blender `invoke -> modal -> execute / cancel` 协议的 `modal_ops.js`：
1. **选面交互拉伸 (`EXTRUDE_OT_face` - 快捷键 `E`)**：选中面（或草图）后按 `E`，鼠标移动沿该面法向实时绘制半透明 3D 拉伸体/切槽预览与动态标尺（支持直接键盘敲入数字如 `20` 或 `-8`、按 `B` 切换合并/切除/新建），左键或 `Enter` 确认提交，`Esc`/右键取消；
2. **选边交互倒圆角/倒角 (`FILLET_OT_edge` - 快捷键 `Ctrl + B`)**：选中一条或多条拓扑边后按 `Ctrl + B`，鼠标拖动实时计算半径并绘制动态圆角预览线与数值 HUD（按 `M` 切换圆角 Fillet / 倒角 Chamfer，支持键盘数字输入），左键确认即对所选边索引执行真实倒角；
3. **变换手柄与模态移动/旋转/缩放 (`G / R / S` + `X / Y / Z` 轴向锁定)**：拖拽期间 60 FPS 本地显存矩阵变换，松手确认提交；
4. **特征消除快捷键 (`X` / `Delete`)**：在编辑模式下选中孔洞面或圆角面按 `X`，弹出确认菜单直接执行 `remove_faces`（填平孔洞）或 `remove_fillets`（擦除圆角）；
5. **左下角 `Adjust Last Operation` 面板联动**：算子完成后自动展示参数微调控件，修改任意参数即刻调用 `/api/workspace/adjust_last` 无损回滚重算。

**Acceptance criteria:**
- [ ] 选中任意平面按 `E` 移动鼠标，视口出现 60 FPS 动态拉伸预览体与高度读数，点击左键后真实生成拉伸/切槽特征
- [ ] 选中一条或多条边按 `Ctrl + B` 移动鼠标，左键确认后仅对选中的边完成倒圆角或倒角
- [ ] 操作完成后修改左下角 `Adjust Last Operation` 面板中的数值，模型立即无损更新为新尺寸（不产生重复叠加特征）
- [ ] 选中孔内壁面按 `X` 选择“移除面并愈合 (`remove_faces`)”，孔洞被直接抹平

**Verification:**
- [ ] Manual check: 通过无头浏览器自动化脚本模拟选面按 `E` 鼠标移动与点击、选边按 `Ctrl+B` 鼠标移动与点击，验证模型体积与拓扑面数准确变化

**Dependencies:** Task 6

**Files likely touched:**
- `static/js/modal_ops.js`

**Estimated scope:** Medium (1 focused module + cleanup of superseded files)

---

### Task 8: 实现 3D 视口工作平面交互式草图绘制器 (`static/js/sketcher.js`)
**Description:** 实现直接在 3D 视口中用鼠标取点绘制真实 2D 草图的交互系统：当用户点击左侧工具栏的草图工具（直线 `Line`、矩形 `Rectangle`、圆 `Circle`、三点圆弧 `Arc`、折线 `Polyline`、样条 `Spline`）时，自动以当前选中的平面（如长方体顶面）或默认 XY 平面建立带网格吸附的工作平面；鼠标在视口移动时实时投射到该工作平面并绘制动态几何预览线与尺寸标注；点击完成取点后向后端提交精确坐标点列，生成真实的 `smlibpy` `Sketch` / `Wire` 对象，并支持紧接着按 `E` 直接交互拉伸成体。

**Acceptance criteria:**
- [ ] 支持在 XY 基准面或任意选中的实体平面（如 `part.faces()[j]`）上开启草图绘制模式
- [ ] 鼠标在 3D 视口中点击取点时，实时显示动态橡皮筋预览线（矩形框、圆环、圆弧、多段折线/样条曲线）与坐标/尺寸读数（支持网格点吸附 Snap）
- [ ] 绘制完成后在场景中生成真实的 `Sketch` 几何体，选中该草图按 `E` 即可直接交互拉伸为 3D 实体特征

**Verification:**
- [ ] Manual check: 在浏览器中选择长方体顶面 ➔ 点击“圆”草图工具 ➔ 在顶面点击圆心与半径点生成圆草图 ➔ 按 `E` 向下拉伸切出盲孔

**Dependencies:** Task 7

**Files likely touched:**
- `static/js/sketcher.js`

**Estimated scope:** Small (1 focused module)

---

### Task 9: 实现 CFD 物理边界模块 (`static/js/boundary.js`)、具身 Agent 面板 (`static/js/agent_panel.js`) 与主控制器 (`static/app.js`) 并完成全量验收
**Description:** 重构 `boundary.js` 使其直接基于真实 B-Rep `face_index` 整面渲染 CFD 物理边界色块（仅在开启“🌊 边界模式”时显示 Inlet 深蓝、Outlet 玫红、Wall 冷灰、Interface 暖橙，平时保持纯净 CAD 金属色）；实现 `agent_panel.js`（自动展示当前选中的 `part.faces()[j]` / `part.edges()[n]` 上下文胶囊，支持与 Agent 双向同步选区与操作历史）；编写精简的 `static/app.js`（< 250 行）装配全部子模块，并运行全套单元测试与真实无头浏览器端到端验收测试。

**Acceptance criteria:**
- [ ] 开启“🌊 边界模式”时，标记为 Inlet/Outlet 的整张 CAD 拓扑面（包含曲面或带孔平面）完整呈现对应物理颜色，关闭模式立即恢复默认材质
- [ ] 选中任意面或边后，Agent 面板顶部实时显示选区标签（如 `Face #2 (plane, 1200 mm²)`），对 Agent 输入“在这个面上打一个直径 12 的通孔”或“将选中边倒 R3 圆角”，Agent 准确完成建模并刷新视口
- [ ] 所有前端 JS 文件均 < 350 行，所有后端 Python 文件均 < 400 行
- [ ] 全套自动化测试与真实浏览器交互测试 100% 通过

**Verification:**
- [ ] Tests pass: `python -m unittest discover -s tests`
- [ ] Manual check: 运行无头浏览器全链路验收并采集高分辨率视口截图验证

**Dependencies:** Task 8

**Files likely touched:**
- `static/js/boundary.js`
- `static/js/agent_panel.js`
- `static/app.js`
- `tests/test_api_e2e.py`

**Estimated scope:** Medium (4 files)

---

## Checkpoint 4: 全系统最终验收 (Definition of Done)
- [ ] 根目录及全库无任何过期文件与 `cax-viewer` 字眼
- [ ] 所有模块符合 [`docs/CODE_STANDARDS.md`](../docs/CODE_STANDARDS.md) 行数与安全规范
- [ ] 后端单元测试与 API E2E 测试 100% 通过
- [ ] 真实浏览器验证 B-Rep 整面/整边拾取、`E` 交互拉伸、`Ctrl+B` 交互倒角、3D 视口鼠标绘制草图、`Adjust Last Operation` 实时重算、CFD 边界模式与具身 Agent 协同全部工作正常
