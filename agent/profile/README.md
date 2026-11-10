# cad-agent profile

给 dsh 用的 CAD 专用 profile：只挂 `cad` MCP（`http://127.0.0.1:8765/mcp/`），并禁用所有能碰宿主的能力（shell、文件、网络、插件管理、子 agent）。

## 安装

```bash
python agent/install.py            # 复制 package.json + cordis.patch.yml 到 $DSH_HOME/profiles/cad-agent
python -m cadwork.service --port 8765
dsh --profile cad-agent
```

## 模型路由：不要提交

这个目录里**没有任何 provider / baseURL / token**。模型路由属于本机配置，追加到 `$DSH_HOME/cordis.patch.yml`（home 级覆盖层），不要写进仓库：

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

`:8765` 是 `python -m cadwork.service` 的默认端口，与 `cadwork/service/__main__.py` 保持一致。

## 为什么禁用这些工具

agent 的职责是改文档，不是改机器。把 shell/文件/网络收走之后，「它能不能做这件事」就退化成「MCP 里有没有这个工具」，权限边界变成一个可审查的列表，而不是一句承诺。
