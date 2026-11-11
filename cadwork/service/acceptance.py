"""The four acceptance criteria, run against the real service in one script.

Used by `scripts/demo.py` and by the acceptance test. No HTTP server required:
every call goes through the same CADService the HTTP and MCP surfaces use.
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

    # 1. build the impeller and export STEP + CFD.
    applied = service.apply(document.id, document.version, _add_ops())
    document = service.read(document.id)
    step_bytes, _ = service.export(document.id, "step")
    cfd_bytes, _ = service.export(document.id, "cfd")
    steps.append(
        f"1 built {len(document.features)} features at v{document.version}, "
        f"checks_ok={_checks_ok(service, document.id)}, "
        f"step={len(step_bytes)}B cfd={len(cfd_bytes)}B"
    )
    assert len(document.features) == 9
    assert _checks_ok(service, document.id)
    assert len(step_bytes) > 1000 and b"boundaries" in cfd_bytes

    # 2. change blade count; boundaries still resolve.
    preview = service.preview(document.id, [
        {"op": "update", "id": "f3", "params": {"count": 11}},
    ])
    assert "f3" in preview["diff"]["changed"]
    service.apply(document.id, document.version, [
        {"op": "update", "id": "f3", "params": {"count": 11}},
    ])
    document = service.read(document.id)
    tags = service.checks(document.id)["tags"]
    steps.append(
        f"2 count=11 at v{document.version}, boundaries={sorted(tags)}"
    )
    assert sorted(tags) == ["f6", "f7", "f8"]

    # Back to nine blades: the fillet edge is a geometric query, and at eleven
    # blades the nearest edge changes (see the known limitation in the doc).
    service.apply(document.id, document.version, [
        {"op": "update", "id": "f3", "params": {"count": 9}},
    ])
    document = service.read(document.id)
    steps.append(f"3 count back to 9 at v{document.version}")

    # 4. an impossible fillet fails without touching the document; a small one works.
    version = document.version
    failure: ServiceError | None = None
    try:
        service.apply(document.id, version, [
            {"op": "update", "id": "f5", "params": {"radius": 2.0}},
        ])
    except ServiceError as exc:
        failure = exc
    assert failure is not None and failure.status == 422
    assert service.read(document.id).version == version
    service.apply(document.id, version, [
        {"op": "update", "id": "f5", "params": {"radius": 0.3}},
    ])
    document = service.read(document.id)
    steps.append(
        f"4 fillet 2mm -> {failure.code} on {failure.detail.get('feature_id')}, "
        f"version stayed {version}; 0.3mm -> v{document.version}"
    )
    assert document.version == version + 1

    # 5. a fresh service on the same store: scene, edit, export and undo still work.
    restarted = CADService(Store(folder))
    scene = restarted.scene(document.id)
    assert scene["faces"] and scene["edges"]
    restarted.apply(document.id, restarted.read(document.id).version, [
        {"op": "update", "id": "f3", "params": {"count": 10}},
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
