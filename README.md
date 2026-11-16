# BrepX

面向工程零件与流体机械前处理的**参数化 B-Rep 工作台**：文档是数据，几何是编译产物。
人给意图与方向，LLM 维护建模计划，确定性编译器生成内核调用，人审里程碑。

几何由 [smlibpy](https://github.com/awv-informatik/smlibpy) 0.6（SMLib NURBS 内核）
提供；宿主是 DeepSeek Harness（dsh）。

## 开发规范

本仓库的强制工程约束见 [AGENTS.md](AGENTS.md)：代码不引用文档、不使用阶段/批次
标记符、注释只写第一性内容（为什么必须这样，而不是复述代码）。所有改动与代码评审
都必须遵守。

## 三条不变量

1. **计划声明意图，编译器写代码。** LLM 产出 `ModelingPlan`（目标/特征/依赖/参数/验收），
   编译器校验后 lower 成 `BuildProgram`；LLM 不直接写 smlib 调用，也不拥有 `run_script`。
2. **文档是真相源。** 几何只在 Python 侧编译一次；脚本是 IR，smlibpy session 是缓存。
   落盘的是文档、计划与内容哈希，不是脚本。
3. **agent 只经 MCP 改文档。** 只读文件工具用于 skill references 和 STEP 导入；写入、
   shell、网络、子 agent 默认关闭。

## 架构

| 层 | 位置 | 职责 |
| :--- | :--- | :--- |
| 内核动作 | `cadwork/design/kernel_actions.py` | 从 smlibpy 签名生成 `k_*`：参数、角色、返回类型；语义覆盖表只写角色/调用方式 |
| 适配器 | `cadwork/design/adapters.py` | `pattern`、`tag_boundary`、`import_base`、`place_on`、`cavity` |
| 计划 | `cadwork/design/plan.py` | `ModelingPlan`：goal/feature/check 节点、依赖、`Expect`、JSON、CAS |
| 编译器 | `cadwork/design/plan_compile.py` | 校验 → 文档 ops / `BuildProgram` IR；报告 issues 与覆盖率 |
| 验收 | `cadwork/design/verify.py` | volume/area/faces/edges/solids/watertight/bbox/distance/intersects |
| 执行 | `cadwork/design/backends/` | `LocalBackend`（进程内）与 `ScriptBackend`（本地 `run_script`） |
| 文档/构建 | `cadwork/design/document.py`、`build.py` | 不可变 `Document` + 原子 ops + 内容寻址缓存 |
| 服务 | `cadwork/service/` | 一个 `CADService`：HTTP `/api` 与 MCP `/mcp` 同进程；JSONL 领域事件 |
| 宿主 | `agent/profile/` | dsh profile：CAD MCP + 只读文件 + skills |
| 视口 | `plugins/cadview/` | DSH client plugin：右侧 CAD 标签、计划树、拾取、toolview |

## 快速开始

```bash
python -m pip install -r requirements.txt

# 构建四类样例（叶轮/蜗壳/空心叶片/法兰）
python -m cadwork.demo
python -m cadwork.demo --export .tmp/impeller

# 测试
python -m unittest discover -s cadwork/tests -t .

# 服务：HTTP + MCP 同进程
python -m cadwork.service --port 8765

# agent：安装 profile 与 skills，然后启动
python agent/install.py
dsh --profile cad-agent
```

## 计划工作流

工具（dsh 命名空间为 `mcp__cad__*`）：

| 工具 | 用途 |
|---|---|
| `state` | 文档版本、特征、checks、metrics、计划摘要、待处理意图 |
| `probe` / `resolve` | 量测、试解析引用/拾取点；自然语言 → 特征 |
| `catalog` | 生成的 `k_*` 与适配器、参数 schema |
| `plan` / `plan_edit` | 读计划；add/update/remove 节点，revision CAS |
| `plan_compile` | dry-run：结构、action、参数、引用、覆盖率 |
| `plan_run` | 执行一个 ready 节点；feature 提交里程碑，check 只量测 |
| `preview` / `commit` / `revert` / `variants` | 直接编辑、回退、方案比选 |
| `render` | 多视图 PNG；`import` 冻结 STEP/IGES 基准体 |
| `intents` | 读/清人的待处理便签 |

一次典型建模：

1. `state` 读版本与计划；
2. `plan_edit` 加节点（按依赖顺序）；
3. `plan_compile` 修完所有 issue；
4. `plan_run` 逐个 ready 节点；失败即停，改参数后重跑；
5. `render` / `state` 复核；`commit` 之外的所有写入都带 `base_version`。

## 工作台（cad-web）

```bash
python -m cadwork.service --port 8765
dsh --profile cad-web --port 3081
# 打开终端打印的 URL；选择工作区后，CAD Agent 默认为建模 agent
```

- 左侧对话输入自由意图；右侧 `CAD` 标签显示真实 B-Rep、计划里程碑、参数、checks 与导出。
- 底部“描述要做的改动”可直接发送给当前对话；文档下拉、新建、刷新在视口顶部。
- Agent 对新建请求调用 `new_document`，对已有工作调用 `documents`/`state`；计划形状不确定时调用 `plan_schema`。
- 失败恢复：节点失败不写文档；改参数后重跑受影响节点，依赖检查随计划走。

安装 profile、skills 与已构建的 cadview：先在 `plugins/cadview` 执行 `npm run build`，再运行 `python agent/install.py --web --force`。

## 组件测试（真实浏览器）

服务启动后打开 `http://127.0.0.1:8765/gen-tests`，页面逐个调用运行中的内核，覆盖
清单里的全部 152 个 GEN；每个用例写 JSON 与 STEP，页面逐行给出证据链接。

```bash
python -m cadwork.service --port 8765
# 浏览器打开 http://127.0.0.1:8765/gen-tests
```

浏览器实跑证据保存在 [artifacts/gen-tests/browser-mwdawbfs](artifacts/gen-tests/browser-mwdawbfs/)（本地目录，已加入 `.gitignore`，不随仓库提交）：
152 份 JSON、78 份 STEP、152 张 PNG、4 张页面截图、`manifest.json` 与 `summary.json`。

## 内核清单

`python scripts/kernel_inventory.py --check` 枚举 smlibpy 0.6.2 的全部公开 callable
（156 顶层函数 + 41 类的 497 个方法，共 653 个），每个标注去向：`GEN`/`ADAPTER`/
`REF`/`MEASURE`/`SERVICE`/`DEFER`/`N/A`。未分类数必须为 0；新增/删除会进入
`kernel_actions.baseline.json` 的 diff。

`features.py` 的 `FeatureSpec` 由内核签名生成：`FEATURES = generated_actions() + ADAPTERS`。
域宏（叶轮/叶片/蜗壳）是计划模板或样例，不是文档类型。

## 双执行后端

- `LocalBackend`：进程内调用 `spec.build`，用于文档构建与等价性基准。
- `ScriptBackend`：编译器把 AST 生成确定性脚本，经本地 `python -m smlibpy.mcp`
  的 `run_script` 执行；每文档一个 session，失败事务回滚，重启从已提交节点重放。
- 同一计划的最终 STEP sha256 应一致；不等价不切换默认后端。
- `plan_run(..., executor="script")` 可让一个节点先经脚本后端执行，再提交本地文档；
  发射器未覆盖的 action 会返回 `SCRIPT_FAILED`，此时用 `executor="local"`。

## 日志

- agent 侧：dsh 的 session log（`~/.dsh/sessions/.../session.v4.jsonl.zstd`）、
  startup log、Web 会话导出；**不重复开发**。
- 领域侧：文档 `Milestone` + 计划节点状态是权威审计；`cadwork/service/events.py`
  写一条薄 JSONL（`CADWORK_HOME/logs/events.jsonl`），只记 id/耗时/错误码，
  不记几何 payload；`GET /api/docs/{id}/timeline` 从文档/计划派生。

## 样例与验收

四个样例都由生成的 `k_*` 组合：

- **叶轮**：多边形回转轮盘 + 5 段叶片 loft + 圆周阵列 + 布尔 + 圆角 + 三个边界 + 流体域；
- **蜗壳**：螺旋 + 矩形截面 + 变截面 sweep + shell；
- **空心叶片**：扭转 loft + shell；
- **法兰**：圆柱 + 融合 + 通孔 + 螺栓阵列 + 倒角。

```bash
python -m cadwork.demo --sample impeller
python scripts/accept_plan.py        # 计划：编译、逐节点、checks、导出
python scripts/accept_face_volute.py # 面锚定：拾取面 -> 螺旋扫掠 -> 布尔
python scripts/accept_volute.py --all
```

验收线：计划可编译、每个节点 checks 通过、失败不写文档、重启可重放、Local/Script
最终 STEP 一致、旧文档类型报 `UNKNOWN_FEATURE_TYPE`。

## 视口

`plugins/cadview` 需要构建一次：`cd plugins/cadview && npm install && npm run build`
（产出 `lib/workbench.mjs`，被 `.gitignore` 忽略）。视口用 import map 直接加载内核包，
点选得到真实 B-Rep 面与面积；不要用 esbuild 打包内核（`init` 会 pending）。

## 边界

- 窄域：叶轮/蜗壳/叶片/法兰与同类回转/扫掠/布尔零件；不是通用 CAD。
- 拓扑命名未解决：上游改动后引用可能 `REF_RETARGETED`，必须显式重选。
- `DEFER` 的内核能力（deform/NURBS/region 等）没有被绑定为生成动作；需要时先在
  `kernel_actions.py` 加语义覆盖，再写测试。
