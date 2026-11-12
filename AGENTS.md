# AGENTS.md

BrepX 是以 smlibpy 为几何内核、以 dsh 为宿主的参数化 B-Rep 工作台。
本文件是本仓库的工程约束，所有人和 agent 的改动都必须遵守。

## 代码规范（强制）

### 一、代码不引用文档

代码必须自证。注释、docstring、测试名、异常文案和标识符里不写：

- `见 docs/xxx.md`、`详见设计文档`、`按计划/规范第 3 节`；
- `per the plan`、`as described in ...`、`see RFC ...` 这类出处指引；
- 开发任务、里程碑、评审记录的名称。

需要背景时，把约束本身写进注释——不变量、量纲、失败模式、兼容对象——
而不是让读者再去读另一份文件。领域名词（如 NACA 4 位数翼型）不是文档引用。

### 二、禁用开发阶段标记

不在标识符、注释、docstring、测试类名或字符串里使用 `v1`/`v2`、`p1..p9`、
`s1..s3`、`M0`、`P0`、`阶段二`、`phase 2`、`batch 3` 之类代指开发阶段或
生成批次的标记。它们只记录写作顺序，不表达任何工程事实。

- 标识符用语义命名：`plate` / `boss` / `bore` / `bolt_hole` /
  `spiral` / `sweep` / `shell`；测试名描述行为：`PlanValidationTests`、
  `MilestoneRecordingTests`。
- 版本与进度属于 git 历史、任务系统和发布记录，不属于代码。
- 真实领域版本（文件格式、API 版本）用完整名称定义常量并注释语义，
  不写成裸 `v1`。

### 三、注释只写第一性内容

注释回答“为什么必须这样”，不回答“这行在做什么”。应当写：

- 非显然的不变量、约束、量纲、顺序要求、所有权和副作用；
- 失败模式，以及为什么这样失败而不是那样失败；
- 内核/平台限制、性能与安全上的权衡、需要保持兼容的外部对象。

不要写：

- 复述代码的注释（`# 返回结果`）；
- 装饰性分区横幅（`# ---------------- params ----------------`）；
- 历史叙事（“旧版”“不再手写”“替代了 X”）；
- 过程记录（`TODO: 下一步`、`阶段一先这样`）。待办放进任务系统。

函数和类的 docstring 写职责、契约与失败行为，不写路线图、进度或归属。
能用命名表达的信息不写注释。

## 修改后自检

```powershell
# 1. 不得出现文档引用（写文件路径的常量不算引用）
git grep --untracked -n -I -E '见 ?docs/|详见|参考 ?docs/|per the plan|as described in|see the (doc|spec)|按.*(文档|计划)' -- cadwork scripts agent plugins

# 2. 不得出现阶段/批次标记（人工确认领域版本除外）
git grep --untracked -n -I -E '(^|[^A-Za-z0-9_])(v|p|s|M|P)[0-9]+([^A-Za-z0-9_]|$)' -- cadwork scripts agent plugins

# 3. 语法与测试
python -m compileall -q cadwork scripts agent
python -m unittest discover -s cadwork/tests -t .

# 4. 内核清单变更后重新生成基线
python scripts/kernel_inventory.py --check --write
```

代码评审时，违反以上任一条的 diff 不予通过。
