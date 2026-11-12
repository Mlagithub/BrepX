"""Accept the plan pipeline end to end: document -> plan -> compile -> run -> checks -> STEP.

    python scripts/accept_plan.py

It converts the impeller document into plan nodes, runs every node through
CADService.plan_run, adds a final check node, proves failure isolation on the
fillet, then exports the checked body.
"""

from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cadwork.design.plan import Expect, PlanNode, plan_node_to_json  # noqa: E402
from cadwork.samples.impeller import impeller_document  # noqa: E402
from cadwork.service.service import CADService, ServiceError  # noqa: E402
from cadwork.service.store import Store  # noqa: E402

from cadwork.design.document import Ref  # noqa: E402


def _deps(feature) -> tuple[str, ...]:
    found: list[str] = []
    for value in feature.refs.values():
        items = value if isinstance(value, (list, tuple)) else (value,)
        for ref in items:
            if not isinstance(ref, Ref):
                continue
            for source in (ref.source, *ref.since, *ref.extra):
                if source not in found:
                    found.append(source)
    return tuple(found)


def main() -> int:
    folder = tempfile.mkdtemp(prefix="cadwork-accept-plan-")
    print(f"folder {folder}")
    store = Store(folder)
    service = CADService(store)
    document = store.create("plan-acceptance")

    source = impeller_document(count=9)
    nodes = [
        PlanNode(
            id=feature.id,
            kind="feature",
            title=feature.id,
            action=feature.type,
            params=dict(feature.params),
            refs=dict(feature.refs),
            deps=_deps(feature),
        )
        for feature in source.features
    ]
    nodes.append(PlanNode(
        id="fluid_check", kind="check", title="fluid is one closed solid",
        deps=("fluid_cavity",),
        expect=(
            Expect("solids", "eq", 1),
            Expect("watertight", "true"),
        ),
    ))
    plan = service.plan_edit(
        document.id,
        [{"op": "add_node", "node": plan_node_to_json(node)} for node in nodes],
        goal="impeller with a fluid domain",
    )
    print(f"plan nodes {len(plan['plan']['nodes'])} revision {plan['plan']['revision']}")

    issues = service.plan_compile(document.id)
    if issues.get("issues"):
        print("compile issues", issues["issues"])
        return 1
    print(f"compile ok: {issues.get('coverage')}")

    order = [node.id for node in nodes]
    for node_id in order:
        try:
            service.plan_run(document.id, node_id)
        except ServiceError as exc:
            print(f"FAIL node {node_id}: {exc.code}: {exc.message}")
            return 1
    current = store.get(document.id)
    print(f"all nodes done at v{current.version}")

    # Failure isolation: a 3 mm fillet must fail without writing a version.
    version = current.version
    service.plan_edit(document.id, [{
        "op": "update_node",
        "node": {"id": "b_fillet", "params": {"radius": 3.0}},
    }])
    view = service.plan(document.id)
    downstream = {node["id"]: node["status"] for node in view["plan"]["nodes"]}
    if downstream.get("fluid_cavity") != "pending":
        print(f"FAIL: downstream fluid_cavity was not invalidated: {downstream.get('fluid_cavity')}")
        return 1
    try:
        service.plan_run(document.id, "fluid_check")
        print("UNEXPECTED: the check ran while its dependency was stale")
        return 1
    except ServiceError as exc:
        if exc.code != "NODE_NOT_READY":
            print(f"FAIL: expected NODE_NOT_READY, got {exc.code}")
            return 1
        print(f"stale check blocked: {exc.code}")
    try:
        service.plan_run(document.id, "b_fillet")
        print("UNEXPECTED: the 3 mm fillet succeeded")
        return 1
    except ServiceError as exc:
        if store.get(document.id).version != version:
            print(f"FAIL: version changed after {exc.code}")
            return 1
        print(f"failure isolated: {exc.code}; document still v{version}")
    service.plan_edit(document.id, [{
        "op": "update_node",
        "node": {"id": "b_fillet", "params": {"radius": 0.3}},
    }])
    service.plan_run(document.id, "b_fillet")
    service.plan_run(document.id, "fluid_cavity")
    service.plan_run(document.id, "fluid_check")
    final = store.get(document.id)
    print(f"recovered at v{final.version}; timeline {len(service.timeline(document.id))}")

    payload, media = service.export(document.id, "step", feature="b_fillet")
    target = os.path.join(folder, "impeller.step")
    with open(target, "wb") as handle:
        handle.write(payload)
    print(f"wrote {target} ({len(payload)} bytes, {media})")
    return 0 if len(payload) > 1000 else 1


if __name__ == "__main__":
    raise SystemExit(main())
