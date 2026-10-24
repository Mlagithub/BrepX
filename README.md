# BrepX

**BrepX** 是专为 **AI + CAD + CAE (特别是 CFD 工业流体仿真全栈体系)** 设计的现代化、Blender 式流体交互、Agent 原生的三维 B-Rep 几何建模工作台。

本系统基于瑞士 **SMLib NURBS 工业几何内核 (`smlibpy`)** 构建，将精确的 B-Rep 拓扑边界表示（点、边、环、面、壳、体）、Blender 5.1.2 级视口模态交互手感（`G/R/S` 空间变换、`E` 选面交互拉伸、`Ctrl+B` 选边交互倒角、3D 视口直接绘制 2D 草图、左下角 `Adjust Last Operation` 实时参数微调）与共享统一工作区 (`WorkspaceSession`) 的具身 AI Agent 深度融合，支持一键去特征化 (`remove_fillets` / `remove_faces`)、内流道水密提取 (`cavity_extraction`) 以及表面物理边界语义 (`Inlet` / `Outlet` / `Wall` / `Interface`) 标注与工业标准 **STEP AP242** 交付。

---

## Quick Start (快速启动)

### 1. 环境要求
- Python 3.10 – 3.14（推荐 Python 3.11+）
- 现代桌面浏览器（Chrome / Edge / Firefox / Safari，支持 WebGL 2.0）

### 2. 安装依赖与启动
```bash
# 1. 安装依赖
python -m pip install -r requirements.txt

# 2. 启动工作台服务 (默认监听 http://127.0.0.1:8080)
python server.py
```
在 Windows 环境下，也可直接双击运行根目录的 `start.bat`。

---

## Commands (常用命令)

| Command | Description |
|---------|-------------|
| `python server.py` | 启动 BrepX Web 服务 (`http://127.0.0.1:8080`) |
| `python -m unittest discover -s tests` | 运行全部后端单元测试与 API 端到端集成测试 |
| `python -m unittest tests/test_workspace_and_brep.py` | 单独运行统一工作区与 B-Rep 拓扑图形容器测试 |
| `python -m unittest tests/test_api_e2e.py` | 单独运行全算子、Agent 协同与 CFD 边界导出测试 |

---

## Core Interaction & Shortcuts (Blender 标准键位)

| Shortcut / Action | Mode | Description |
|-------------------|------|-------------|
| **`Tab`** | Global | 在 **对象模式 (Object Mode)** 与 **编辑模式 (Edit Mode)** 之间切换 |
| **`1` / `2` / `3`** | Edit Mode | 切换真实 B-Rep 拾取层级：`1` 拓扑顶点 (`Vertex`)、`2` 拓扑边 (`Edge`)、`3` 拓扑面 (`Face`) |
| **`Shift + 左键`** | Edit Mode | 累加多选多个 CAD 拓扑面或多条特征边 |
| **`Shift + A`** | Viewport | 在鼠标光标处呼出 **Add 添加菜单**（三维图元、2D 草图、高阶特征） |
| **`E`** | Edit Mode (Face/Sketch) | **交互式拉伸 / 开槽 (`EXTRUDE_OT_face`)**：沿选中面法向移动鼠标实时拉出凸台（正值）或挖槽切削（负值），支持直接敲入数字确认 |
| **`Ctrl + B`** | Edit Mode (Edge) | **交互式倒圆角 / 倒角 (`FILLET_OT_edge`)**：移动鼠标实时调整选中边的圆角半径（按 `M` 切换圆角 Fillet / 倒角 Chamfer） |
| **`G` / `R` / `S`** | Object Mode | 呼出平移 (`G`)、旋转 (`R`)、缩放 (`S`) 模态变换手柄；拖拽时按 **`X` / `Y` / `Z`** 锁定单轴 |
| **`X` / `Delete`** | Edit Mode (Face) | **直接建模特征消除**：对选中的孔内壁面调用 `remove_faces` 直接填平愈合，或对圆角面调用 `remove_fillets` 恢复锐边 |
| **`Alt + Z`** | Viewport | 切换 **X-Ray 半透明透视模式**（便于观察内部流道与盲孔） |
| **`Ctrl + Z` / `Ctrl + Y`** | Global | 工作区无损撤销 (Undo) / 重做 (Redo) |

---

## Architecture & Documentation (架构与设计文档)

项目采用严格的分层解耦架构，核心设计决策与规范详见 `docs/` 目录：

