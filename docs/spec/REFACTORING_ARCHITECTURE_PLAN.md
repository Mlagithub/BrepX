# SMLib Studio Next 彻底重构方案：去除 Demo 痕迹、落地真实 B-Rep 拓扑管线、Blender 模态交互与统一 Agent 会话

> 本文档定义了从早期原型向工业级 **AI + CAD + CAE (CFD)** 几何建模工作台演进的完整架构重构方案，彻底解决历史遗留的脏文件、Demo 痕迹、假三角面片拾取、工具硬编码以及 Agent 上下文割裂五大核心痛点。

---

## 一、 核心问题诊断与重构目标 (Root-Cause & Objectives)

1. **彻底清理根目录脏文件与过期资产**：
   - 删除所有早期临时抓包脚本（`fetch_*.py`, `inspect_cax.py`）、分散测试脚本（`test_smlibpy.py`, `test_features.py`, `test_templates.py`, `test_browser_actions.py`）、临时截图（`*.png`）以及整个逆向参考目录与 `test_outputs/`。
   - 建立严格的工程目录结构：后端收敛至 `backend/` 包，前端收敛至 `static/`，测试收敛至 `tests/`，规范与架构文档收敛至 `docs/`。
2. **彻底清除早期 Demo 痕迹，确立独立产品形态**：
   - 从所有代码、HTML 标题、UI 徽章、注释与文档中彻底移除旧参考项目的字眼；
   - 摒弃“右侧死板堆砌 32 个残缺表单按钮”的旧布局，重构为对标 Blender 5.1.2 的现代化 CAD 界面：**左侧交互式工具箱 (T-Panel) + Outliner 场景特征树**、**中央全屏 3D 视口 (Modal HUD + Shift+A 菜单 + 左下角 Adjust Last Operation 微调浮窗)**、**右侧属性/物理边界与 Agent 协同面板 (N-Panel)**。
3. **升级为真实 B-Rep 拓扑图形管线（解决“假拾取”与“工具未真实实现”）**：
   - **现状痛点**：此前前端使用 `GLTFLoader` 加载整体合并的三角网格，拾取 `hit.faceIndex` 只是拾取了**单个三角面片 (Triangle)**，而非真正的 **CAD 拓扑面 (`Face`)** 或 **拓扑边 (`Edge`)**；且草图工具（直线/圆弧/折线/样条）全是用矩形/圆假冒的，倒角/抽壳也写死在 `edges().parallel_to(Z)`。
   - **根治方案**：基于 `smlibpy` 原生 `face_meshes` 与 `tessellate_boundaries` 构建 B-Rep 图形容器协议！后端将每个实体的每一个真实拓扑面 `part.faces()[j]` 独立三角化并携带精确的 `faceIndex = j` 及曲面解析参数（平面法向、圆柱轴线/半径、球半径），每一条真实拓扑边 `part.edges()[n]` 独立离散为高精折线并携带 `edgeIndex = n` 与真实长度，每一个拓扑顶点 `part.vertices()[v]` 独立映射。
   - **结果**：鼠标在视口中悬停/点击时，高亮的是**完整的 CAD 拓扑曲面（例如整个圆柱侧面、整个法兰顶面）**和**完整的 CAD 特征边（例如整条圆弧边）**，并生成真实的语义表达式（如 `part.faces()[3]`, `part.edges()[5]`）。
4. **实现真正的 Blender 级交互式模态操作 (Modal Operators) 与 100% 真实几何工具**：
   - **选面交互拉伸 (`E` 键 / Extrude Tool)**：选中任意拓扑面后按 `E`，鼠标沿该面法向移动即可实时预览拉伸高度（60 FPS 动态网格/线框预览），左键点击或输入精确数字确认，直接对该面执行 `extrude` 或布尔加减（正值凸起、负值挖槽）；
   - **选边交互倒圆角/倒角 (`Ctrl + B` / Fillet & Chamfer Tool)**：选中一条或多条真实拓扑边（支持 Shift 多选）后按 `Ctrl + B`，左右移动鼠标实时预览圆角/倒角半径，左键确认后对**用户实际选中的边索引**执行 `part.fillet([part.edges()[i] for i in selected], r)`；
   - **选面交互抽壳 (`Shell Tool`)**：选中一个或多个开口拓扑面后执行抽壳，真正将用户选中的面作为 `openings` 传入 `part.shell(thickness, openings=[...])`；
   - **视口交互式 2D 草图绘制 (Interactive Sketching)**：在基准面或选定平面上，用鼠标在 3D 视口工作平面直接点击取点绘制真实的 `Line`、`Rectangle`、`Circle`、`CenterArc`/`ThreePointArc`、`Polyline`、`Spline`，闭合后直接生成 `Sketch`/`Profile` 并可一键拉伸/旋转/扫掠；
   - **左下角 `Adjust Last Operation` 浮窗（复刻 Blender F9 面板）**：任何工具执行完毕后，视口左下角自动浮现参数微调面板，修改任意数值即刻回滚上一步并实时重算。
