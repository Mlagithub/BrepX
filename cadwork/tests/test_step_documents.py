"""A flat assembly STEP materializes into part and assembly documents."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from cadwork.design.assembly import Instance, PartRef, Transform, new_assembly_document
from cadwork.design.document import apply_ops
from cadwork.service.service import CADService
from cadwork.service.step_documents import import_step_documents
from cadwork.service.store import Store


class StepDocumentImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.source_store = Store(self.folder.name + "/source")
        self.source = CADService(self.source_store)
        blade = self.source_store.create("blade")
        blade = apply_ops(
            blade,
            [
                {
                    "op": "add",
                    "feature": {
                        "id": "base",
                        "type": "k_box",
                        "params": {"length": 10.0, "width": 6.0, "height": 4.0},
                    },
                }
            ],
        )
        blade = self.source_store.save(blade)
        assembly = new_assembly_document("assembly", seq=1)
        assembly = replace(
            assembly,
            instances=(
                Instance("blade_a", PartRef(blade.id, 1), Transform()),
                Instance(
                    "blade_b",
                    PartRef(blade.id, 1),
                    Transform(translation=(20.0, 0.0, 0.0)),
                ),
            ),
        )
        self.assembly = self.source_store.save_assembly(assembly)
        raw, _, _ = self.source.assembly_export(self.assembly.id)
        self.step_path = Path(self.folder.name) / "assembly.step"
        self.step_path.write_bytes(raw)

        self.target_store = Store(self.folder.name + "/target")
        self.target = CADService(self.target_store)

    def test_import_creates_part_and_assembly_documents(self) -> None:
        result = import_step_documents(self.target, str(self.step_path))
        self.assertEqual(result["part_documents"], 2)
        self.assertEqual(result["assembly_documents"], 1)
        self.assertEqual(result["missing_geometry"], [])
        root = result["root_assembly_id"]
        state = self.target.assembly_state(root)
        self.assertEqual(len(state["assembly"]["instances"]), 2)
        self.assertEqual(sum(row["quantity"] for row in state["build"]["bom"]), 2)
        self.assertTrue(state["build"]["ok"], state["build"]["failures"])
        scene = self.target.assembly_scene(root)
        self.assertEqual(len(scene["definitions"]), 2)
        self.assertGreater(len(next(iter(scene["definitions"].values()))["faces"]), 0)


if __name__ == "__main__":
    unittest.main()