### 顶层愿景与规格规范
- **产品最终愿景声明 (Statement of Intent)**：[`docs/intent/statement_of_intent.md`](docs/intent/statement_of_intent.md)
- **产品概念单页 (Concept One-Pager)**：[`docs/ideas/cfd_cad_workbench_concept.md`](docs/ideas/cfd_cad_workbench_concept.md)
- **系统功能规格书 (System Specification)**：[`docs/spec/SPEC-cfd-cad-workbench.md`](docs/spec/SPEC-cfd-cad-workbench.md)
- **深度架构重构方案 (Refactoring Plan)**：[`docs/spec/REFACTORING_ARCHITECTURE_PLAN.md`](docs/spec/REFACTORING_ARCHITECTURE_PLAN.md)
- **代码与架构契约规范 (Code Standards)**：[`docs/CODE_STANDARDS.md`](docs/CODE_STANDARDS.md)
- **Blender 5.1.2 核心数据结构逆向手册**：[`docs/blender_architecture_dna.md`](docs/blender_architecture_dna.md)

### 架构决策记录 (ADRs)
- **[ADR-001](docs/decisions/ADR-001-brep-topological-graphic-pipeline.md)**：采用真实 B-Rep 拓扑级图形容器协议替代合并 glTF 网格传输
- **[ADR-002](docs/decisions/ADR-002-blender-modal-operator-and-adjust-last-loop.md)**：采用 Blender 式双通道模态操作符 (`Modal Loop`) 与 `Adjust Last Operation` 机制
- **[ADR-003](docs/decisions/ADR-003-unified-workspace-session-and-embodied-agent.md)**：采用统一工作区会话 (`WorkspaceSession`)、代码即原始定义 (`Code-as-Original`) 与具身 Agent 共享命名空间
- **[ADR-004](docs/decisions/ADR-004-cfd-surface-semantic-persistence-and-step-export.md)**：面向 CFD 的拓扑面级物理边界语义绑定与 STEP AP242 / 字典双轨导出

---

## Project Structure (工程目录结构)

```text
C:\Users\keep_\work\smlib\
├── server.py                      # 应用启动入口
├── requirements.txt               # Python 依赖声明
├── start.bat                      # Windows 一键启动脚本
├── README.md                      # 项目总览与架构导航
├── backend/                       # 核心后端包
│   ├── workspace.py               # 统一工作区引擎 (AST 沙盒、持久化命名空间、Undo/Redo、Adjust Last)
│   ├── brep_graphic.py            # B-Rep 拓扑图形序列化器 (独立 Face/Edge/Vertex 缓冲与解析几何参数)
│   ├── operators.py               # 选区敏感真实 SMLib 几何算子库 (图元、草图、特征、CFD 去特征/流道提取)
│   ├── agent_engine.py            # 具身 CAD Agent 引擎 (选区感知、smlibpy.discovery RAG、自愈执行)
│   ├── semantic_patches.py        # CFD 表面物理边界语义管理与几何指纹重绑定
│   └── router.py                  # FastAPI REST 路由与 Pydantic 契约
├── static/                        # 前端工程资产
│   ├── index.html                 # Blender 风格沉浸式工作台界面
│   ├── style.css                  # 暗黑工业风样式表
│   ├── app.js                     # 前端主控制器 (< 250 行)
│   ├── js/                        # 模块化前端子系统 (单文件 < 350 行)
│   │   ├── context.js             # 全局 CADContext 响应式状态总线
│   │   ├── viewport.js            # Three.js B-Rep 容器渲染与显存生命周期管理
│   │   ├── selection.js           # 真实 B-Rep 拓扑面/边/点拾取、悬停预高亮与 Shift 多选
│   │   ├── modal_ops.js           # Blender 模态操作符 (E 拉伸、Ctrl+B 倒角、G/R/S、X 消除、F9 微调)
│   │   ├── sketcher.js            # 3D 视口工作平面交互式草图绘制器
│   │   ├── boundary.js            # CFD 物理边界模式整面着色
│   │   └── agent_panel.js         # 具身 Agent 协同面板与选区胶囊同步
│   ├── utils/                     # Three.js 几何辅助库
│   └── vendor/                    # Three.js r186 核心与扩展库
├── docs/                          # 规范、规格书与 ADR 架构决策库
├── tasks/                         # 实施计划 (plan.md) 与任务清单 (todo.md)
└── tests/                         # 自动化单元测试与端到端集成测试
```

---

## Contributing & Code Standards
参与开发或通过 Agent 扩展功能前，请务必阅读 [`docs/CODE_STANDARDS.md`](docs/CODE_STANDARDS.md)：
1. 保持模块精简（前端单文件 < 350 行，后端单文件 < 400 行）；
2. 所有几何修改必须通过 `WorkspaceSession` 执行并生成可读的 `smlibpy` 代码；
3. 每次更新 WebGL 几何体必须调用 `.dispose()` 释放显存；
4. 提交前确保 `python -m unittest discover -s tests` 全部通过。