5. **消除 Agent 割裂感：基于统一工作区 (`WorkspaceSession`) 与 `smlibpy` 原生内省协议**：
   - **现状痛点**：此前 `agent.py` 用粗糙的正则表达式硬凑代码，且与前端选区、场景多物体变量脱节。
   - **根治方案**：构建统一的 `WorkspaceSession`（复用并增强 `smlibpy.mcp.worker` 与 `discovery` 引擎）：
     - **同一命名空间 (Shared Namespace)**：鼠标操作、算子执行与 Agent 脚本在同一个持久化 Python 命名空间 (`ns`) 中运行，支持多实体共存、Checkpoint 快照与 Undo/Redo 历史栈；
     - **双向具身感知 (`get_selection` / `set_selection` / `inspect`)**：人类在视口点选的面/边自动转化为精确的 Python 拓扑引用（如 `part.faces()[2]` 及其几何类型、面积、法向、中心点）注入 Agent 上下文；Agent 不仅能直接对该选区编程，还能主动调用 `set_selection` 在视口中高亮特定面/边供用户确认；
     - **原生 RAG API 检索**：接入 `smlibpy.mcp.discovery` 的 89 个函数/27 个类完整签名与内置 Skill 指南检索，配合 AST 安全校验与几何报错自动重试闭环。
6. **制定并落地严格的代码规范 (`docs/CODE_STANDARDS.md`)**：
   - 明确 Python 后端（PEP 8、100% 类型注解、Pydantic v2 严格契约、AST 安全沙盒、统一错误码）与前端 ES Modules（单文件 < 350 行、显存生命周期 `.dispose()` 守则、状态单向数据流、Modal Operator 接口契约）规范。

---

## 二、 清理清单与重构后的项目目录架构

### 1. 待删除的过期/无关文件清单
* **目录删除**：逆向临时目录、`test_outputs/`
* **根目录过期脚本删除**：`inspect_cax.py`, `fetch_cax_files.py`, `fetch_vendor.py`, `fetch_three_addons.py`, `fetch_utils.py`, `test_smlibpy.py`, `test_features.py`, `test_templates.py`, `test_browser_actions.py`, `test_e2e.py`（迁移并重写至 `tests/`）
* **根目录临时图片删除**：`actual_render.png`, `render_bracket.png`, `render_csg.png`, `agent_dialogue_render.png`, `right_tools_render.png`, `full_ui_render.png`, `selection_transform_render.png`, `boundary_mode_render.png`, `cfd_venturi_render.png`, `refactored_system_render.png`
* **旧平面后端文件归并删除**：根目录下的 `tools_handler.py`, `agent.py`, `semantic_manager.py`, `session_manager.py` 重构并迁入规范的 `backend/` 模块包中。

