"""Independent Agent service FastAPI application running in isolated process."""

from __future__ import annotations

import json
import urllib.request
from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.adapters.agent.llm_client import AgentConfigError, LLMConfig
from backend.adapters.agent.service import handle_turn

app = FastAPI(
    title="BrepX-Agent-Service",
    description="Isolated Agent Process communicating strictly via HTTP Command/Query API",
    version="1.0.0",
)


class LLMConfigModel(BaseModel):
    base_url: str
    model: str
    api_key: str
    temperature: float = 0.0
    max_tokens: int = 1024
    timeout_s: float = 30.0


class AgentTurnRequest(BaseModel):
    prompt: str
    selections: list[str] = Field(default_factory=list)
    host_url: str = Field(default="http://127.0.0.1:8080")
    config: LLMConfigModel


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "agent_isolated"}


@app.post("/turn")
async def execute_agent_turn(payload: AgentTurnRequest) -> dict[str, Any]:
    try:
        cfg = LLMConfig(
            base_url=payload.config.base_url,
            model=payload.config.model,
            api_key=payload.config.api_key,
            temperature=payload.config.temperature,
            max_tokens=payload.config.max_tokens,
            timeout_s=payload.config.timeout_s,
        )
    except AgentConfigError as exc:
        raise HTTPException(status_code=400, detail=exc.to_diagnostic())

    query_endpoint = payload.host_url.rstrip("/") + "/api/query"
    try:
        with urllib.request.urlopen(query_endpoint, timeout=10.0) as resp:
            q_data = json.loads(resp.read().decode("utf-8"))
            body_dict = q_data.get("body") or {}
            view_dict = {
                "version": q_data.get("version", 1),
                "summary": body_dict,
                "selections": [{"selector": s} for s in payload.selections],
                "faces": body_dict.get("faces", []),
                "edges": body_dict.get("edges", []),
            }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to connect to BrepX host at '{payload.host_url}': {exc}",
        )

    res = handle_turn(
        prompt=payload.prompt,
        view=view_dict,
        config=cfg,
        host_url=payload.host_url,
    )
    return res
