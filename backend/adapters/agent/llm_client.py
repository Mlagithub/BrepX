"""OpenAI-compatible LLM HTTP client with structured configuration and error translation."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class AgentConfigError(Exception):
    def __init__(self, message: str, code: str = "CONFIG_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def to_diagnostic(self) -> dict[str, Any]:
        return {
            "error": "AgentConfigError",
            "message": self.message,
            "code": self.code,
        }


class AgentTransportError(Exception):
    def __init__(self, message: str, status_code: int = 0) -> None:
        super().__init__(f"Agent transport failure [{status_code}]: {message}")
        self.message = message
        self.status_code = status_code

    def to_diagnostic(self) -> dict[str, Any]:
        return {
            "error": "AgentTransportError",
            "message": self.message,
            "status_code": self.status_code,
        }


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    model: str
    api_key: str
    temperature: float = 0.0
    max_tokens: int = 1024
    timeout_s: float = 30.0

    def __post_init__(self) -> None:
        if not self.api_key or not self.api_key.strip():
            raise AgentConfigError("未配置大模型 API Key，请在设置中提供有效的访问密钥。", code="MISSING_API_KEY")


def chat(messages: list[dict[str, str]], config: LLMConfig) -> str:
    endpoint = config.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=data_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=config.timeout_s) as response:
            res_body = response.read().decode("utf-8")
            data = json.loads(res_body)
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8", errors="replace")
        raise AgentTransportError(err_msg[:200], status_code=exc.code) from exc
    except Exception as exc:
        raise AgentTransportError(str(exc)) from exc


def ping_llm(config: LLMConfig) -> dict[str, Any]:
    start = time.perf_counter()
    messages = [{"role": "user", "content": "ping"}]
    chat(messages, config)
    latency = round((time.perf_counter() - start) * 1000.0, 2)
    return {"ok": True, "model": config.model, "latency_ms": latency}
