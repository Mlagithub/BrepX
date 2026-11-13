"""One end-to-end trunk case: intent, plan, build, failure recovery, incremental edits."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from cadwork.design.document import Filter, Ref
from cadwork.design.plan import Expect, PlanNode, plan_node_to_json
from cadwork.service.service import CADService, ServiceError


def _node(node_id: str, title: str, action: str, params: dict[str, Any] | None = None,
          refs: dict[str, Any] | None = None, deps: tuple[str, ...] = ()) -> PlanNode:
    return PlanNode(node_id, "feature", title, action, params or {}, refs or {}, deps)


def _check(node_id: str, title: str, deps: tuple[str, ...]) -> PlanNode:
    return PlanNode(node_id, "check", title, deps=deps,
                    expect=(Expect("solids", "eq", 1), Expect("watertight", "true")))


def _ops(nodes: list[PlanNode]) -> list[dict[str, Any]]:
    return [{"op": "add_node", "node": plan_node_to_json(node)} for node in nodes]


def _run(service: CADService, document_id: str, node_id: str) -> str | None:
    try:
        service.plan_run(document_id, node_id)
        return None
    except ServiceError as exc:
        return f"{exc.code}: {exc.message}"


def _snapshot(service: CADService, document_id: str) -> dict[str, Any]:
    view = service.plan(document_id)
    plan = view["plan"]
    return {
        "version": service.read(document_id).version,
        "plan_revision": plan["revision"],
        "plan_status": plan["status"],
        "nodes": [
            {"id": node["id"], "kind": node["kind"], "status": node["status"],
             "error": node["error"]}
            for node in plan["nodes"]
        ],
    }


def _evidence(service: CADService, document_id: str, folder: Path, turn: int,
              intent: str, feature: str, error: str | None) -> dict[str, Any]:
    snapshot = _snapshot(service, document_id)
    payload: dict[str, Any] = {"turn": turn, "intent": intent, "feature": feature,
                               "error": error, **snapshot}
    png_path = folder / f"turn-{turn}.png"
    step_path = folder / f"turn-{turn}.step"
    try:
        png = service.render(document_id, feature=feature, view="iso")
        png_path.write_bytes(png)
        payload["png"] = png_path.name
    except Exception as exc:
        payload["render_error"] = f"{type(exc).__name__}: {exc}"
    try:
        step, _media = service.export(document_id, "step", feature=feature)
        step_path.write_bytes(step)
        payload["step"] = step_path.name
    except Exception as exc:
        payload["export_error"] = f"{type(exc).__name__}: {exc}"
    if not error:
        report = service.checks(document_id)
        payload["checks_ok"] = report["ok"]
        payload["metrics"] = service.state(document_id).get("metrics")
    (folder / f"turn-{turn}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def run_trunk_case(service: CADService,
                   evidence_root: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    run_id = f"trunk-{uuid.uuid4().hex[:8]}"
    root = Path(evidence_root) if evidence_root else Path(service.store.root) / "trunk-case"
    folder = root / run_id
    folder.mkdir(parents=True, exist_ok=True)
    document = service.store.create("trunk case")
    document_id = document.id
    turns: list[dict[str, Any]] = []

    first = [
        _node("plate", "80x80x20 plate", "k_box",
              {"length": 80.0, "width": 80.0, "height": 20.0}),
        _node("bore", "20 mm through bore", "k_cylinder",
              {"radius": 10.0, "height": 40.0}),
        _node("cut", "cut the bore", "k_cut",
              refs={"target": Ref("plate", "self"),
                    "others": (Ref("bore", "self"),)},
              deps=("plate", "bore")),
        _check("check_cut", "plate with one bore", ("cut",)),
    ]
    service.plan_edit(document_id, _ops(first), goal="plate with a through bore")
    errors = [_run(service, document_id, node.id) for node in first]
    turns.append(_evidence(service, document_id, folder, 1,
                           "做一块 80x80x20 的板，中心开 Ø20 通孔", "cut",
                           next((item for item in errors if item), None)))

    second = [
        _node("boss", "30 mm boss, 10 high", "k_cylinder",
              {"radius": 15.0, "height": 10.0}),
        _node("boss_on_plate", "boss sunk 0.5 mm into the plate", "k_translate",
              {"x": 20.0, "y": 0.0, "z": 14.5},
              {"target": Ref("boss", "self")}, ("boss",)),
        _node("join", "join the boss", "k_fuse",
              refs={"target": Ref("cut", "self"),
                    "others": (Ref("boss_on_plate", "self"),)},
              deps=("cut", "boss_on_plate")),
        _check("check_join", "plate, bore and boss", ("join",)),
    ]
    service.plan_edit(document_id, _ops(second))
    errors = [_run(service, document_id, node.id) for node in second]
    turns.append(_evidence(service, document_id, folder, 2,
                           "在顶面加一个 Ø30、高 10 的凸台", "join",
                           next((item for item in errors if item), None)))

    edge_ref = Ref("join", "edges",
                   (Filter("nearest", args=([20.0, 0.0, 19.5],)),))
    third = [
        _node("fillet", "top edge fillet", "k_fillet",
              {"radius": 20.0},
              {"target": Ref("join", "self"), "edges": edge_ref}, ("join",)),
        _check("check_fillet", "filleted joint", ("fillet",)),
    ]
    service.plan_edit(document_id, _ops(third))
    fillet_error = _run(service, document_id, "fillet")
    failed_version = service.read(document_id).version
    turns.append(_evidence(service, document_id, folder, 3,
                           "给凸台顶边做 20 mm 圆角（预期失败）", "join", fillet_error))
    turns[-1]["version_after_failure"] = failed_version
    _run(service, document_id, "check_fillet")

    service.plan_edit(document_id, [{
        "op": "update_node",
        "node": {"id": "fillet", "params": {"radius": 0.5}},
    }])
    fix_error = _run(service, document_id, "fillet")
    check_error = _run(service, document_id, "check_fillet")
    turns.append(_evidence(service, document_id, folder, 4,
                           "圆角太大，改成 0.5 mm", "fillet", fix_error or check_error))

    service.plan_edit(document_id, [{
        "op": "update_node",
        "node": {"id": "bore", "params": {"radius": 6.0, "height": 40.0}},
    }])
    redo = ["bore", "cut", "join", "fillet", "check_cut", "check_join", "check_fillet"]
    errors = [_run(service, document_id, node_id) for node_id in redo]
    turns.append(_evidence(service, document_id, folder, 5,
                           "中心孔改成 Ø12，增量重算", "fillet",
                           next((item for item in errors if item), None)))

    summary = {
        "run_id": run_id,
        "document_id": document_id,
        "folder": str(folder),
        "turns": turns,
        "final_version": service.read(document_id).version,
        "final_plan": service.plan(document_id)["plan"],
        "errors": [turn["error"] for turn in turns if turn.get("error")],
    }
    (folder / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
