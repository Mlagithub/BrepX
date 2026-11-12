"""Run the end-to-end acceptance checks against the real service in one script.

No HTTP server required: every call goes through the same CADService the HTTP and
MCP surfaces use, so these checks cover the same build, export and undo paths.
"""

from __future__ import annotations

import tempfile
from typing import Any

from cadwork.design.document import feature_to_json
from cadwork.samples.impeller import impeller_document

from .service import CADService, ServiceError
from .store import Store


def _add_ops(extra: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    features = impeller_document(count=9).features
    ops = [{"op": "add", "feature": feature_to_json(feature)} for feature in features]
    if extra:
        ops.append(extra)
    return ops


def _checks_ok(service: CADService, document_id: str) -> bool:
    report = service.checks(document_id)
    return all(check["ok"] for item in report["features"] for check in item["checks"])


def run_acceptance(folder: str | None = None) -> dict[str, Any]:
    folder = folder or tempfile.mkdtemp(prefix="cadwork-accept-")
    store = Store(folder)
    service = CADService(store)
    document = store.create("acceptance")
    steps: list[str] = []
    report: dict[str, Any] = {"folder": folder, "steps": steps, "ok": False}

    # A complete impeller must compile, pass every check and export STEP and CFD bytes.
    applied = service.apply(document.id, document.version, _add_ops())
    document = service.read(document.id)
    step_bytes, _ = service.export(document.id, "step")
    cfd_bytes, _ = service.export(document.id, "cfd")
    steps.append(
        f"1 built {len(document.features)} features at v{document.version}, "
        f"checks_ok={_checks_ok(service, document.id)}, "
        f"step={len(step_bytes)}B cfd={len(cfd_bytes)}B"
    )
    assert len(document.features) == 36
    assert _checks_ok(service, document.id)
    assert len(step_bytes) > 1000 and b"boundaries" in cfd_bytes

    # Changing the pattern count must still resolve the cavity boundaries by name.
    preview = service.preview(document.id, [
        {"op": "update", "id": "b_pattern", "params": {"count": 11}},
    ])
    assert "b_pattern" in preview["diff"]["changed"]
    service.apply(document.id, document.version, [
        {"op": "update", "id": "b_pattern", "params": {"count": 11}},
    ])
    document = service.read(document.id)
    tags = service.checks(document.id)["tags"]
    steps.append(
        f"2 count=11 at v{document.version}, boundaries={sorted(tags)}"
    )
    assert sorted(tags) == ["t_in", "t_out", "t_wall"]

    # Back to nine blades proves the fillet edge is found by geometric query, not by a remembered index.
    service.apply(document.id, document.version, [
        {"op": "update", "id": "b_pattern", "params": {"count": 9}},
    ])
    document = service.read(document.id)
    steps.append(f"3 count back to 9 at v{document.version}")

    # An impossible fillet must fail without touching the document; a legal radius must then succeed.
    version = document.version
    failure: ServiceError | None = None
    try:
        service.apply(document.id, version, [
            {"op": "update", "id": "b_fillet", "params": {"radius": 3.0}},
        ])
    except ServiceError as exc:
        failure = exc
    assert failure is not None and failure.status == 422
    assert service.read(document.id).version == version
    service.apply(document.id, version, [
        {"op": "update", "id": "b_fillet", "params": {"radius": 0.3}},
    ])
    document = service.read(document.id)
    steps.append(
        f"4 fillet 3mm -> {failure.code} on {failure.detail.get('feature_id')}, "
        f"version stayed {version}; 0.3mm -> v{document.version}"
    )
    assert document.version == version + 1

    # A fresh service over the same store must reproduce scene, edit, export and undo from persisted state.
    restarted = CADService(Store(folder))
    scene = restarted.scene(document.id)
    assert scene["faces"] and scene["edges"]
    restarted.apply(document.id, restarted.read(document.id).version, [
        {"op": "update", "id": "b_pattern", "params": {"count": 10}},
    ])
    exported, _ = restarted.export(document.id, "step")
    edited_version = restarted.read(document.id).version
    undone = restarted.undo(document.id)
    steps.append(
        f"5 restarted service: scene={len(scene['faces'])} faces, "
        f"edit -> v{edited_version}, export={len(exported)}B, "
        f"undo -> v{undone['document']['version']}"
    )
    assert len(exported) > 1000
    assert undone["document"]["version"] == edited_version + 1
    assert len(undone["document"]["features"]) == len(document.features)

    report["ok"] = True
    report["final_version"] = undone["document"]["version"]
    return report
