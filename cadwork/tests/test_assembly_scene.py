"""Assembly scene shares one definition mesh across placed instances."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace

from cadwork.design.assembly import Instance, PartRef, Transform, new_assembly_document
from cadwork.design.document import ParameterSpec, apply_ops
from cadwork.service.service import CADService
from cadwork.service.store import Store


class AssemblySceneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.store = Store(self.folder.name)
        part = self.store.create("blade")
        part = apply_ops(
            part,
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
        self.part = self.store.save(part)
        assembly = new_assembly_document("assembly", seq=1)
        assembly = replace(
            assembly,
            instances=(
                Instance("blade_a", PartRef(self.part.id, 1), Transform()),
                Instance(
                    "blade_b",
                    PartRef(self.part.id, 1),
                    Transform(translation=(20.0, 0.0, 0.0)),
                ),
            ),
        )
        self.assembly = self.store.save_assembly(assembly)
        self.service = CADService(self.store)

    def tearDown(self) -> None:
        self.folder.cleanup()

    def test_scene_has_one_definition_and_two_instances(self) -> None:
        scene = self.service.assembly_scene(self.assembly.id)
        self.assertEqual(len(scene["definitions"]), 1)
        self.assertEqual(len(scene["instances"]), 2)
        self.assertEqual(
            [item["path"] for item in scene["instances"]], ["blade_a", "blade_b"]
        )
        self.assertEqual(
            [item["placement"]["translation"] for item in scene["instances"]],
            [[0.0, 0.0, 0.0], [20.0, 0.0, 0.0]],
        )
        key = next(iter(scene["definitions"]))
        self.assertEqual(key, f"{self.part.id}@1#default#{{}}")
        self.assertGreater(len(scene["definitions"][key]["faces"]), 0)
        self.assertEqual(scene["bom"][0]["quantity"], 2)
        self.assertEqual(scene["bbox"]["min"], [-5.0, -3.0, -2.0])
        self.assertEqual(scene["bbox"]["max"], [25.0, 3.0, 2.0])

    def test_scene_reports_failure_without_raising(self) -> None:
        assembly = new_assembly_document("broken", seq=2)
        assembly = replace(
            assembly,
            instances=(Instance("ghost", PartRef("part_missing", 1), Transform()),),
        )
        # Store validation rejects a bad pin on save; build the document directly
        # to exercise the scene's failure projection.
        from cadwork.design.assembly_build import build_assembly
        from cadwork.service.scene import build_assembly_scene

        result = build_assembly(assembly, self.store, self.service.cache)
        scene = build_assembly_scene(result, self.store, self.service.cache)
        self.assertEqual(scene["metrics"]["failures"], 1)
        self.assertIn(
            scene["instances"][0]["error"]["code"], {"NOT_FOUND", "VERSION_NOT_FOUND"}
        )
        self.assertEqual(scene["definitions"], {})

    def test_overrides_use_separate_definition_meshes(self) -> None:
        part = replace(
            self.part,
            version=2,
            parameters=(
                ParameterSpec(
                    "length", "base", "length", "float", 10.0, "mm", 5.0, 50.0
                ),
            ),
        )
        self.store.save(part)
        assembly = new_assembly_document("overrides", seq=3)
        assembly = replace(
            assembly,
            instances=(
                Instance(
                    "short",
                    PartRef(part.id, 2),
                    Transform(),
                    overrides={"length": 20.0},
                ),
                Instance(
                    "long",
                    PartRef(part.id, 2),
                    Transform(translation=(20.0, 0.0, 0.0)),
                    overrides={"length": 40.0},
                ),
            ),
        )
        self.store.save_assembly(assembly)
        scene = self.service.assembly_scene(assembly.id)
        self.assertEqual(len(scene["definitions"]), 2)
        volumes = sorted(
            item["metrics"]["volume"] for item in scene["definitions"].values()
        )
        self.assertAlmostEqual(volumes[0], 20.0 * 6.0 * 4.0, delta=1e-6)
        self.assertAlmostEqual(volumes[1], 40.0 * 6.0 * 4.0, delta=1e-6)


if __name__ == "__main__":
    unittest.main()
