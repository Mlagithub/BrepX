# Technical Implementation Plan: CFD CAD Workbench (SMLib Studio Next)

> 本规划基于已确认的顶层意图宪章 (`docs/intent/statement_of_intent.md`) 与系统功能规格书 (`docs/spec/SPEC-cfd-cad-workbench.md`) 制定。

---

## 1. 架构目标与组件依赖图

```text
[Frontend Viewport] ──────────┐
(TransformControls, Gizmos)   │
                              ▼
[CADContext & Keymap] ──► [REST / API Gate] ──► [smlibpy Geometry Engine]
(Tab, Shift+A, G/R/S, 1/2/3)  │                 (CSG, Fillet, Defeaturing)
                              ▼                           │
[Boundary Semantic Manager] ──┴───────────────────────────┴──► [STEP AP242 / Export]
(Inlet/Outlet/Wall Patching)
```

### 组件实施依赖顺序：
1. **视口交互核心 (Slice 1)**：实现 TransformControls 手柄与 G/R/S 键盘驱动，解决交互延迟。
2. **快捷操作体系 (Slice 2)**：实现 `Shift+A` 浮动菜单与 `Tab` (1/2/3) 模式切换。
3. **物理语义管理 (Slice 3)**：实现 BoundaryPatch 数据模型、边界模式着色与属性导出。
4. **CFD 前处理算子 (Slice 4)**：实现去特征化 (Defeaturing) 与反向内流体域提取 (Cavity Extraction)。
5. **Agent 双向具身闭环 (Slice 5)**：Agent 语义打标与流体前处理全流程打通。

---

## 2. 风险识别与缓解策略

1. **TransformControls 与 OrbitControls 鼠标事件冲突**：
   - *风险*：拖动变换手柄时相机同时发生旋转，造成视口错乱。
   - *缓解策略*：监听 `transformControls.addEventListener('dragging-changed', e => controls.enabled = !e.value)`，拖拽手柄期间严格锁定相机控制器。
2. **STEP 导出保留面名称属性**：
   - *风险*：普通 STEP 导出可能丢失面级属性。
   - *缓解策略*：在导出 STEP 时采用 SMLib 原生带有 Face Name 标记的命名面导出机制，同时生成配套的标准物理语义元数据 JSON/YAML 侧袋文件（Sidecar Metadata），供所有 CFD 软件 100% 可靠读取。
3. **去特征化几何破面风险**：
   - *风险*：对非规则几何执行 `remove_fillets` 可能产生非流形边。
   - *缓解策略*：执行前后进行 `part.is_valid` 校验，若自愈失败保留原实体并给予温和提示。

---

## 3. 分阶段验证检查点 (Checkpoints)

* **Checkpoint 1**：在视口中点击模型，按 G/R/S 出现三维手柄，按 X/Y/Z 可锁定轴向，拖拽 60 FPS 顺滑无掉帧，松手后端脚本更新。
* **Checkpoint 2**：视口任意位置按 `Shift+A` 弹出浮动菜单并成功创建图元；按 `Tab` 与 `1/2/3` 流畅切换模式。
* **Checkpoint 3**：开启“物理边界模式”，选定面一键标注为 Inlet（深蓝）与 Outlet（鲜红），退出模式恢复天蓝；导出包含属性。
* **Checkpoint 4**：一键去除复杂模型倒角 (`remove_fillets`) 并提取内流体域 (`cavity extraction`)。
* **Checkpoint 5**：通过对话让 Agent 自动识别并打标物理边界，完成端到端自动化。
