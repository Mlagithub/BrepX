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

1. **前后端双向联动工作流**：
   - **参数化调节模式**：左侧提供直观的滑动条与数值输入（机械法兰、L型角码、衬套、CSG体），实时生成 3D 模型；
   - **Python 脚本工作台**：参数调节时自动同步生成规范的 Python `smlibpy` 代码；用户亦可在右侧直接编写/修改任意复杂的 Python 建模脚本，按 `Ctrl+Enter` 立即由后端 `smlibpy` 运算并实时三维渲染。
2. **Three.js 高精度工业 CAD 视口**：
   - 支持等轴测 (ISO)、正视 (Front)、俯视 (Top)、右视 (Right)、自适应居中 (Fit)；
   - 支持正交投影 (Orthographic) 与透视投影 (Perspective) 无缝平滑切换；
   - 双向光源、地面网格标尺、三维基准坐标轴、高对比度特征轮廓边线。
3. **全格式工业交付中心**：
   - 实时生成并下载工业标准 **STEP 文件** (可直接导入 SolidWorks / Fusion 360 / NX / AutoCAD 等专业 CAD 软件)；
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
├── server.py              # FastAPI 后端服务 (参数化解析、脚本沙盒执行、STEP/STL导出)
├── requirements.txt       # Python 依赖清单
├── start.bat              # Windows 一键启动脚本
├── static/                # 前端静态 Web 资产
│   ├── index.html         # CAD 工作台主界面 (cax-viewer 风格布局)
│   ├── style.css          # 工程灰/暗黑主题样式表
│   ├── app.js             # Three.js 视口控制、GLTF渲染管线、参数同步交互
│   └── vendor/            # 本地离线 Three.js 及其扩展库 (r186)
│       ├── three.module.js
│       ├── OrbitControls.js
│       └── GLTFLoader.js
├── cax_reverse/           # cax-viewer.com 逆向源码与分析文件
├── test_templates.py      # 参数化模板单元测试
└── test_e2e.py            # 端到端 API 接口与导出测试
```
