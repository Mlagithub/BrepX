# Implementation Task List: SMLib Studio Next

- [x] Task 1: 引入 Three.js TransformControls 并实现 Blender 级手柄模态循环 (G/R/S/X/Y/Z)
  - 描述: 挂载 TransformControls，绑定 `G` (移动)、`R` (旋转)、`S` (缩放) 以及 `X/Y/Z` 轴向锁定；拖拽时仅本地矩阵变换保证 60 FPS，松手时向后端结算并同步代码。
  - Acceptance: 视口选中模型按 G/R/S 可直接用鼠标流体拖拽，按 X/Y/Z 锁定单轴，松手后模型坐标与 Python 脚本自动更新。
  - Verify: 在浏览器中按 G 键拖动模型，检查帧率与松手后的模型位置。
  - Files: `static/app.js`, `static/style.css`, `static/vendor/TransformControls.js`

- [x] Task 2: 实现 Blender 快捷键流体系 (Shift+A 菜单, Tab 模式切换, Alt+Z 透视)
  - 描述: 视口按 `Shift + A` 弹出原生毛玻璃添加菜单；按 `Tab` 切换 Object/Edit 模式，`1/2/3` 切换顶点/边/面模式；按 `Alt + Z` 切换 X-Ray 半透明透视。
  - Acceptance: 按快捷键流畅呼出菜单并创建实体，模式与透视状态在视口中即时响应。
  - Verify: 浏览器自动化测试按键响应与视口表现。
  - Files: `static/index.html`, `static/app.js`, `static/style.css`

- [x] Task 3: 研发面向 CFD 的表面物理语义标注与导出系统
  - 描述: 后端增加 `semantic_manager.py`；前端增加“物理边界模式 (Boundary Mode)”开关；选面一键标注为 Inlet (深蓝), Outlet (鲜红), Wall (冷灰), Interface (暖橙)；平时恢复天蓝色，开启模式彩色高亮；导出 STEP/元数据清单。
  - Acceptance: 用户可在视口中为流体表面打标，边界属性在边界模式下正确着色，导出的 STEP/JSON 包含物理语义。
  - Verify: 编写端到端 API 测试验证打标与导出一致性。
  - Files: `semantic_manager.py`, `server.py`, `static/app.js`, `static/style.css`, `static/index.html`

- [x] Task 4: 研发流体前处理高阶工具（去特征化与反向内流道提取）
  - 描述: 在 `tools_handler.py` 中实现基于 SMLib 的特征反圆角 (`remove_fillets`)、孔洞填平 (`remove_faces`) 以及反向包围盒差集流体域提取 (`cavity_extraction`)。
  - Acceptance: 右侧工具栏与 API 新增流体前处理工具，复杂几何一键剔除小特征并生成纯净封闭流体域。
  - Verify: Python 单元测试验证体积变化与流道抽取有效性。
  - Files: `tools_handler.py`, `server.py`, `static/app.js`

- [x] Task 5: 升级 Agent 具身协同感知与自愈纠错闭环
  - 描述: 将当前选择面的物理语义注入 Agent 提示词，使 Agent 能基于视口物理语义完成多轮智能设计与自动修复。
  - Acceptance: 对 Agent 说“将当前面标记为入口，并沿内腔挖一个通孔”，Agent 自动理解并执行完成。
  - Verify: 真实浏览器端多轮对话自动化测试。
  - Files: `agent.py`, `server.py`, `static/app.js`

- [x] Task 6: 代码系统性简化与架构稳固化 (Code Simplification & Modularization)
  - 描述: 解耦 2013 行的单体 `app.js`，按职责拆分为 `viewport.js`, `gizmo.js`, `selection.js`, `boundary.js`, `tools.js`, `agent.js`；后端引入 `session_manager.py` 解耦状态与临时文件生命周期。
  - Acceptance: 单文件代码量下降 75% 以上，所有功能行为 100% 保持一致，全量回归测试绿灯通过。
  - Verify: 运行 `test_e2e.py` 与浏览器自动化截图测试。
  - Files: `server.py`, `session_manager.py`, `static/app.js`, `static/js/*.js`
