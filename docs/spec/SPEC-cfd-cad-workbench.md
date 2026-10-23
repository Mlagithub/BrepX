# Spec: 面向 CFD 工业仿真的流体交互与 Agent 原生 CAD 建模工作台 (SPEC-cfd-cad-workbench)

---

## 1. Objective (目标与愿景)
为 **AI + CAD + CAE (特别是 CFD 工业流体仿真全栈体系)** 构建轻量、沉浸、流体交互、Agent 原生的现代三维 CAD 几何工作台。
彻底解决传统 CAD 前处理简单操作繁复、高阶曲面门槛高两大卡点，支持“从零参数化流道设计”与“外部 STEP 导入去特征/提取内流道”，并让几何表面能够携带完备的**物理边界语义 (Inlet / Outlet / Wall / Interface)** 随工业标准 STEP (AP242) / 网格数据无缝交付给下游求解器。

---

## 2. Tech Stack (技术栈与依赖)

* **底层几何内核**：SMLib C++ NURBS Kernel via `smlibpy 0.4.0` (运行在 Python 3.11/3.13 运行时环境)
* **后端服务框架**：FastAPI + Uvicorn + Pydantic v2 + NumPy
* **前端渲染与视口引擎**：Three.js (r186) + OrbitControls + TransformControls (用于 Blender 式 G/R/S 实时手柄) + GLTFLoader
* **前端界面与交互**：Vanilla ES Modules (原生响应式组件, 极简 HUD, 无重型第三方框架冗余)
* **Agent 协议**：兼容 `smlibpy-mcp` 的 Code-as-Interface 模式，支持 OpenAI/DeepSeek/Ollama 兼容协议与本地内置 CAD 语义解析引擎

---

## 3. Commands (命令清单)

* **启动服务 (Dev/Prod)**：
  `python server.py` (监听 `http://127.0.0.1:8080`)
* **Windows 一键拉起**：
  `start.bat`
* **API 与端到端回归测试**：
  `python test_e2e.py`
* **浏览器全交互与渲染测试**：
  `python test_browser_actions.py`
* **依赖安装**：
  `python -m pip install -r requirements.txt`

---

## 4. Project Structure (工程结构设计)

```text
C:\Users\keep_\work\smlib\
├── server.py              # FastAPI 网关：路由分发、会话状态保持、格式导出、静态托管
├── agent.py               # CAD Agent 中枢：自然语言理解、Prompt 模板、代码自愈重试
├── tools_handler.py       # SMLib 32+ 项核心建模算子底层封装 (CSG, Loft, Sweep, Revolve...)
├── semantic_manager.py    # [新增] 表面物理语义标注管理器 (Inlet/Outlet/Wall 属性分配与持久化)
├── requirements.txt       # Python 运行环境依赖声明
├── start.bat              # Windows 一键执行入口
├── docs/
│   ├── intent/
│   │   └── statement_of_intent.md  # 顶层意图宪章
│   ├── spec/
│   │   └── SPEC-cfd-cad-workbench.md  # [本规范文档]
│   └── blender_architecture_dna.md # Blender 5.1.2 逆向核心数据结构手册
├── static/
│   ├── index.html         # 全屏 Blender 式视口、上下文浮动菜单、状态栏
│   ├── style.css          # 暗黑工程灰主题、浮动 HUD、半透明抽屉
│   ├── app.js             # 前端控制中枢：Modal 操作符、拾取、视口渲染
│   ├── utils/             # BufferGeometryUtils, SkeletonUtils
│   └── vendor/            # Three.js 核心库与控件 (r186)
└── test_e2e.py            # 自动化接口与回归测试套件
```

---

## 5. Core Data Models & Schemas (核心数据结构契约)

### 5.1 表面物理语义模型 (Boundary Semantic Annotation)
用于标记几何表面属于 CFD 仿真的何种边界条件：
```python
# 后端模型 (Pydantic / Python)
class BoundarySemanticType(str, Enum):
    INLET = "inlet"           # 速度入口 / 质量入口
    OUTLET = "outlet"         # 压力出口 / 自由流出
    WALL = "wall"             # 无滑移固体壁面 / 绝热壁面
    SYMMETRY = "symmetry"     # 对称面
    INTERFACE = "interface"   # 流固耦合或多相流交界面
    INTERNAL = "internal"     # 内部流道特征面

class BoundaryPatch(BaseModel):
    id: str                   # 唯一补丁 ID
    name: str                 # 物理边界名称 (例如 "inlet_1", "hot_wall")
    semantic_type: BoundarySemanticType
    face_indices: List[int]   # 关联的 B-Rep 面序号列表
    selector_expr: str        # SMLib 语义选择器表达式 (如 "part.faces().filter(lambda f: f.center[0] > 50)")
    color_hex: str            # 视口标记颜色 (Inlet: 蓝色, Outlet: 红色, Wall: 灰色, Interface: 橙色)
    area: float               # 补丁总面积 (mm²)
```

