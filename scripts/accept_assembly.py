"""End-to-end assembly acceptance: plan, build, edit, re-pin, export, import."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import smlibpy as s

from cadwork.design.assembly import PartRef, Transform
from cadwork.design.assembly_plan import (
    AssemblyPlan,
    Pattern,
    PlanInstance,
    compile_assembly_plan,
)
from cadwork.design.document import apply_ops
from cadwork.design.step_import import parse_step_structure
from cadwork.service.service import CADService
from cadwork.service.store import Store


def _part(store: Store, name: str, height: float):
    document = store.create(name)
    document = apply_ops(
        document,
        [
            {
                "op": "add",
                "feature": {
                    "id": "base",
                    "type": "k_box",
                    "params": {"length": 10.0, "width": 6.0, "height": height},
                },
            }
        ],
    )
    return store.save(document)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--step", default=None, help="optional turbofan STEP for structure assertions"
    )
    parser.add_argument(
        "--import-step",
        dest="import_step",
        default=None,
        help="optional STEP materialized into part/assembly documents",
    )
    args = parser.parse_args()
    evidence: dict[str, object] = {}

    with tempfile.TemporaryDirectory() as folder:
        store = Store(folder)
        service = CADService(store)
        blade = _part(store, "blade", 4.0)
        disk = _part(store, "disk", 6.0)

        plan = AssemblyPlan(
            "assembly_accept",
            "assembly_accept",
            (
                PlanInstance("disk", PartRef(disk.id, 1), Transform()),
                PlanInstance(
                    "blade",
                    PartRef(blade.id, 1),
                    placement=Transform(translation=(0.0, 0.0, 3.0)),
                    pattern=Pattern("polar", 6, radius=30.0),
                ),
            ),
        )
        assembly = compile_assembly_plan(plan)
        store.save_assembly(assembly)
        state = service.assembly_state(assembly.id)
        assert len(state["assembly"]["instances"]) == 7, state
        assert sum(entry["quantity"] for entry in state["build"]["bom"]) == 7, state

        edited = service.edit_assembly(
            assembly.id,
            1,
            [
                {
                    "op": "transform",
                    "id": "blade_0",
                    "placement": {
                        "rotation": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                        "translation": [100.0, 0.0, 0.0],
                    },
                },
                {
                    "op": "override",
                    "id": "blade_0",
                    "overrides": {"length": 12.0},
                },
            ],
        )
        assert edited["assembly"]["version"] == 2, edited

        blade_v2 = replace(blade, version=2)
        store.save(blade_v2)
        status = service.assembly_references(assembly.id)
        assert status["outdated"], status
        updated = service.update_assembly_references(assembly.id, 2)
        assert updated["assembly"]["version"] == 3, updated
        assert not service.assembly_references(assembly.id)["outdated"]

        raw, media, sidecar = service.assembly_export(assembly.id)
        assert media == "application/step"
        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as handle:
            handle.write(raw)
            step_path = Path(handle.name)
        try:
            bodies = list(s.import_step(str(step_path)))
            assert len(bodies) == 7, len(bodies)
        finally:
            step_path.unlink(missing_ok=True)
        assert sum(entry["quantity"] for entry in sidecar["bom"]) == 7, sidecar

        evidence["assembly"] = {
            "instances": len(state["assembly"]["instances"]),
            "bom_quantity": sum(entry["quantity"] for entry in state["build"]["bom"]),
            "edited_version": edited["assembly"]["version"],
            "updated_version": updated["assembly"]["version"],
            "step_bodies": len(bodies),
        }

    if args.step:
        graph = parse_step_structure(args.step)
        assert graph.assembly_count == 12, graph.assembly_count
        assert graph.part_count == 183, graph.part_count
        assert graph.leaf_instance_count == 1930, graph.leaf_instance_count
        assert graph.depth == 3, graph.depth
        evidence["turbofan"] = graph.summary()

    if args.import_step:
        from cadwork.service.step_documents import import_step_documents

        with tempfile.TemporaryDirectory() as imported_folder:
            imported_store = Store(imported_folder)
            imported_service = CADService(imported_store)
            imported = import_step_documents(imported_service, args.import_step)
            assert imported["part_documents"] == 183, imported["part_documents"]
            assert imported["assembly_documents"] == 12, imported["assembly_documents"]
            root = imported["root_assembly_id"]
            state = imported_service.assembly_state(root)
            assert len(state["assembly"]["instances"]) >= 1, state
            assert state["build"]["ok"], state["build"]["failures"][:3]
            assert sum(row["quantity"] for row in state["build"]["bom"]) == 1930
            evidence["imported"] = {
                "root_assembly_id": root,
                "part_documents": imported["part_documents"],
                "assembly_documents": imported["assembly_documents"],
                "leaf_instances": sum(row["quantity"] for row in state["build"]["bom"]),
                "missing_geometry": imported["missing_geometry"],
                "build_ok": state["build"]["ok"],
            }

    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
