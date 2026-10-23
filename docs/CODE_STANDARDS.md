# SMLib Studio Next 代码与架构规范 (Code Standards & Architectural Contract)

> 本规范适用于 **SMLib Studio Next** 全栈代码库（`backend/` 与 `static/`），所有新增或重构代码必须严格遵守。

---

## 1. 品牌与术语规范 (Naming & Terminology)
* **唯一产品名称**：全局统一使用 **SMLib Studio Next**。
* **历史清理禁令**：严禁在任何源码、HTML 标题、UI 徽章、注释、接口字段或文档中出现任何早期参考 Demo 的名称或旧目录引用。
* **领域术语对齐**：
  - 拓扑层级严格使用 B-Rep 标准术语：`Body` (`Part`/`Shell`/`Sketch`)、`Face` (`face_index`)、`Edge` (`edge_index`)、`Vertex` (`vertex_index`)；
  - CFD 边界语义严格使用：`inlet`、`outlet`、`wall`、`symmetry`、`interface`、`internal`。

---

## 2. 目录与模块边界规范 (Module Boundaries)
* **根目录整洁守则**：
  - 仓库根目录只允许存放应用入口 (`server.py`, `start.bat`)、依赖配置 (`requirements.txt`, `.gitignore`) 与顶层说明 (`README.md`)；
  - 严禁在根目录放置临时抓包脚本、一次性调试脚本或测试截图。
* **后端分层 (`backend/`)**：
  - `router.py`：**仅负责** HTTP/REST 路由分发与 Pydantic 入参/出参校验，禁止编写任何几何建模逻辑；
  - `workspace.py`：**唯一状态中枢**，管理 Python 会话命名空间 (`ns`)、历史步骤 (`history`) 与 Undo/Redo 快照栈；
  - `brep_graphic.py`：**纯函数图形序列化层**，负责将 `smlibpy` 的 `Part`/`Sketch` 拆分为带精确拓扑索引 (`face_index`, `edge_index`, `vertex_index`) 的前端可渲染数据包；
  - `operators.py`：**几何算子实现层**，所有算子必须输出标准、可读、幂等的 `smlibpy` Python 代码交由 `workspace` 执行；
  - `agent_engine.py`：**具身 Agent 协同层**，共享 `workspace` 上下文与选区表达式，内置 `smlibpy.mcp.discovery` API 检索与自愈重试。
* **前端分层 (`static/js/`)**：
  - 单文件行数上限：**不超过 350 行**；
  - `context.js`：前端唯一状态源 (`CADContext`)，通过事件总线驱动 UI 与视口更新；
  - `viewport.js`：仅负责 Three.js 场景、相机、灯光与 B-Rep 拓扑容器渲染，每次更新模型必须递归调用 `.dispose()` 释放旧 `BufferGeometry` 与 `Material`；
  - `modal_ops.js`：严格实现 Blender 式 `invoke -> modal -> execute / cancel` 状态机协议。

---

## 3. Python 编码与安全规范 (Python Backend Standards)
* **类型安全**：所有公开函数与方法必须具备完整的 Python Type Hints (`from __future__ import annotations`)，API 载荷一律使用 `pydantic.BaseModel` 强类型校验。
* **AST 代码执行沙盒**：
  - 工作区在执行用户或 Agent 脚本前，必须经过 `ast.parse` 语法树审计；
  - **白名单模块**：仅允许导入 `smlibpy`, `math`, `numpy`；
  - **黑名单拦截**：严禁导入或调用 `os`, `sys`, `subprocess`, `shutil`, `socket`, `urllib`, `open`, `eval`, `exec`, `__import__`。
* **几何容差与流形校验**：
  - 所有生成三维实体的算子必须检查 `part.is_valid()`；若操作导致非流形或退化错误，必须捕获 `KernelError` / `ModelingError`，自动回滚至上一步状态并返回明确的几何失败原因。

---

## 4. 前端交互与 WebGL 性能规范 (Frontend & WebGL Standards)
* **真实拓扑映射**：
  - 禁止对合并三角网格的 `hit.faceIndex` (单个 Triangle) 直接当成 CAD 面使用；
  - 必须使用后端 `brep_graphic` 提供的 `faceMap`（三角形索引 ➔ 真实 `part.faces()[j]` 索引）与独立 `edge` 折线对象进行拾取与高亮。
* **60 FPS 模态循环守则**：
  - 在 `EXTRUDE_OT_face` (`E`)、`FILLET_OT_edge` (`Ctrl+B`)、`TRANSFORM_OT_gizmo` (`G/R/S`) 的 `modal()` 鼠标移动期间，**严禁发起任何网络请求**，仅在前端显存中实时更新预览网格或矩阵；
  - 仅在鼠标左键确认或按下 `Enter` 进入 `execute()` 阶段时，向后端提交一次确定性几何求解。
