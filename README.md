# BrepX

面向 **CFD 工业流体仿真前处理**的 Agent 原生三维 B-Rep 几何工作台。

基于瑞士 SMLib NURBS 工业几何内核（`smlibpy`），提供精确 B-Rep 拓扑建模、内流道水密提取、表面物理边界语义标注与 STEP AP242 工业交付。

---

## 当前状态

**M1、M2、M3、M4 与 M5 五大里程碑已全量高质量交付！**

系统已完全确立 Command-Centric CAD (CC-CAD) 核心架构与专业工业级三维 Web 交互工作台：
1. **M1 Design 骨架**：结构化命令、纯函数事务管道、B-Rep 拓扑级视口容器、60 FPS 模态交互、无损撤销与重做。
2. **M2 增量重算与选择器稳定性**：DAG 依赖图、脏标记反向传播、内存 LRU 快照、增量重算引擎、选择器覆盖率 100.0%、失效自愈诊断。
3. **M3 进程隔离 Agent 适配器**：独立进程 FastAPI Agent 服务、Plan-as-Data（关键路径 ≤4）、KV Cache 亲和前缀、动作指纹防死循环与预算硬熔断；杀掉 Agent 进程主服务零影响。
4. **M4 领域算子与 CFD 交付**：31 个工业算子齐备、离心蜗壳与参数化叶轮全链路水密生成、去特征化与流道水体提取、STEP/STL/DXF/CFD 字典多格式交付。
5. **M5 工业 CAD 前端工作台重构**：
   - **交互手感**：Blender 风格模态拖拽，支持**直接敲键盘数字精准确认**（如输入 `-15.5`），60 FPS 显存响应；
   - **参数化时间线**：Fusion 360 风格底部特征时间线 (Timeline)，支持历史卡片双击就地微调改参并触发后端增量重算级联，以及黄色回退重构棒 (Rollback Bar)；
   - **工业工具箱**：31 个算子分类排布，两步式布尔拾取工作流（Target + Tool），Shift+A 就地快速添加；
   - **流体分析与度量**：动态交互剖切面 (Section Clipping)、双元素测距卡尺、多实体清单显隐与孤立、斑马线曲面连续性检验。

| 里程碑 | 内容 | 状态 |
| :--- | :--- | :--- |
| M1 | Design 骨架（零 AI）：点选 → 打孔 → 撤销 → 重做 | **已完成** |
| M2 | 语义选择器 + 增量重算 | **已完成** |
| M3 | 接入 Agent 适配器（独立进程，只提交命令） | **已完成** |
| M4 | 流体机械领域算子 + CFD 交付 | **已完成** |
| M5 | 工业 CAD 前端工作台重构（全功能、时间线、模态数字确认、测量剖切） | **已完成** |

---

## 架构与设计规范

- **前端工业工作台规格**：[`docs/ideas/frontend_workbench_spec.md`](docs/ideas/frontend_workbench_spec.md)
  布局架构、模态数字输入、两步布尔、底部时间线、多实体管理与测量探针设计标准。

- **最终架构设计**：[`docs/ideas/industrial-cad-architecture-final.md`](docs/ideas/industrial-cad-architecture-final.md)
  四层骨架、命令契约、增量重算、进程隔离边界、实施里程碑、A1–A7 假设验证与 Open Questions 决策。

- **产品意图宪章**：[`docs/intent/statement_of_intent.md`](docs/intent/statement_of_intent.md)

- **工程约束**：[`CONSTRAINTS.md`](CONSTRAINTS.md)

---

## 交互范式与键鼠速查

视口中心主义，手柄主导，Agent 作为副驾。

| 交互 / 快捷键 | 行为表现 |
| :--- | :--- |
| `1` / `2` / `3` | 拓扑拾取层级：顶点 / 边 / 面 |
| `Shift + 左键` | 累加多选拓扑元素 |
| `鼠标右键` | 依据当前拾取对象（面/边/空白/时间线）动态就地弹出操作气泡 |
| `Shift + A` | 鼠标位置呼出分类添加菜单（3D 图元、叶轮、成型特征） |
| `Space` / `F3` | 全屏居中命令搜索盘（支持中文拼音首字母与英文模糊匹配） |
| `Z` | 呼出 4 向饼状轮盘（Pie Menu）：带边着色 / 纯实体 / 纯线框 / 斑马线分析 |
| `E` | 选中面沿法向模态拉伸 / 开槽（拖拽零网络请求，可直接敲数字 Enter 确认） |
| `Ctrl + B` | 选中边模态倒圆角 / 倒角（按 `M` 键切换圆角/斜角，敲数字确认） |
| `Ctrl + 8` | 正视于选定面 (Normal To)：视角相机平滑对齐当前选中面的法向量 |
| `G` / `R` / `S` | 平移 / 旋转 / 缩放手柄（拖拽中按 `X`/`Y`/`Z` 锁定单轴，可敲数字确认） |
| `Alt + Z` | X-Ray 半透明透视 |
| `Ctrl + Z` / `Ctrl + Y` | 撤销 / 重做（走 Design 版本与命令管道重放） |
| 视口底部 | Fusion 360 风格特征时间线 (Timeline)，双击改参增量重算，支持黄色回退棒 |
| 视口左下角 | `Adjust Last Operation` 无损调参面板 |

---

## 环境与依赖

```bash
python -m pip install -r requirements.txt
```

Python 3.10+ / 3.11 推荐。几何内核依赖 `smlibpy`。

---

## 工程命令

```bash
# 全量测试（99 项单元与集成测试全部通过）
python -m unittest discover -s tests

# 质量门禁检查（模块行数、零抑制、分层依赖、第一性注释、进程隔离守卫）
python scripts/check_all_gates.py

# 拓扑选择器覆盖率审计（实测覆盖率 100.0%）
python scripts/selector_coverage.py

# 启动 CAD 主工作台服务（默认 http://127.0.0.1:8080）
python server.py

# 启动独立进程 Agent 服务（默认 http://127.0.0.1:8081）
python scripts/run_agent.py --port 8081
```

Windows 下亦可双击 `start.bat`。
