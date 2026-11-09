"""FastAPI REST routing endpoints for BrepX Command and Query channels."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.adapters.agent.llm_client import AgentConfigError, LLMConfig, ping_llm
from backend.adapters.agent.service import handle_turn
from backend.adapters.export.exporters import (
    export_cfd_dict,
    export_dxf,
    export_step,
    export_stl,
)
from backend.adapters.export.journal_to_python import journal_to_python
from backend.core.command import Command
from backend.core.design import Design
from backend.query.agent_view import build_agent_view
from backend.session import session

router = APIRouter(prefix="/api")


def _serialize_journal(records: list[Any]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for r in records:
        cmd = r.command
        target_dict = (
            {"base": cmd.target.base, "expr": cmd.target.expr}
            if cmd.target is not None
            else None
        )
        tool_dict = (
            {"base": cmd.tool.base, "expr": cmd.tool.expr}
            if cmd.tool is not None
            else None
        )
        serialized.append({
            "command": {
                "command_id": cmd.command_id,
                "op": cmd.op,
                "target": target_dict,
                "tool": tool_dict,
                "params": dict(cmd.params),
                "idempotency_key": cmd.idempotency_key,
                "replaces": cmd.replaces,
            },
            "version": r.version,
            "result_summary": r.result_summary,
        })
    return serialized


class SelectorRefModel(BaseModel):
    base: str = Field(..., description="Base geometry source ('prev' or 'c<digits>')")
    expr: str = Field(..., description="Topological semantic selector expression")


class AssertionModel(BaseModel):
    name: str = Field(..., description="Physical assertion identifier")
    args: list[Any] = Field(default_factory=list, description="Assertion arguments")


class CommandModel(BaseModel):
    command_id: str = Field(..., description="Unique command identifier")
    op: str = Field(..., description="Registered operator identifier")
    target: SelectorRefModel | None = Field(default=None, description="Primary topological target")
    tool: SelectorRefModel | None = Field(default=None, description="Secondary tool body or target")
    params: dict[str, Any] = Field(default_factory=dict, description="Operator scalar parameter mapping")
    expect: list[AssertionModel] = Field(default_factory=list, description="Optional extra physical assertions")
    idempotency_key: str = Field(..., description="Client action fingerprint for idempotency deduplication")
    replaces: str | None = Field(default=None, description="Superseded command identifier if replanning")


class CommandResponseModel(BaseModel):
    ok: bool
    version: int
    command_id: str
    body: dict[str, Any] | None = None


class ParamsUpdateModel(BaseModel):
    params: dict[str, Any] = Field(..., description="Updated operator parameter mapping")


class LLMConfigModel(BaseModel):
    base_url: str
    model: str
    api_key: str
    temperature: float = 0.0
    max_tokens: int = 1024
    timeout_s: float = 30.0


class AgentChatModel(BaseModel):
    prompt: str
    selections: list[str] = Field(default_factory=list)
    config: LLMConfigModel


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/agent/test-llm")
async def test_llm_connection(config_payload: LLMConfigModel) -> Any:
    try:
        cfg = LLMConfig(
            base_url=config_payload.base_url,
            model=config_payload.model,
            api_key=config_payload.api_key,
            temperature=config_payload.temperature,
            max_tokens=config_payload.max_tokens,
            timeout_s=config_payload.timeout_s,
        )
        res = ping_llm(cfg)
        return res
    except AgentConfigError as exc:
        return JSONResponse(status_code=200, content={"ok": False, "error": exc.to_diagnostic()})
    except Exception as exc:
        return JSONResponse(status_code=200, content={"ok": False, "error": {"message": str(exc)}})


@router.post("/agent/chat")
async def agent_chat_turn(payload: AgentChatModel) -> Any:
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
        return JSONResponse(status_code=200, content={"ok": False, "error": exc.to_diagnostic()})

    view = build_agent_view(session.design, selections=payload.selections)

    def _in_process_exec(url: str, cmd_dict: dict[str, Any]) -> dict[str, Any]:
        try:
            cmd = Command.from_payload(cmd_dict)
            session.submit(cmd)
            return {"ok": True, "command_id": cmd.command_id}
        except Exception as e:
            diag = getattr(e, "to_diagnostic", lambda: {"message": str(e)})()
            return {"ok": False, "error": diag}

    turn_res = handle_turn(
        prompt=payload.prompt,
        view=view,
        config=cfg,
        command_executor=_in_process_exec,
    )

    query_body = session.query().to_dict() if session.design.geometry is not None else None
    return {
        "ok": turn_res["ok"],
        "explanation": turn_res.get("explanation", ""),
        "version": session.design.version,
        "body": query_body,
        "executed": turn_res.get("executed", []),
        "error": turn_res.get("error"),
    }


@router.post("/command")
async def execute_command(payload: CommandModel) -> dict[str, Any]:
    cmd_dict = payload.model_dump()
    cmd = Command.from_payload(cmd_dict)
    design = session.submit(cmd)
    query_body = session.query().to_dict()
    return {
        "ok": True,
        "version": design.version,
        "command_id": cmd.command_id,
        "body": query_body,
        "journal": _serialize_journal(design.journal),
    }


@router.patch("/command/{command_id}/params")
async def update_command_params(command_id: str, payload: ParamsUpdateModel) -> Any:
    rebuild_res = session.update_params(command_id, payload.params)
    if not rebuild_res.ok:
        return JSONResponse(
            status_code=400,
            content=rebuild_res.to_diagnostic(),
        )

    query_body = session.query().to_dict() if session.design.geometry is not None else None
    rebuilt_downstream = [cid for cid in rebuild_res.succeeded if cid != command_id]
    return {
        "ok": True,
        "version": session.design.version,
        "body": query_body,
        "rebuilt": rebuilt_downstream,
        "journal": _serialize_journal(session.design.journal),
    }


@router.get("/export/step")
async def export_step_endpoint() -> Response:
    if session.design.geometry is None:
        raise HTTPException(status_code=400, detail="No geometry available to export.")
    data = export_step(session.design.geometry)
    return Response(
        content=data,
        media_type="application/step",
        headers={"Content-Disposition": 'attachment; filename="model.step"'},
    )


@router.get("/export/stl")
async def export_stl_endpoint() -> Response:
    if session.design.geometry is None:
        raise HTTPException(status_code=400, detail="No geometry available to export.")
    data = export_stl(session.design.geometry)
    return Response(
        content=data,
        media_type="application/sla",
        headers={"Content-Disposition": 'attachment; filename="model.stl"'},
    )


@router.get("/export/dxf")
async def export_dxf_endpoint(
    plane: str = Query(default="XY"),
    offset: float = Query(default=0.0),
) -> Response:
    if session.design.geometry is None:
        raise HTTPException(status_code=400, detail="No geometry available to export.")
    data = export_dxf(session.design.geometry, plane_name=plane, offset=offset)
    return Response(
        content=data,
        media_type="application/dxf",
        headers={"Content-Disposition": 'attachment; filename="section.dxf"'},
    )


@router.get("/export/cfd-dict")
async def export_cfd_dict_endpoint() -> Response:
    data = export_cfd_dict(session.design.patches)
    return Response(
        content=data,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="cfd_boundaries.json"'},
    )


@router.get("/export/python")
async def export_python_script_endpoint() -> Response:
    script_str = journal_to_python(session.design)
    return Response(
        content=script_str.encode("utf-8"),
        media_type="text/x-python",
        headers={"Content-Disposition": 'attachment; filename="reproduce_model.py"'},
    )


@router.get("/query")
async def get_query() -> dict[str, Any]:
    query_info = session.query()
    body_data = query_info.to_dict() if session.design.geometry is not None else None
    return {
        "ok": True,
        "version": session.design.version,
        "body": body_data,
        "journal": _serialize_journal(session.design.journal),
    }


@router.get("/scene")
async def get_scene() -> dict[str, Any]:
    scene_data = session.scene()
    return {
        "ok": True,
        "version": session.design.version,
        "bodies": scene_data.get("bodies", []),
    }


@router.post("/undo")
async def undo_command() -> dict[str, Any]:
    design = session.undo()
    query_body = session.query().to_dict() if design.geometry is not None else None
    return {
        "ok": True,
        "version": design.version,
        "body": query_body,
        "journal": _serialize_journal(design.journal),
    }


@router.post("/redo")
async def redo_command() -> dict[str, Any]:
    design = session.redo()
    query_body = session.query().to_dict() if design.geometry is not None else None
    return {
        "ok": True,
        "version": design.version,
        "body": query_body,
        "journal": _serialize_journal(design.journal),
    }


@router.post("/reset")
async def reset_design() -> dict[str, Any]:
    session.design = Design.empty()
    return {
        "ok": True,
        "version": session.design.version,
        "body": None,
        "journal": [],
    }
