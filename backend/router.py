"""FastAPI REST API Router for BrepX."""

from __future__ import annotations

import json
import sys
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

import smlibpy
from .agent_engine import embodied_agent
from .operators import build_operator_code
from .semantic_patches import semantic_patch_manager
from .workspace import workspace_session

router = APIRouter(prefix="/api")


class OperatorExecuteRequest(BaseModel):
    operator: str
    params: dict[str, Any] = Field(default_factory=dict)
    selections: list[str] = Field(default_factory=list)
    replace_all: bool | None = None


class AdjustLastRequest(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)


class ScriptRunRequest(BaseModel):
    script: str
    label: str = "自定义 Python 脚本"
    replace_all: bool = True


class AgentChatRequest(BaseModel):
    prompt: str
    selections: list[str] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class SemanticPatchAssignRequest(BaseModel):
    face_indices: list[int]
    semantic_type: str
    name: str | None = None


def _ensure_initial_model() -> None:
    if not workspace_session.history:
        code, lbl, _ = build_operator_code("flange_plate", {"length": 100, "width": 80, "thickness": 12, "fillet_r": 10, "hole_r": 15})
        workspace_session.execute_step(code, label=lbl, operator_id="flange_plate", params={"length": 100, "width": 80, "thickness": 12, "fillet_r": 10, "hole_r": 15}, replace_all=True)


@router.get("/info")
def api_info() -> dict[str, Any]:
    return {
        "status": "ready",
        "product": "BrepX",
        "smlibpy_version": getattr(smlibpy, "__version__", "0.4.0"),
        "kernel": "SMLib NURBS B-Rep Kernel",
        "platform": sys.platform,
    }


@router.get("/workspace/state")
def api_workspace_state() -> dict[str, Any]:
    _ensure_initial_model()
    state = workspace_session.get_state()
    state["patches"] = semantic_patch_manager.get_all_patches()
    return state


@router.post("/workspace/clear")
def api_workspace_clear() -> dict[str, Any]:
    workspace_session.clear()
    semantic_patch_manager.clear()
    _ensure_initial_model()
    state = workspace_session.get_state()
    state["patches"] = []
    return state


@router.post("/workspace/execute_operator")
def api_execute_operator(req: OperatorExecuteRequest) -> dict[str, Any]:
    try:
        has_part = workspace_session.primary_part() is not None
        code, label, default_replace = build_operator_code(
            req.operator,
            req.params,
            req.selections,
            has_existing_part=has_part,
        )
        replace_flag = req.replace_all if req.replace_all is not None else default_replace
        if replace_flag:
            semantic_patch_manager.clear()

        state = workspace_session.execute_step(
            code=code,
            label=label,
            operator_id=req.operator,
            params=req.params,
            selections=req.selections,
            replace_all=replace_flag,
        )
        semantic_patch_manager.rebind_to_part(workspace_session.primary_part())
        state["patches"] = semantic_patch_manager.get_all_patches()
        state["explanation"] = f"已执行【{label}】"
        return state
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workspace/adjust_last")
def api_adjust_last(req: AdjustLastRequest) -> dict[str, Any]:
    if not workspace_session.history:
        raise HTTPException(status_code=400, detail="没有可微调的上一步操作")
    last = workspace_session.history[-1]
    if not last.operator_id:
        raise HTTPException(status_code=400, detail="上一步为自由脚本，请直接在脚本编辑器中修改")

    try:
        merged_params = {**last.params, **req.params}
        has_prev = len(workspace_session.history) > 1
        new_code, new_label, _ = build_operator_code(
            last.operator_id,
            merged_params,
            last.selections,
            has_existing_part=has_prev,
        )
        state = workspace_session.adjust_last_step(new_code, merged_params, label=new_label)
        semantic_patch_manager.rebind_to_part(workspace_session.primary_part())
        state["patches"] = semantic_patch_manager.get_all_patches()
        state["explanation"] = f"已实时微调【{new_label}】"
        return state
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workspace/run_script")
def api_run_script(req: ScriptRunRequest) -> dict[str, Any]:
    try:
        state = workspace_session.execute_step(
            code=req.script,
            label=req.label,
            operator_id=None,
            replace_all=req.replace_all,
        )
        semantic_patch_manager.rebind_to_part(workspace_session.primary_part())
        state["patches"] = semantic_patch_manager.get_all_patches()
        return state
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workspace/undo")
def api_workspace_undo() -> dict[str, Any]:
    try:
        state = workspace_session.undo()
        semantic_patch_manager.rebind_to_part(workspace_session.primary_part())
        state["patches"] = semantic_patch_manager.get_all_patches()
        return state
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workspace/redo")
def api_workspace_redo() -> dict[str, Any]:
    try:
        state = workspace_session.redo()
        semantic_patch_manager.rebind_to_part(workspace_session.primary_part())
        state["patches"] = semantic_patch_manager.get_all_patches()
        return state
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/agent/chat")
def api_agent_chat(req: AgentChatRequest) -> dict[str, Any]:
    res = embodied_agent.chat(
        prompt=req.prompt,
        selections=req.selections,
        history=req.history,
        config=req.config,
        ws=workspace_session,
    )
    semantic_patch_manager.rebind_to_part(workspace_session.primary_part())
    if "state" in res and isinstance(res["state"], dict):
        res["state"]["patches"] = semantic_patch_manager.get_all_patches()
    return res


@router.post("/agent/test_llm")
def api_agent_test_llm(req: dict[str, Any]) -> dict[str, Any]:
    return embodied_agent.test_connection(req)


@router.post("/semantic/patch")
def api_set_semantic_patch(req: SemanticPatchAssignRequest) -> dict[str, Any]:
    try:
        patch = semantic_patch_manager.set_patch(
            face_indices=req.face_indices,
            semantic_type=req.semantic_type,
            name=req.name,
            part=workspace_session.primary_part(),
        )
        return {"ok": True, "patch": patch, "patches": semantic_patch_manager.get_all_patches()}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/semantic/patches")
def api_get_semantic_patches() -> dict[str, Any]:
    return {"ok": True, "patches": semantic_patch_manager.get_all_patches()}


@router.delete("/semantic/patch/{patch_id}")
def api_delete_semantic_patch(patch_id: str) -> dict[str, Any]:
    ok = semantic_patch_manager.remove_patch(patch_id)
    return {"ok": ok, "patches": semantic_patch_manager.get_all_patches()}


@router.delete("/semantic/patches")
def api_clear_all_semantic_patches() -> dict[str, Any]:
    semantic_patch_manager.clear()
    return {"ok": True, "patches": []}


@router.get("/export/cfd_meta")
def api_export_cfd_meta() -> Response:
    meta = semantic_patch_manager.export_cfd_metadata()
    return Response(
        content=json.dumps(meta, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="cfd_boundaries.json"'},
    )


@router.get("/export/{fmt}")
def api_export_file(fmt: str) -> Response:
    _ensure_initial_model()
    fmt = fmt.lower()
    try:
        if fmt in ("step", "stp") and semantic_patch_manager.patches:
            data = semantic_patch_manager.export_step_with_semantics(workspace_session.primary_part())
            return Response(
                content=data,
                media_type="application/step",
                headers={"Content-Disposition": 'attachment; filename="smlib_cfd_model.step"'},
            )
        data, mime, filename = workspace_session.export_bytes(fmt)
        return Response(
            content=data,
            media_type=mime,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
