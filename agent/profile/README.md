# cad-agent profile

用于 dsh 的 CAD 专用 profile：挂载 `cad` MCP（`http://127.0.0.1:8765/mcp/`），
提供只读文件工具（读 skill references、STEP/IGES），并禁用 shell、网络、插件管理、
子 agent 和文件写入。

## 安装

```bash
python agent/install.py            # 复制 profile + 全部 skill 到 $DSH_HOME
python -m cadwork.service --port 8765
dsh --profile cad-agent
```

`agent/install.py` 会安装：

- `$DSH_HOME/profiles/cad-agent/{package.json,cordis.patch.yml}`
- `$DSH_HOME/skills/{impeller,volute,blade,brepx-plan,smlibpy}`

`smlibpy` skill 从已安装的 wheel（`smlibpy/skill`）复制，含 `references/` 与
`recipes/`。

## 工具边界

- `cad` MCP：读/写文档、计划、编译、执行、渲染、导入。
- `read` / `read_image`：只读，能读宿主机任意路径（`fs-local` 的 `cwd` 不是
  containment），用于 skill references 和 STEP 原文件。
- 写入默认关闭：`write/edit/apply_patch: false`。需要写文件时改用
  `dsh-fs-sandbox` + workspace 写权限，而不是打开宿主写。
- 无 `pwsh`/`bash`、无 web、无 subagent、无 plugin manager。
- 领域计划放在文档里（`plan`/`plan_edit`），不放进 dsh 的 `todo`/`goal`。

## 模型路由：不要提交

这个目录**没有任何 provider / baseURL / token**。模型路由属于本机配置，追加到
`$DSH_HOME/cordis.patch.yml`（home 级覆盖层），不要写进仓库。

```yaml
- id: llm-pi-ai
  name: '@deepseek-ai/dsh-llm-pi-ai'
  config:
    providers:
      <provider>:
        api: openai-responses
        baseURL: <your endpoint>
        headers:
          Authorization: 'Bearer <token 从环境变量或密钥库读取>'
        models:
          - id: <model>
            name: <model>
- id: agent-default-model
  name: '@deepseek-ai/dsh-agent-default-model'
  config:
    provider: <provider>
    model: <model>
```

`:8765` 是 `python -m cadwork.service` 的默认端口，与
`cadwork/service/__main__.py` 保持一致。