### 5.2 前端全局上下文总线 (`CADContext`)
借鉴 Blender `bContext`，作为人机协同与操作符调度的唯一事实源：
```typescript
interface CADContext {
  mode: 'OBJECT' | 'EDIT_FACE' | 'EDIT_EDGE' | 'EDIT_VERTEX';
  activeObject: {
    id: string;
    name: string;
    volume: number;
    area: number;
    bbox: { min: number[], max: number[], size: number[] };
  };
  selection: {
    type: 'solid' | 'face' | 'edge' | 'vertex' | 'none';
    hitPoint: [number, number, number];
    normal?: [number, number, number];
    faceIndex?: number;
    edgeIndex?: number;
    semanticExpr?: string; // 传给 Agent 的表达式，如 "part.faces().top()"
  };
  semanticPatches: BoundaryPatch[]; // 当前实体挂载的所有物理边界定义
}
```

---

## 6. Code Style (代码与开发规范)

* **Python 规范**：强类型注解 (`typing.Annotated`, `Optional`, `List`, `Dict`)，遵循 PEP 8，错误处理绝不盲目捕获，抛出清晰异常；
* **SMLib 建模代码生成规范**：
  ```python
  from smlibpy import *
  
  # 必须使用干净、确定性、高精度的语义化表达
  part = Box(100, 80, 15)
  part = part.fillet(part.edges().parallel_to(Z), 6.0)
  
  # 语义化命名实体表面供下游 CFD 读取
  inlet_face = part.faces().filter(lambda f: f.center[0] < -45)
  outlet_face = part.faces().filter(lambda f: f.center[0] > 45)
  ```
* **JavaScript / WebGL 规范**：严格遵循 ES Modules，资源分配后必须考虑 `.dispose()` 防止 WebGL 显存泄漏，拖拽交互必须由 GPU 矩阵承载。

---

## 7. Testing Strategy (测试验证体系)

1. **几何内核健壮性测试 (Kernel Unit Tests)**：
   - 验证实体运算（CSG、Loft、Sweep、Fillet、Shell、Offset）的流形性 (`is_valid`) 与容差边界；
2. **物理语义读写一致性测试 (Semantic Roundtrip Test)**：
   - 验证为 Face 打标 ➔ 导出 STEP AP242 ➔ 重新读取验证属性是否完整无损；
3. **真实浏览器视口测试 (Headless Browser Integration Test)**：
   - 验证 TransformControls 手柄拖拽帧率（>50 FPS）与松手后的网络结算；
   - 验证 Agent 对话式建模与视口选区双向联动。

---

## 8. Boundaries & UX Conventions (设计约定与边界)

* **交互模式约定 (User Confirmed)**：
  - **物理边界着色规则**：物理边界语义（Inlet/Outlet/Wall 等）**仅在“物理边界模式 (Boundary Mode)”下彩色高亮显示**（入口蓝、出口红、壁面灰、交界面橙），平时默认保持标准 CAD 天蓝金属材质，保持视口纯粹利落；
  - **快捷键对齐**：完全按照 **Blender 标准键位** 执行：
    - `G`：抓取移动 (Grab/Translate)
    - `R`：旋转 (Rotate)
    - `S`：缩放 (Scale)
    - `X` / `Y` / `Z`：手柄轴向锁定约束
    - `Shift + A`：在鼠标光标处呼出添加图元浮动菜单
    - `Alt + Z`：X-Ray 半透明透视观察切换
    - `1` / `2` / `3`：在编辑模式下切换顶点、边、面拾取
    - `Tab`：对象模式与编辑模式切换
* **Always Do (必须遵循)**：
  - 导出的几何模型必须通过 `part.is_valid` 水密流形性检验；
  - 视口拖动手柄必须在前端显存矩阵层即时预览，不可在拖拽中频繁阻塞请求后端；
  - 任何对几何产生修改的操作必须同步反映在 Python 代码工作台中。
* **Never Do (坚决禁止)**：
  - **严禁**在此项目中引入计算网格剖分器（如生成四面体/多面体体网格）；
  - **严禁**在此项目中调用外部 CFD 数值求解器；
  - **严禁**在此项目中构建神经网络代理模型训练管线。

---

## 9. Success Criteria (可测试验收指标)

- [ ] **物理语义打标**：用户在视口中点击模型表面（或 Agent 对话），可将选定面命名为 `inlet` / `outlet` / `wall`，并在视口中以对应物理颜色高亮区分；
- [ ] **语义属性导出**：导出的 STEP / 几何数据完整保存各 Patch 的命名与边界类型；
- [ ] **流体流道提取 (Cavity/Flow Domain Extraction)**：提供一键布尔反向包裹提取内流场几何的能力；
- [ ] **去特征化修面 (Defeaturing)**：支持通过指令一键消除小倒角 (`remove_fillets`) 和缝合小螺栓孔 (`remove_faces`)；
- [ ] **Blender 式流体手柄**：支持按 G/R/S 呼出手柄进行 60 FPS 顺滑变换，松开确认并生成代码；
- [ ] **全流程 Agent 闭环**：Agent 能在感知当前选区与物理语义的前提下，完成端到端的零件建模与流体域准备。