### 2. 重构后的干净工程结构
```text
C:\Users\keep_\work\smlib\
├── server.py                      # 极简应用启动入口 (挂载 FastAPI 与静态目录)
├── requirements.txt               # Python 依赖声明
├── start.bat                      # Windows 一键启动脚本
├── README.md                      # 产品架构、快捷键与使用指南
├── backend/                       # 核心后端包
│   ├── __init__.py
│   ├── workspace.py               # 统一工作区引擎 (持久化命名空间、Undo/Redo Checkpoint、多实体管理)
│   ├── brep_graphic.py            # B-Rep 拓扑图形序列化器 (按真实 Face/Edge/Vertex 拆分网格与折线及测量数据)
│   ├── operators.py               # 真实 SMLib 几何算子库 (基于真实选区索引的倒角/抽壳/拉伸/扫掠/放样/草图/CFD前处理)
│   ├── agent_engine.py            # 具身 CAD Agent 引擎 (共享 Workspace 上下文、smlibpy.discovery RAG、自愈执行)
│   ├── semantic_patches.py        # CFD 表面物理边界语义标注 (绑定真实 B-Rep Face 与 STEP AP242 命名导出)
│   └── router.py                  # FastAPI 统一 REST API 路由定义与 Pydantic 契约
├── static/                        # 前端工程资产
│   ├── index.html                 # Blender 风格沉浸式工作台界面
│   ├── style.css                  # Blender 暗黑工业风样式表
│   ├── app.js                     # 前端主控制器 (< 250 行，负责模块装配与全局状态总线)
│   ├── js/
│   │   ├── context.js             # 全局响应式 CADContext 总线 (Objects, Mode, ActiveSelection, History)
│   │   ├── viewport.js            # Three.js 渲染管线、B-Rep 容器组装 (真实拓扑面 Mesh + 拓扑边 Line2)
│   │   ├── modal_ops.js           # Blender 式模态操作符状态机 (交互式鼠标拉伸 E、交互式倒角 Ctrl+B、G/R/S 手柄、Shift+A)
│   │   ├── sketcher.js            # 3D 视口工作平面交互式草图绘制器 (鼠标点击绘制 Line/Arc/Circle/Rect/Spline)
│   │   ├── selection.js           # 真实 B-Rep 拓扑级 Raycaster (整面高亮、整条弧/边高亮、Shift 多选、测量 HUD)
│   │   ├── boundary.js            # CFD 物理边界模式着色与表面语义管理
│   │   └── agent_panel.js         # 具身 Agent 协同面板 (自动感知当前选区标签、双向高亮、操作历史同步)
│   ├── utils/                     # Three.js 几何辅助库
│   └── vendor/                    # Three.js r186 核心与 Addons (OrbitControls, TransformControls, Line2)
├── docs/                          # 架构与规范文档库
│   ├── CODE_STANDARDS.md          # 前后端代码规范与架构契约
│   ├── blender_architecture_dna.md
│   ├── intent/
│   │   └── statement_of_intent.md
│   ├── ideas/
│   │   └── cfd_cad_workbench_concept.md
│   └── spec/
│       ├── SPEC-cfd-cad-workbench.md
│       └── REFACTORING_ARCHITECTURE_PLAN.md
└── tests/                         # 自动化回归测试套件
    ├── test_workspace_and_brep.py # 工作区、B-Rep 拓扑序列化与全部算子单元测试
    └── test_api_e2e.py            # 全链路 API、Agent 协同与 CFD 导出集成测试
```

---

## 三、 核心子系统详细设计 (Subsystem Specifications)

### 1. 真实 B-Rep 拓扑图形管线 (`backend/brep_graphic.py` & `static/js/viewport.js`)
* **后端序列化协议 (`/api/workspace/scene`)**：
  - 对工作区中的每个可见实体 (`Part` / `Shell` / `Sketch`)，调用 `smlibpy` 底层 `face_meshes` 与 `tessellate_boundaries`；
  - 输出结构化 JSON 容器：
    - `faces`: 数组，每项对应 `part.faces()[j]`，包含独立顶点/索引缓冲、`face_index: j`、`expr: "part.faces()[j]"`、`geom_type` (`plane`/`cylinder`/`sphere`/`cone`/`torus`/`nurbs`)、`area`、`center`、`normal`、`radius`；
    - `edges`: 数组，每项对应 `part.edges()[n]`（自动过滤接缝边 seam），包含高精度采样折线点列、`edge_index: n`、`expr: "part.edges()[n]"`、`geom_type` (`line`/`circle`/`ellipse`/`bspline`)、`length`、`center`、`radius`、`start`、`end`；
    - `vertices`: 数组，每项对应 `part.vertices()[v]`，包含 `vertex_index: v`、`expr: "part.vertices()[v]"`、`position: [x, y, z]`。
* **前端拓扑构建与拾取 (`static/js/selection.js`)**：
  - 每个拓扑面构建为一个带有 `userData = { bodyName, faceIndex, expr, surfaceInfo }` 的独立子 Mesh；
  - 每一条拓扑边构建为独立的宽线对象 `LineSegments2`（使用 `vendor/lines/LineSegments2.js`），带有 `userData = { bodyName, edgeIndex, expr, edgeInfo }`；
  - **悬停预高亮 (Hover Pre-highlight)** 与 **Shift 多选 (Multi-selection)**：鼠标划过时实时预高亮整张 CAD 曲面或整条特征边；左键点击选中，按住 `Shift` 点击可同时选中多条边或多个面（例如同时选 4 条边一起倒圆角，或同时选 2 个面一起抽壳开口）。

