# ADR-002: 采用 Blender 式双通道模态操作符 (`Modal Loop`) 与 `Adjust Last Operation` 机制

## Status
Accepted

## Date
2026-10-23

## Context
本项目明确确立了“**以 Blender 式视口手柄与鼠标直接操作为主、Agent 具身协同为辅**”的交互范式。然而，Web 浏览器（Three.js）与后端（Python `smlibpy` C++ 内核）之间存在物理进程与 HTTP 网络边界：
1. **高频鼠标移动与重型 B-Rep 求解的延迟冲突**：
   当用户在视口中选中一个面按下 `E` 键移动鼠标拉伸，或选中一条边按下 `Ctrl + B` 移动鼠标调整圆角半径，鼠标以 60~120 Hz 的频率产生 `pointermove` 事件。如果每次鼠标移动都向后端发起 HTTP 请求调用 SMLib 进行布尔切削与 NURBS 求交，单次往返（20~80 ms）会导致视口严重卡顿、掉帧，丧失直接操作手感。
2. **事后精确调参的幂等性需求**：
   工程师在用鼠标直觉拉出一个大概的拉伸高度（如 `23.4 mm`）或圆角半径（如 `4.2 mm`）后，往往需要在视口左下角将其修改为精确的工程整数（如 `25.0 mm` 或 `5.0 mm`）。如果修改参数只是在当前已变形的模型上再叠加一次操作，会导致重复拉伸或在同一条已圆滑边上二次倒角报错。

## Decision
借鉴 Blender 5.1.2 源码中 `wmOperatorType` 的生命周期（详见 [`docs/blender_architecture_dna.md`](../blender_architecture_dna.md)），采用 **前端高频模态预览 (`invoke -> modal`) + 后端确定性结算与快照重算 (`execute -> adjust_last`)** 双通道机制：

1. **前端模态循环 (`static/js/modal_ops.js` & `sketcher.js`)**：
   - **`invoke(ctx, event)`**：校验当前选区（如 `EXTRUDE_OT_face` 要求至少选中 1 个拓扑面或草图；`FILLET_OT_edge` 要求至少选中 1 条拓扑边），记录初始屏幕坐标与 3D 基准点/法向，锁定相机旋转，进入活跃模态；
   - **`modal(ctx, event)`**：在鼠标移动 (`pointermove`) 或数字键敲击期间，**绝不发起任何后端网络请求**。将鼠标屏幕位移投影到 3D 法向或径向向量上，在 WebGL 显存中实时更新半透明预览几何体（Preview Mesh / Wireframe）与 HUD 数值标尺，保持 60 FPS 满帧跟手；
   - **`execute(ctx)` / `cancel(ctx)`**：用户左键点击或按 `Enter` 时，退出模态循环并向后端发送唯一一次 `/api/workspace/execute_operator` 请求；按 `Esc` 或右键则直接清除预览几何体，零副作用恢复原状。
2. **左下角 `Adjust Last Operation` 无损回滚重算机制 (`backend/workspace.py`)**：
   - 每次执行算子前，`WorkspaceSession` 自动保存前置历史步索引 (`pre_step_index`) 与该算子的结构化描述符 `LastOperatorRecord(operator_id, params, target_selections)`；
   - 操作完成后，视口左下角自动浮现 `#adjust-last-panel` 面板展示当前算子的参数控件；
   - 当用户在面板中修改任何数值时，前端调用 `/api/workspace/adjust_last`，后端先将工作区无损恢复至 `pre_step_index`，再用更新后的参数重新执行该算子并替换最后一步脚本，实现与 Blender `F9` 面板完全一致的无损调参。

## Alternatives Considered

### 方案 A：鼠标移动时通过 WebSocket 流式调用后端 SMLib 实时重算 B-Rep
- **Pros**：拖拽过程中看到的就是 100% 精确的 B-Rep 圆角或布尔结果。
- **Cons**：复杂圆角 (`fillet`) 或螺旋扫掠 (`sweep`) 在 C++ 内核中单次耗时可达 50~500 ms，且鼠标划过非法边界（如半径超过相邻边间距的一半）时内核会频繁抛出 `ModelingError`，导致视口闪烁与队列阻塞。
- **Rejected**：违反 60 FPS 流体交互准则。

### 方案 B：所有工具均点击按钮弹出居中模态对话框填表提交
- **Pros**：实现最简单，无需编写 3D 空间射线投影与动态预览网格。
- **Cons**：打断工程师的视口注意力，退化为早期粗糙 Demo 的表单填数模式，无法对标 Blender 的直接建模体验。
- **Rejected**：不符合产品核心交互定位。

## Consequences
- **正面影响**：
  - 鼠标交互达到原生 60 FPS 丝滑体验，同时支持在模态拖拽中直接敲击键盘数字（如 `E -> 25 -> Enter`、`Ctrl+B -> 4 -> Enter`、`G -> X -> 30 -> Enter`）完成精确工程输入；
  - 直觉拖拽与事后精确改数（左下角 F9 面板）无缝衔接。
- **实现约束**：
  - `modal_ops.js` 与 `sketcher.js` 中的临时预览几何体（导引线、半透明拉伸框、草图橡皮筋线）必须统一挂载在独立的 `previewGroup` 下，并在 `execute()` 或 `cancel()` 时彻底 `.dispose()` 清理。
