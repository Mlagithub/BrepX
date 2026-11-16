"""Anchor a spiral volute on a picked face of a built impeller and prove the boolean.

    python scripts/accept_face_volute.py

The impeller is converted to plan nodes, then four nodes are appended:

* a spiral path;
* ``place_on`` that puts the path on the impeller's flat back face
  (``nearest([44, 0, -4])`` selects the face, no index);
* a circular section and a growing ``sweep``;
* a ``k_fuse`` that joins the volute to the impeller.

A final check requires one watertight solid.  The fused body is exported.
"""

from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cadwork.design.document import Filter, Ref
from cadwork.design.plan import Expect, PlanNode, plan_node_to_json
from cadwork.samples.impeller import impeller_document
from cadwork.service.service import CADService, ServiceError
from cadwork.service.store import Store

FACE_POINT = [44.0, 0.0, -4.0]


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
    folder = tempfile.mkdtemp(prefix="cadwork-face-volute-")
    print(f"folder {folder}")
    store = Store(folder)
    service = CADService(store)
    document = store.create("face-anchored volute")

    base = impeller_document(count=9)
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
        for feature in base.features
    ]
    nodes.extend(
        [
            PlanNode(
                id="volute_spiral",
                kind="feature",
                title="volute path",
                action="k_spiral",
                params={
                    "start_radius": 10.0,
                    "end_radius": 25.0,
                    "turns": 2.0,
                    "plane": "XY",
                    "clockwise": False,
                },
            ),
            PlanNode(
                id="volute_on_face",
                kind="feature",
                title="place path on the back face",
                action="place_on",
                refs={
                    "shape": Ref("volute_spiral", "self"),
                    "face": Ref(
                        "b_fillet",
                        "faces",
                        (Filter("planar"), Filter("nearest", args=(FACE_POINT,))),
                    ),
                },
                deps=("volute_spiral", "b_fillet"),
            ),
            PlanNode(
                id="volute_section",
                kind="feature",
                title="circular section",
                action="k_circle",
                params={"radius": 2.0},
            ),
            PlanNode(
                id="volute_sweep",
                kind="feature",
                title="growing sweep",
                action="k_sweep",
                params={
                    "orient": True,
                    "translational": False,
                    "twist": 0.0,
                    "scale_start": 0.5,
                    "scale_end": 1.2,
                },
                refs={
                    "profile": Ref("volute_section", "self"),
                    "path": Ref("volute_on_face", "self"),
                },
                deps=("volute_section", "volute_on_face"),
            ),
            PlanNode(
                id="volute_fuse",
                kind="feature",
                title="fuse with the impeller",
                action="k_fuse",
                refs={
                    "target": Ref("b_fillet", "self"),
                    "others": (Ref("volute_sweep", "self"),),
                },
                deps=("b_fillet", "volute_sweep"),
            ),
            PlanNode(
                id="volute_check",
                kind="check",
                title="one watertight body",
                deps=("volute_fuse",),
                expect=(
                    Expect("solids", "eq", 1),
                    Expect("watertight", "true"),
                    Expect("volume", "ge", 40000.0),
                ),
            ),
        ]
    )

    service.plan_edit(
        document.id,
        [{"op": "add_node", "node": plan_node_to_json(node)} for node in nodes],
        goal="impeller with a face-anchored volute",
    )
    report = service.plan_compile(document.id)
    if report.get("issues"):
        print("compile issues", report["issues"])
        return 1
    print(f"compile ok: {report.get('coverage')}")

    for node in nodes:
        try:
            service.plan_run(document.id, node.id)
        except ServiceError as exc:
            print(f"FAIL node {node.id}: {exc.code}: {exc.message}")
            return 1

    current = store.get(document.id)
    print(f"all nodes done at v{current.version}")
    payload, media = service.export(document.id, "step", feature="volute_fuse")
    target = os.path.join(folder, "impeller-volute.step")
    with open(target, "wb") as handle:
        handle.write(payload)
    print(f"wrote {target} ({len(payload)} bytes, {media})")
    return 0 if len(payload) > 1000 else 1


if __name__ == "__main__":
    raise SystemExit(main())