### 2. 对标 Blender 的交互式模态操作符 (`static/js/modal_ops.js` & `sketcher.js`)
所有操作遵循 `invoke(ctx, event) -> modal(ctx, event) -> execute(ctx) / cancel(ctx)` 协议：
1. **交互式面拉伸 (`EXTRUDE_OT_face` - 快捷键 `E`)**：
   - **触发条件**：在选中任意拓扑面（或二维草图）时按下 `E` 键（或点击工具栏“拉伸”）；
   - **Modal 阶段**：从该面中心引出一条黄色法向导引线，鼠标沿屏幕法向投影方向移动时，实时在视口中绘制半透明拉伸体预览框及动态距离标尺（支持直接键盘输入数字如 `25` 或 `-10` 切槽，按 `B` 切换新建/并集/差集切削）；
   - **Execute 阶段**：左键点击或按 Enter，向后端提交目标面索引与高度，后端在选中面上执行真实拉伸或切削：`part = part + part.faces()[j].extrude(h)`（正值凸起）或 `part = part - part.faces()[j].extrude(-h)`（负值开槽）。
2. **交互式边倒圆角 / 倒角 (`FILLET_OT_edge` / `CHAMFER_OT_edge` - 快捷键 `Ctrl + B`)**：
   - **触发条件**：在选中一条或多条真实拓扑边时按下 `Ctrl + B`（或点击工具栏“圆角”/“倒角”）；
   - **Modal 阶段**：鼠标远离选定边中心移动时，动态映射为半径 $r$（屏幕顶部与光标旁实时显示 `Fillet Radius: 4.5 mm`，支持键盘直接输入数值，按 `M` 切换圆角 Fillet / 倒角 Chamfer）；
   - **Execute 阶段**：左键点击确认，后端精确对用户选中的边索引列表 `[i1, i2, ...]` 执行 `part = part.fillet([part.edges()[i] for i in indices], r)`。
3. **交互式视口 2D 草图绘制器 (`SKETCH_OT_draw` - `static/js/sketcher.js`)**：
   - **触发条件**：点击工具栏的草图工具（直线 `Line`、矩形 `Rectangle`、圆 `Circle`、三点圆弧 `Arc`、多段折线 `Polyline`、样条曲线 `Spline`）；
   - **基准面自适应**：若当前已选中某个平面（如长方体顶面），自动以该面为草图工作平面 (`Plane`)；否则默认使用 XY 基准面；
   - **鼠标取点绘制**：
     - 矩形：视口点击第一角点 ➔ 移动鼠标实时预览矩形框与长宽尺寸 ➔ 点击对角点生成真实 `Rectangle` 草图；
     - 圆：点击圆心 ➔ 移动鼠标实时预览圆环与半径 ➔ 点击生成真实 `Circle` 草图；
     - 折线 / 样条 / 圆弧：视口连续点击添加控制点（实时绘制虚线预览），右键或按 Enter 结束并调用 SMLib `Polyline` / `Spline` / `ThreePointArc` 生成真实曲线/草图对象。
4. **左下角 `Adjust Last Operation` 实时重算面板**：
   - 任何算子执行后，视口左下角自动弹出半透明微调面板（显示刚刚执行的算子名称与参数滑块/输入框）；
   - 修改数值时，后端直接从上一 `Checkpoint` 恢复并用新参数重新执行该算子，实现与 Blender 左下角面板完全一致的无损调参体验。

### 3. 全功能真实几何算子 (`backend/operators.py`)
所有工具栏算子全部废除硬编码假逻辑，对接真实 `smlibpy` API：
* **基础图元**：`box`, `cylinder`, `sphere`, `cone`, `torus`, `wedge`（楔形体）；
* **选区敏感特征**：
  - `hole` / `counterbore` / `countersink`：若选中了平面，直接在该平面中心或拾取点位置垂直打贯穿孔/沉头孔/埋头孔（使用 `Hole`, `CounterBoreHole`, `CounterSinkHole` + `.on(face)`）；
  - `fillet` / `chamfer`：严格作用于当前选中的 `edge_indices`（若未选边则支持按方向筛选）；
  - `shell`：严格将当前选中的 `face_indices` 作为开口面传入 `part.shell(thickness, openings=[part.faces()[i] for i in face_indices])`；
  - `draft`（拔模斜度）：对选中面施加真实 `part.draft(faces, angle, plane)`；
  - `extrude` / `revolve` / `sweep` / `loft`：支持选择场景中的草图或面进行拉伸、绕轴旋转、沿路径扫掠、多截面放样；
  - `split` / `section`：使用原生 `split(part, plane)` 切分实体，或 `section(part, plane)` 提取横截面；
  - `mirror` / `grid_array` / `polar_array` / `translate` / `rotate` / `scale`；
