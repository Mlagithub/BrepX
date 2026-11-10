# BrepX

面向工程零件与流体机械前处理的**薄层**参数化 B-Rep 工作台：**文档是数据，几何是编译产物**。Agent 主导建模，人审阅与改参。

几何由 [smlibpy](https://github.com/awv-informatik/smlibpy) 0.6（SMLib NURBS 内核）提供；宿主是 DeepSeek Harness（dsh）。

## 三条不变量

1. **步骤只声明，不实现几何。** 注册表描述参数、输入角色、check 和一次内核调用；`sweep`/`loft`/`shell`/`helix` 这些形状操作由 smlibpy 提供。
2. **几何只在 Python 侧编译一次。** 浏览器加载导出的精确 B-Rep 用于显示与拾取，不重放文档步骤 —— 双份编译逻辑是禁止的。
3. **agent 只经 MCP 改文档。** 没有 shell、没有文件、没有网络；权限边界就是 MCP 的工具清单。

## 架构

| 层 | 位置 | 职责 |
| :--- | :--- | :--- |
| 文档 | `cadwork/design/document.py` | 不可变 `Document` + 原子 `ops`（add/update/remove/reorder）+ 版本 |
| 步骤 | `cadwork/design/steps.py` | 声明式步骤注册表：参数 schema、输入角色、check、一次内核调用 |
| 引用 | `cadwork/design/refs.py` | 语义选择：`nearest` / `largest` / `planar` / `concave` … |
| 校验 | `cadwork/design/checks.py` | 门禁；失败即 422，文档不动，返回可读 hint |
| 编译 | `cadwork/design/build.py` | 重放步骤 + 内容寻址缓存（LRU，删掉只损失时间） |
| 服务 | `cadwork/service/` | 一个 `CADService`，HTTP `/api` 与 MCP `/mcp` 同进程 |
| 宿主 | `agent/profile/` | dsh profile：只挂 CAD MCP，禁用一切能碰宿主的工具 |
| 视口 | `plugins/cadview/`（进行中） | DSH client plugin：`sidebarRightTabs` 视口 + `tool.call.toolview` 卡片，`smlibpy-three` 精确拾取 |

## 快速开始

```bash
python -m pip install -r requirements.txt

# 建出九特征叶轮（回归样本）
python -m cadwork.demo
python -m cadwork.demo --export .tmp/impeller

# 测试
python -m unittest discover -s cadwork/tests -t .

# 服务：HTTP + MCP 同进程
python -m cadwork.service --port 8765

# agent：装 profile 后只看见 CAD 工具
python agent/install.py
dsh --profile cad-agent
```

在 DSH 里看图：先起上面那个服务，再重启一次 `dsh web`。打开任意会话的右侧栏，指南里有 **CAD** 入口，点开就是一个 CAD 标签页：

- 顶部下拉选零件族（Impeller / Volute casing / Hollow blade）：**选中即按该族的默认参数重建**，不需要再点按钮；中间显示该族声明的参数，改完参数后按 **Build** 应用；
- 每次构建都替换当前文档的特征（不追加），状态行给出 `built <sample> at vN · 特征 · 面数 · 体积`；下拉会按文档里实际的零件自动校正，标签与模型始终一致；
- 特征芯片（`f1`、`v3`…）点击可启停单步，用来审阅「关掉这个圆角/抽壳会怎样」；底栏是 checks 结果，失败项带 hint；
- 一键验收（不需要浏览器）：`python scripts/accept_volute.py --all`，构建三个样本、跑 checks、导出 STEP/STL/PNG 并在任何一项失败时非零退出；
- 视口里拖拽转、滚轮缩放、点面读面积；状态行显示 `特征 · 面数 · 体积`。
- 视口是 `cadwork` 提供的 `/api/kernel-view` 页面（iframe）：它用 **import map 直接加载内核包**，内核在浏览器里跑，所以点击得到的是真实 B-Rep 面与精确面积。
- **不要用 esbuild 打包内核**：包的 `init` 用 `import.meta.url` 定位 wasm 和 probe worker，打包后 `init` 会永久 pending（同一份字节在 Node 里 164 ms）。`/api/probe` 保留了对照实验：打包版卡死、不打包版 491 ms 成功。

四个零件族都由同一套通用步骤组合出来：叶轮 = 回转 + 叶片放样 + 圆周阵列 + 布尔 + 圆角；蜗壳 = 螺旋 + 矩形截面 + 变截面扫掠 + 抽壳；空心叶片 = 扭转放样 + 抽壳；法兰 = 圆柱基本体 + 布尔 + 圆周阵列 + 倒角。

步骤表（30 个，全部是一次内核调用）：

| 类别 | 步骤 |
|---|---|
| 基本体 | `solid_box` `solid_cylinder` `solid_cone` `solid_sphere` |
| 轮廓 | `profile_rect` `profile_circle` `profile_polygon` `curve_spiral` `curve_helix` |
| 成体 | `extrude` `revolve_profile` `hub_revolve` `blade_loft` `sweep` `shell`（可命名 `openings`） `thicken_faces` |
| 孔 | `hole`（简单孔 / 沉头 / 沉孔，孔口自顶面起算，深度 0 为通孔） |
| 布尔/阵列 | `boolean` `pattern_circular` `pattern_linear` `pattern_grid` `mirror_part` |
| 修饰 | `fillet` `chamfer` `offset_solid` `split_part` `scale_part` |
| 放置 | `transform` |
| 场景扩展 | `tag_boundary` `cavity_extraction` |

引用种类（`part`/`faces`/`edges`/`curve`/`profile`）是**注册表**，不是枚举：`register_input_kind()` 加一种新种类不需要改编译引擎。步骤还可以声明**可选输入**（如 `shell.openings`），缺省即走闭壳。

加一个新零件族 = 在 `cadwork/samples/` 写一个文档构造器；只有需要新几何能力时才往注册表加**通用**步骤。

插件首次使用前要构建一次：`cd plugins/cadview && npm install && npm run build`（产出 `lib/viewport.mjs`，已被 `.gitignore` 忽略）。

## 验收

v1 的唯一验收线是**蜗壳**：从零用通用步骤组合建出，**不出现任何零件专用步骤**，编译与文档引擎零改动，checks 全绿，导出 STEP/STL。

做不到，就说明「通用」还没兑现 —— 不是参数没调好。

## 目录

```
cadwork/design/     文档、步骤、引用、校验、编译
cadwork/service/    HTTP + MCP + 存储 + 渲染
cadwork/samples/    叶轮、蜗壳、空心叶片（回归 + 验收）
plugins/cadview/    DSH client plugin（浏览器半 + 宿主空壳，无构建步骤）
agent/profile/      dsh profile（不含任何凭据）
scripts/            demo、内核探针、一键验收（accept_volute.py）
```

服务端只提供 API（`/api`）与 MCP（`/mcp`），不再挂独立前端；工作台只在 DSH 里。

`docs/` 与 `tasks/` 是本机知识（计划、架构说明），被 `.gitignore` 忽略，不进版本库。

## 状态

| 部分 | 状态 |
| :--- | :--- |
| 文档模型、语义引用、校验门禁、缓存、HTTP/MCP | 已完成 |
| 九特征叶轮样本（回归） | 已完成 |
| smlibpy 0.6 升级、通用步骤（`curve_spiral`/`curve_helix`/`profile_rect`/`sweep`/`shell`） | 已完成 |
| 蜗壳验收（螺旋 + 变截面扫掠 + 抽壳，4 步全通用） | 已完成 |
| DSH client plugin 骨架（装进 web profile、进入 boot 图） | 已完成 |
| 右侧栏 `CAD` tab（`sidebarRightTabs` + `sidebar.right.pane.tab`） | 已完成，浏览器实测 |
| 视口：three.js + 服务端 `scene`，轨道 / 缩放 / 点面拾取 | 已完成 |
| 交互式生成：样本下拉 + 参数 + Build | 已完成（叶轮 / 蜗壳 / 空心叶片 / 法兰） |
| 特征芯片启停、checks 面板、文档版本自动刷新 | 已完成，浏览器实测 |
| web 会话内的 agent 挂载 CAD MCP（`cad_*` 工具） | 已完成（服务日志见 `POST /mcp/` 会话） |
| 独立前端 `web/` | 已删除，工作台只在 DSH |
| `smlibpy-three` 精确拾取 | 已完成：视口是一个带 import map 的 iframe 页面，内核用它自己的模块运行；点面返回真实 B-Rep 面与精确面积（`face · 4259.3 mm²`）。原因见下 |
| CFD 边界字典、STEP 导入改造、交互式草图、多用户部署 | 不在 v1 |
| 旧栈（Command-Centric + 31 算子 + 静态前端） | 已删除，见 git 历史 |
