# SMLib Web Studio (smlibpy × cax-viewer)

> 基于瑞士 ClassCAD 开源几何内核 **smlibpy** 与 **cax-viewer (SMLib Modeler)** 逆向架构融合的现代三维 CAD 几何建模工作台。

---

## 一、 项目背景与深度理解 (smlibpy)

[smlibpy](https://smlibpy.classcad.ch) 是由瑞士 St. Gallen 的 **AWV Informatik (ClassCAD 团队)** 推出的全新 Python 3D 几何建模库，其核心构建于享誉业界的 **SMLib (Solid Modeling Library)** NURBS 几何建模内核之上（该内核最早由 Solid Modeling Solutions 开发，并被广泛应用于工业 CAD 软件，近期也开源于 NVIDIA Omniverse usd-brep 项目中）。

### 核心特性
1. **纯正工业级 B-Rep / NURBS 内核**：区别于基于多边形网格（Mesh）的建模工具，SMLib 处理精确的曲面几何、NURBS 曲线曲面方程以及严谨的拓扑边界表示（Vertex-Edge-Loop-Face-Shell-Solid）。
2. **极简优雅的 Pythonic 语法**：
   - 构造原语：`Box(l, w, h)`, `Cylinder(r, h)`, `Sphere(r)`, `Cone(r1, r2, h)`, `Torus(R, r)`。
   - 布尔运算重载：并集 `a + b`、差集 `a - b`、交集 `a & b`。
   - 特征操作：`part.fillet(edges, r)` (圆角)、`part.chamfer(edges, d)` (倒角)、`shell` (抽壳)、`extrude` (拉伸)、`revolve` (旋转)、`sweep` (扫掠)、`loft` (放样)。
   - 几何查询：体积 `part.volume`、表面积、包围盒等。
3. **无缝读写标准工业 CAD 格式**：
   - 读取：**STEP**, **USD**, **DXF**
   - 导出：**STEP (ISO-10303-21)**、**STL**、**glTF**、**USD**、**DXF**
4. **内置 AI Agent MCP 支持**：提供 `smlibpy-mcp` Server，允许大模型 Agent 通过工具调用直接进行参数化设计与零部件建造。

---

## 二、 逆向工程分析报告 (https://www.cax-viewer.com/smlib/)

通过 REA (`reverse-engineer-anything`) 对 `https://www.cax-viewer.com/smlib/` 进行深度逆向，揭示了其现代 Web CAD 的技术实现：

### 1. 核心架构解密
- **纯前端 WebAssembly 几何内核计算**：
  - 核心模块为编译为 WASM 的 SMLib 内核：`smlib.8ff7d050f38c00d4.wasm` (~8.3 MB) + `smlib.js` Emscripten 胶水层。
  - **Worker 多线程隔离**：采用 `geometry-worker.js` + `kernel-client.js`。主线程将编译好的 `WebAssembly.Module` 传递给 Worker，每次建模调用 `smlib_execute`，避免复杂几何运算阻塞 UI 渲染。
  - **交互格式**：通过 JSON 描述 `action`（如 `create`, `boolean`, `curve_create`, `fillet`, `step_import`, `step_export`），中间模型保存在虚拟内存文件系统中的 `.smb` 二进制 BREP 数据。
- **渲染管线 (Three.js)**：
  - 内核输出 `result.shape` 包含顶点网格 `mesh.positions` 与拓扑边线 `topology.edges`。
  - 前端使用天蓝色柔光 CAD 材质 (`#80baff`) 渲染实体网格，配合深色抗锯齿轮廓线，呈现干净利落的机械工程图效果。
  - 支持面选择 (`faceMap`) 和边选择 (`edgeMap`) 级拾取。
- **参数化与特征树 (Feature Graph)**：
  - 支持“带孔圆角板”、“草图驱动零件”、“轴类零件”等典型参数化零部件的受约束重建。

---

## 三、 本次融合设计与 Demo 创新 (SMLib Web Studio)

我们将 **smlibpy (Python 后端计算)** 与 **cax-viewer (Three.js 前端交互视觉体系)** 深度融合，打造了完整的 Web CAD 工作台：

1. **🤖 AI 智能建模 Agent（自然语言对话式 CAD）**：
   - **自然语言输入**：支持用户用中文自然语言描述意图（如“帮我建一个带4个对称螺栓孔的管道连接法兰，外径80，内孔30，厚度12”）；
   - **双模架构 (Dual-Engine)**：
     - **内置本地精准语义 CAD 引擎**：无需配置任何 API Key，开箱即用支持多类常见机械特征与多轮微调；
     - **外部大模型 (LLM) 接入**：支持用户在界面设置自定义 Base URL / API Key / Model（兼容 OpenAI、DeepSeek、Qwen、Ollama 等），具备代码自愈重试纠错能力；
   - **3D 视口与代码编辑器全贯通**：Agent 生成代码后自动在后端的 SMLib 内核中执行，即时刷新 3D 渲染，并将生成的 Python 源码同步至编辑器。
2. **🛠️ 完整复刻 cax-viewer 右列几何造型工具栏 (32+ 工具全功能可用)**：
   - **三维图元与经典构件**：草图驱动零件、带孔圆角板、长方体 (`Box`)、圆柱 (`Cylinder`)、球体 (`Sphere`)、圆锥 (`Cone`)、圆环 (`Torus`)、定位孔 (`Hole`)；
   - **布尔运算体系**：布尔并集 (`+`)、布尔差集 (`-`)、布尔交集 (`&`)、高级布尔运算参数设置；
   - **平面轮廓与草图**：直线、矩形、圆、圆弧、折线、样条曲线 (`B-Spline`)；
   - **高级构造特征（激活原网页未实现的功能）**：
     - 拉伸 (`Extrude`)、旋转体 (`Revolve`)、空间扫掠 (`Sweep`)、多截面放样 (`Loft`)；
     - 倒角 (`Chamfer`)、倒圆角 (`Fillet`)、薄壁抽壳 (`Shell`)、法向偏移 (`Offset`)；
     - 对称镜像 (`Mirror`)、网格阵列 (`Grid Array`)、圆周环阵列 (`Circular Array`)、平面切分 (`Slice`)、轴旋转 (`Rotate3D`)、平移复制 (`Copy`)；
   - 每个工具点击均弹出专业参数配置弹窗，支持独立创建或在当前实体上累加特征，并同步生成 Python 源码！
3. **🎯 点、线、面、体分级拾取与拓扑测量 (Selection Hierarchy)**：
   - 顶部工具栏支持切换：**实体 (Solid)**、**面 (Face)**、**边 (Edge)**、**点 (Vertex)** 拾取模式；
   - **面拾取**：自动计算法向量 `[nx, ny, nz]`、判断顶面/底面/侧面朝向，并在模型表面覆盖半透明金色高亮面；
   - **边拾取**：吸附最近的特征边缘线段，黄色高亮显示并测量边线长度；
   - **点拾取**：吸附至模型几何顶点，放置三维标靶指示小球并显示三维绝对空间坐标 `(X, Y, Z)`；
   - **实时几何卡片**：动态显示包围盒外形尺寸 (X×Y×Z)、实体表面积 (mm²)、体积 (mm³)、拓扑面数/边数。
4. **🔄 典型几何变换 (平移 / 旋转 / 缩放)**：
   - **平移 (Translate)**：输入沿 X、Y、Z 轴的位移增量进行空间移动（`part.translate(dx, dy, dz)`）；
   - **旋转 (Rotate)**：绕空间 X/Y/Z 轴旋转指定角度（`part.rotate(axis, angle)`）；
   - **缩放 (Scale)**：三维等比自由缩放（`part.scale(factor)`）；
   - 变换完成后实时更新 3D 视口，并在 Python 代码工作台中同步追加变换代码。
5. **参数化调节模式**：
   - 左侧提供直观的滑动条与数值输入（机械法兰、L型角码、衬套、CSG体），实时生成 3D 模型；
6. **🌊 CFD 表面物理边界语义标注与导出 (CFD Boundary Semantics)**：
   - **分级物理语义打标**：选定面后一键标记为 `Inlet` (速度/流量入口), `Outlet` (压力出口), `Wall` (壁面), `Interface` (流固交界面) 或 `Symmetry` (对称面)；
   - **物理边界着色模式**：遵循工程规范，仅在开启 **【🌊 边界模式】** 时以物理高饱和颜色高亮（入口深蓝、出口玫红、壁面冷灰、交界面暖橙），退出后自动恢复标准 CAD 天蓝金属色；
   - **导出 CFD 边界字典 JSON**：一键导出包含补丁名称、面索引、面积、法向矢量的标准 JSON 数据，直接对接 OpenFOAM / Fluent 网格划分与求解。
7. **🌀 CFD 几何前处理专用算子**：
   - **去特征化·反圆角 (`remove_fillets`)**：一键消除导入模型上的微小圆角，相邻平面自动延伸缝合为尖锐棱边，防止体网格畸变与数量爆炸；
   - **内流道反向水密提取 (`cavity_extraction`)**：对阀体或中空管道外壳执行反向包络差集，一键抽取纯净内部流体域水密实体。
8. **🎨 Blender 5.1.2 级交互手柄与快捷键流 (Blender-like UX)**：
   - **TransformControls 空间手柄**：支持按 `G` (移动)、`R` (旋转)、`S` (缩放) 呼出三维手柄；
   - **轴向锁定约束**：拖拽手柄时按下 `X` / `Y` / `Z` 即可锁定单一轴向；
   - **就地添加菜单 (`Shift + A`)**：在光标处呼出浮动添加菜单，快速插入实体、草图与高阶特征；
   - **模式无缝切换**：按 `Tab` 键切换对象模式与编辑模式，按 `1` (点)、`2` (边)、`3` (面) 快速切换拾取粒度；按 `Alt + Z` 切换 X-Ray 半透明透视显示。
9. **全格式工业交付中心**：
   - 实时生成并下载工业标准 **STEP (AP242) 文件** (可直接导入 SolidWorks / Fusion 360 / NX / AutoCAD 等专业 CAD 软件)；
   - 导出 **CFD 边界字典 (JSON)**；
   - 导出 **STL 文件** (直接对接 3D 打印切片机)；
   - 导出 **glTF 3D 场景文件**；
   - 导出完全独立的 **Python 建模源码** (`.py`)。

---

## 四、 本地部署与启动

### 1. 环境要求
- Python 3.10 ~ 3.14 (已在 Windows Python 3.11 环境下测试通过)
- 现代浏览器 (Chrome, Edge, Firefox, Safari)

### 2. 一键启动 (Windows)
直接双击项目根目录下的 **`start.bat`** 即可自动安装依赖并启动浏览器。

### 3. 手动命令行启动
```bash
# 1. 安装核心依赖
pip install smlibpy fastapi uvicorn pydantic numpy

# 2. 启动服务 (默认端口 8080)
python server.py
```
启动后在浏览器中打开：**`http://127.0.0.1:8080`**

---

## 五、 项目结构清单
```text
C:\Users\keep_\work\smlib\
├── session_manager.py     # 会话管理与文件导出中心 (解耦状态存储与文件生命周期)
├── semantic_manager.py    # CFD 表面物理边界标注管理器 (Inlet/Outlet/Wall/Interface)
├── tools_handler.py       # SMLib 32+ 项核心建模算子底层封装 (CSG, Loft, Sweep, Revolve...)
├── agent.py               # CAD Agent 核心 (支持外部大模型接入与本地语义解析引擎)
├── server.py              # FastAPI 路由网关与静态托管
├── requirements.txt       # Python 依赖清单
├── start.bat              # Windows 一键启动脚本
├── static/                # 前端静态 Web 资产
│   ├── index.html         # CAD 工作台主界面 (包含 Agent、视口、右侧工具栏与 Shift+A 菜单)
│   ├── style.css          # 工程灰/暗黑主题样式表、弹窗组件与浮动菜单
│   ├── app.js             # [已解耦精简] 前端主入口，胶水绑定子模块 (<470 行)
│   ├── js/                # [模块化重构子系统]
│   │   ├── viewport.js    # Three.js 场景、相机系统、标准视角与渲染循环 (~120 行)
│   │   ├── gizmo.js       # Blender 级 TransformControls 空间手柄与快捷键 (~100 行)
│   │   ├── selection.js   # 点/线/面/体分级拾取与高亮指示器 (~130 行)
│   │   ├── boundary.js    # CFD 物理边界模式网格着色与标注 (~90 行)
│   │   ├── tools.js       # 右侧 32 项几何工具弹窗表单与 Shift+A 菜单 (~180 行)
│   │   └── agent.js       # AI Agent 对话历史与 Prompt 胶囊 (~110 行)
│   ├── utils/             # Three.js 几何工具库 (BufferGeometryUtils, SkeletonUtils)
│   └── vendor/            # 本地离线 Three.js 及其扩展库 (r186)
├── docs/                  # 顶层设计文档库
│   ├── intent/            # 意图宪章 (statement_of_intent.md)
│   ├── spec/              # 功能规格说明书 (SPEC-cfd-cad-workbench.md)
│   ├── ideas/             # 概念单页 (cfd_cad_workbench_concept.md)
│   └── blender_architecture_dna.md # Blender 5.1.2 核心数据结构手册
└── test_e2e.py            # 端到端 API 自动化回归测试
```