* **CFD 专用前处理算子**：
  - `remove_fillets`：支持仅擦除用户选中的圆角面，或自动识别全部圆角面擦除；
  - `remove_faces`（孔洞/特征填平）：直接调用 `part.remove_faces([part.faces()[i] for i in selected_faces])`，一键删除选中的孔洞或凸台并由内核自动延伸愈合表面；
  - `cavity_extraction`（内流道水密提取）与 `heal`（几何拓扑修复）。

### 4. 统一工作区与具身 Agent 引擎 (`backend/workspace.py` & `backend/agent_engine.py`)
* **统一工作区 (`WorkspaceSession`)**：
  - 维护持久化的 Python 命名空间 `ns`、操作历史步骤列表 `history: List[HistoryStep]` 以及内存快照栈（支持 `undo()` 与 `redo()`）；
  - 无论是用户在视口中用鼠标完成了一次模态拉伸，还是在脚本框运行了代码，或是 Agent 执行了建模，全部统一调用 `workspace.execute_step(code, label)`，使**场景树、3D 视口、操作历史栈、Python 脚本编辑器**四者时刻保持 100% 同步。
* **具身 Agent 协同 (`AgentEngine`)**：
  - **上下文自动注入**：每次向 Agent 发送消息时，自动附带：
    1. 当前工作区所有实体变量摘要（名称、体积、面积、包围盒、是否有效流形）；
    2. 当前用户在视口中选中的拓扑元素详情（如 `Selected: [part.faces()[4] (plane, area=1200, normal=[0,0,1]), part.edges()[2] (line, length=40)]`）；
    3. 根据用户 Prompt 通过 `smlibpy.mcp.discovery` 自动检索出的最相关 `smlibpy` API 签名与用法示例；
  - **结构化动作与自愈循环**：Agent 直接生成针对当前会话变量和选区的 Python 代码，在 `workspace` 中执行；若内核报错（如圆角半径过大），自动捕获精准行号与原因进行自愈修正；同时支持 Agent 返回 `highlight_expressions` 在视口中主动高亮目标特征。

---

## 四、 代码规范契约 (`docs/CODE_STANDARDS.md`)

1. **命名与术语规范**：
   - 全局统一产品名称为 **SMLib Studio Next**，禁止在任何代码、注释或文档中出现旧参考项目的名称；
   - Python 遵循 PEP 8，`snake_case` 函数/变量，`PascalCase` 类名；JavaScript 遵循 ES2022 Modules，`camelCase` 函数/变量。
2. **模块体积与职责边界**：
   - 任何单个前端 JS 模块不超过 350 行；任何单个后端 Python 模块不超过 400 行；
   - 严禁在路由层 (`router.py`) 编写几何算法，严禁在视口渲染层 (`viewport.js`) 混入 DOM 表单逻辑。
3. **安全性与健壮性**：
   - 代码执行沙盒通过 AST 校验拦截系统危险模块（禁止导入 `os`, `sys`, `subprocess`, `socket`, `shutil`），仅开放 `smlibpy`, `math`, `numpy`；
   - 前端每次更新 B-Rep 容器时必须递归释放旧 `BufferGeometry` 与 `Material`，杜绝显存泄漏。

---

## 五、 验证与验收标准 (Acceptance Criteria)

1. **目录整洁度验收**：根目录仅保留 `server.py`, `requirements.txt`, `start.bat`, `README.md`, `.gitignore` 及规范子目录（`backend/`, `static/`, `docs/`, `tests/`），`git status` 干净。
2. **真实 B-Rep 拾取验收**：在视口中点击法兰盘顶面，高亮的是**整个顶面（含孔边界）**而非单个三角形，状态栏准确显示 `part.faces()[j]` 的真实面积与法向；点击圆孔边缘，高亮整条圆弧边并显示真实圆半径与周长。
3. **Blender 模态交互验收**：
   - 选中面按 `E` 移动鼠标可实时拉伸/开槽并支持左下角面板微调数值；
   - 选中特定一条边按 `Ctrl + B` 移动鼠标，仅对该条选定边完成倒圆角/倒角；
   - 选中孔内壁面按 `X`（或点击移除特征），调用 `remove_faces` 直接将该孔填平愈合。
4. **Agent 具身协同验收**：选中任意面后对 Agent 说“在这个面上垂直打一个半径 6 的通孔”或“将我选中的这条边倒 R4 圆角”，Agent 直接引用当前选中拓扑表达式完成精确建模。
5. **自动化测试验收**：`python tests/test_workspace_and_brep.py` 与 `python tests/test_api_e2e.py` 100% 通过。
