# ADR-003: 采用统一工作区会话 (`WorkspaceSession`)、代码即原始定义 (`Code-as-Original`) 与具身 Agent 共享命名空间

## Status
Accepted

## Date
2026-10-23

## Context
在重构前的版本中，系统存在三处严重的架构割裂：
1. **鼠标工具与 Agent 状态割裂**：右侧工具栏在 `tools_handler.py` 中用独立函数拼凑临时对象，而 `agent.py` 在临时字典里跑 `exec()`，两者没有共享的持久化会话历史与多对象命名空间；
2. **视口选区与 Agent 盲区割裂**：用户在 3D 视口中用鼠标选中了一个特定的面或一条边，但 Agent 完全不知道用户选了什么，只能靠正则表达式猜数字，无法响应“*在我刚选中的这个面上打一个沉头孔*”或“*把我选中的这几条边倒 R4 圆角*”这类最自然的工程指令；
3. **拓扑持久命名难题 (Topological Naming Problem)**：若在内存中维护一套自定义的树状修改器对象并绑定静态的面 ID，一旦用户修改了基础长方体的尺寸，SMLib 重新生成的 B-Rep 面顺序改变，下游特征就会引用错位甚至崩溃。

## Decision
借鉴 Blender `struct ID` 的 **`original` (原始定义) vs `is_evaluated` (评估网格)** 解耦思想，以及 `smlibpy.mcp` 的会话设计，确立以下核心架构：

1. **统一工作区会话 (`backend/workspace.py` - `WorkspaceSession`)**：
   - 维护单一、持久化的 Python 执行命名空间 (`self.ns`) 与有序步骤栈 (`self.history: list[HistoryStep]`)；
   - **代码即原始定义 (`Code-as-Original`)**：无论是人类通过鼠标模态操作符（如 `E` 拉伸、`Ctrl+B` 倒角、3D 视口画草图）触发的算子，还是 Agent 生成的建模指令，一律转化为标准、幂等的 `smlibpy` Python 代码段追加并执行于同一个 `WorkspaceSession` 中；
   - 每次执行前通过 `ast.parse` 静态审计拦截系统危险调用（禁止 `os`, `sys`, `subprocess`, `socket`, `open` 等，仅允许 `smlibpy`, `math`, `numpy`），并在发生几何异常 (`KernelError` / `ModelingError`) 时自动回滚至上一步状态快照。
2. **人机共享选区总线 (`Selection Bus`) 与具身 Agent 引擎 (`backend/agent_engine.py`)**：
   - 前端 `CADContext.selections` 实时记录用户点击选中的拓扑元素（如 `[{ expr: "part.faces()[4]", kind: "face", geom_type: "plane", area: 1200.0, normal: [0,0,1], center: [0,0,10] }]`）；
   - 当用户向 Agent 发送指令时，前端自动将当前 `selections` 与工作区所有活动实体摘要（`workspace.scene_summary()`）随请求一并提交；
   - `AgentEngine` 自动调用 `smlibpy.mcp.discovery` 检索与用户意图最相关的 `smlibpy` 原生 API 签名及文档片段，连同选区拓扑表达式一起注入大模型上下文（及本地语义引擎），使 Agent 能够直接写出 `part = part - Hole(6, 12).on(part.faces()[4])` 这样精确作用于用户选区的代码；
   - 支持 Agent 反向调用 `set_selection(expressions)` 在 3D 视口中主动高亮特定面或边。

## Alternatives Considered

### 方案 A：将 `smlibpy` 的 89 个函数分别封装为 89 个独立的 LLM Function Calling Tools
- **Pros**：表面上看符合标准 Tool Calling 格式。
- **Cons**：
  1. 89 个工具的 JSON Schema 会消耗数万 Token，导致大模型响应极慢且极易选错工具；
  2. CAD 建模高度依赖链式代数与循环表达式（例如 `part -= PolarLocations(35, 6) * CounterBoreHole(4, 8, 4, 12).on(part.faces().top())`），细碎的单函数 Tool 无法表达这种复合几何逻辑；
  3. `smlibpy` 官方 MCP (`smlibpy/mcp/server.py`) 已明确验证“**Code-as-Interface (`run_script` + `inspect` + `get_selection` + `discovery`)**”才是驱动 SMLib 内核的最佳范式。
- **Rejected**：高 Token 成本、低表达力，且与官方设计背道而驰。

### 方案 B：前端维护独立的 JSON 特征树，不生成也不依赖 Python 脚本
- **Pros**：前端无需关心 Python 语法。
- **Cons**：失去了导出独立可复现 `.py` 自动化脚本以供下游 CFD 批量参数化扫描（Design of Experiments）的核心优势，且必须自己重写一套复杂的拓扑引用求解器。
- **Rejected**：违背产品愿景声明中“全过程代码可复现”的核心交付标准。

## Consequences
- **正面影响**：
  - 人类鼠标操作、脚本编辑器与 AI Agent 三者真正实现了 **100% 状态同步与双向互操作**：人类用鼠标点选面，Agent 写代码加工；Agent 生成的模型，人类直接用鼠标选边按 `Ctrl+B` 倒角；
  - 完整保留可独立运行的 `.py` 脚本，随时可用于批处理变体生成。
- **实现约束**：
  - 算子生成的代码必须使用清晰的变量命名与注释步骤头（如 `# [Step 3] Fillet 2 edges (R=4.0 mm)`），保证脚本编辑器中的代码始终整洁可读。
