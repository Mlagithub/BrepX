"""Assembly build tests: pins, placements, BOM, and per-instance isolation."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace

from cadwork.design.assembly import (
    AssemblyRef,
    Instance,
    PartRef,
    Transform,
    new_assembly_document,
)
from cadwork.design.assembly_build import build_assembly
from cadwork.design.document import ParameterSpec, apply_ops
from cadwork.service.service import CADService, ServiceError
from cadwork.service.store import Store


class _MemorySource:
    """Read-only source for assemblies that never enter a store."""

    def __init__(self, assemblies: dict[tuple[str, int], object]) -> None:
        self.assemblies = assemblies

    def get_version(self, document_id: str, version: int) -> object:
        raise AssertionError("assembly cycle test has no part pins")

    def get_assembly_version(self, assembly_id: str, version: int) -> object:
        return self.assemblies[(assembly_id, version)]


class AssemblyBuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)
        self.service = CADService(self.store)

        part = self.store.create("blade")
        part = apply_ops(
            part,
            [
                {
                    "op": "add",
                    "feature": {
                        "id": "base",
                        "type": "k_box",
                        "params": {"length": 10.0, "width": 20.0, "height": 30.0},
                    },
                }
            ],
        )
        self.store.save(part)
        part = replace(
            part,
            version=2,
            configurations={"long": {"base": {"length": 20.0}}},
            parameters=(
                ParameterSpec(
                    "length", "base", "length", "float", 10.0, "mm", 5.0, 50.0
                ),
            ),
        )
        self.part = self.store.save(part)

        child = new_assembly_document("group", document_id="a_group", seq=2)
        child = replace(
            child,
            instances=(
                Instance(
                    "blade_c",
                    PartRef(self.part.id, 2, "long"),
                    Transform(translation=(0.0, 100.0, 0.0)),
                ),
            ),
        )
        self.child = self.store.save_assembly(child)

        root = new_assembly_document("drive", document_id="a_drive", seq=3)
        root = replace(
            root,
            instances=(
                Instance(
                    "blade_a",
                    PartRef(self.part.id, 2),
                    Transform(translation=(100.0, 0.0, 0.0)),
                ),
                Instance(
                    "blade_b",
                    PartRef(self.part.id, 2, "long"),
                    Transform(translation=(-100.0, 0.0, 0.0)),
                ),
                Instance(
                    "group_1",
                    AssemblyRef(self.child.id, 1),
                    Transform(translation=(0.0, 0.0, 200.0)),
                ),
            ),
        )
        self.root = self.store.save_assembly(root)

    def _assert_bbox(self, result, minimum, maximum) -> None:
        self.assertIsNotNone(result.bbox_min)
        self.assertIsNotNone(result.bbox_max)
        for actual, expected in zip(result.bbox_min, minimum):
            self.assertAlmostEqual(actual, expected, places=5)
        for actual, expected in zip(result.bbox_max, maximum):
            self.assertAlmostEqual(actual, expected, places=5)

    def test_service_build_resolves_the_requested_version(self) -> None:
        result = self.service.build_assembly(self.root.id)
        self.assertTrue(result.ok)
        self.assertEqual(result.document_id, "a_drive")
        self.assertEqual(result.version, 1)
        self.assertEqual(len(result.instances), 4)

        pinned = self.service.build_assembly(self.root.id, 1)
        self.assertEqual(
            [item.path for item in pinned.instances],
            [item.path for item in result.instances],
        )

    def test_instance_paths_and_pins(self) -> None:
        result = build_assembly(self.root, self.store)
        self.assertEqual(
            [item.path for item in result.instances],
            ["blade_a", "blade_b", "group_1", "group_1/blade_c"],
        )
        by_path = {item.path: item for item in result.instances}
        self.assertEqual(by_path["blade_a"].definition_kind, "part")
        self.assertEqual(by_path["blade_a"].configuration, "default")
        self.assertEqual(by_path["blade_b"].configuration, "long")
        self.assertEqual(by_path["group_1"].definition_kind, "assembly")
        self.assertIsNone(by_path["group_1"].configuration)
        self.assertEqual(by_path["group_1"].version, 1)
        self.assertEqual(by_path["group_1/blade_c"].definition_id, self.part.id)
        self.assertEqual(by_path["group_1/blade_c"].version, 2)
        self.assertIsNotNone(by_path["blade_a"].part)
        self.assertIsNone(by_path["group_1"].part)

    def test_placements_compose_through_a_sub_assembly(self) -> None:
        result = build_assembly(self.root, self.store)
        by_path = {item.path: item for item in result.instances}
        self.assertEqual(
            by_path["blade_a"].placement, Transform(translation=(100.0, 0.0, 0.0))
        )
        self.assertEqual(
            by_path["group_1/blade_c"].local_placement,
            Transform(translation=(0.0, 100.0, 0.0)),
        )
        self.assertEqual(
            by_path["group_1/blade_c"].placement,
            Transform(translation=(0.0, 100.0, 200.0)),
        )

    def test_overall_bbox_covers_every_placed_part(self) -> None:
        result = build_assembly(self.root, self.store)
        self._assert_bbox(result, (-110.0, -10.0, -15.0), (105.0, 110.0, 215.0))

    def test_bom_counts_leaf_parts_recursively(self) -> None:
        result = build_assembly(self.root, self.store)
        entries = {
            (entry.document_id, entry.version, entry.configuration): entry
            for entry in result.bom
        }
        self.assertEqual(
            set(entries),
            {(self.part.id, 2, "default"), (self.part.id, 2, "long")},
        )
        default = entries[(self.part.id, 2, "default")]
        self.assertEqual(default.quantity, 1)
        self.assertEqual(default.paths, ("blade_a",))
        long = entries[(self.part.id, 2, "long")]
        self.assertEqual(long.quantity, 2)
        self.assertEqual(set(long.paths), {"blade_b", "group_1/blade_c"})

    def test_part_build_is_shared_between_instances(self) -> None:
        result = build_assembly(self.root, self.store)
        self.assertEqual(result.part_builds, 2)

    def test_rotation_is_applied_to_the_built_part(self) -> None:
        rotation = ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        document = new_assembly_document("rotated", document_id="a_rotated", seq=4)
        document = replace(
            document,
            instances=(
                Instance(
                    "blade",
                    PartRef(self.part.id, 2),
                    Transform(rotation=rotation, translation=(100.0, 200.0, 0.0)),
                ),
            ),
        )
        result = build_assembly(document, self.store)
        self.assertTrue(result.ok)
        self._assert_bbox(result, (90.0, 195.0, -15.0), (110.0, 205.0, 15.0))

    def test_failed_instances_are_isolated(self) -> None:
        document = new_assembly_document("broken", document_id="a_broken", seq=5)
        document = replace(
            document,
            instances=(
                Instance("good", PartRef(self.part.id, 2), Transform()),
                Instance(
                    "stale",
                    PartRef(self.part.id, 99),
                    Transform(translation=(50.0, 0.0, 0.0)),
                ),
                Instance(
                    "unknown_config",
                    PartRef(self.part.id, 2, "missing"),
                    Transform(translation=(0.0, 50.0, 0.0)),
                ),
                Instance("missing_assembly", AssemblyRef("a_missing", 1), Transform()),
            ),
        )
        result = build_assembly(document, self.store)
        self.assertFalse(result.ok)
        by_path = {item.path: item for item in result.instances}
        self.assertIsNotNone(by_path["good"].part)
        self.assertEqual(by_path["stale"].error_code, "VERSION_NOT_FOUND")
        self.assertEqual(by_path["unknown_config"].error_code, "UNKNOWN_CONFIG")
        self.assertEqual(by_path["missing_assembly"].error_code, "VERSION_NOT_FOUND")
        self.assertEqual(
            [item.path for item in result.failures],
            ["stale", "unknown_config", "missing_assembly"],
        )
        self.assertEqual(len(result.bom), 1)
        self.assertEqual(result.bom[0].quantity, 1)
        self._assert_bbox(result, (-5.0, -10.0, -15.0), (5.0, 10.0, 15.0))

    def test_suppressed_instance_is_not_built_or_counted(self) -> None:
        document = new_assembly_document(
            "suppressed", document_id="a_suppressed", seq=6
        )
        document = replace(
            document,
            instances=(
                Instance("shown", PartRef(self.part.id, 2), Transform()),
                Instance(
                    "hidden",
                    PartRef(self.part.id, 2),
                    Transform(translation=(100.0, 0.0, 0.0)),
                    suppressed=True,
                ),
            ),
        )
        result = build_assembly(document, self.store)
        self.assertTrue(result.ok)
        by_path = {item.path: item for item in result.instances}
        self.assertIsNone(by_path["hidden"].part)
        self.assertTrue(by_path["hidden"].suppressed)
        self.assertEqual(len(result.bom), 1)
        self.assertEqual(result.bom[0].quantity, 1)
        self.assertEqual(result.part_builds, 1)
        self._assert_bbox(result, (-5.0, -10.0, -15.0), (5.0, 10.0, 15.0))

    def test_assembly_cycle_is_reported_without_recursing(self) -> None:
        first = replace(
            new_assembly_document("first", document_id="a_first", seq=7),
            instances=(Instance("to_second", AssemblyRef("a_second", 1), Transform()),),
        )
        second = replace(
            new_assembly_document("second", document_id="a_second", seq=8),
            instances=(Instance("to_first", AssemblyRef("a_first", 1), Transform()),),
        )
        source = _MemorySource({("a_first", 1): first, ("a_second", 1): second})
        result = build_assembly(first, source)
        self.assertFalse(result.ok)
        self.assertEqual(
            [item.path for item in result.instances],
            ["to_second", "to_second/to_first"],
        )
        self.assertEqual(result.instances[-1].error_code, "REF_CYCLE")
        self.assertEqual(result.bom, ())
        self.assertIsNone(result.bbox_min)
        self.assertIsNone(result.bbox_max)

    def test_missing_root_assembly_raises_a_service_error(self) -> None:
        with self.assertRaises(ServiceError) as caught:
            self.service.build_assembly("a_missing")
        self.assertEqual(caught.exception.code, "NOT_FOUND")

    def test_instance_override_changes_the_built_part(self) -> None:
        assembly = new_assembly_document("override", seq=4)
        assembly = replace(
            assembly,
            instances=(
                Instance(
                    "blade_override",
                    PartRef(self.part.id, 2, "long"),
                    Transform(),
                    overrides={"length": 30.0},
                ),
            ),
        )
        self.store.save_assembly(assembly)
        result = self.service.build_assembly(assembly.id)
        self.assertTrue(result.ok, result.failures)
        self.assertAlmostEqual(
            float(result.instances[0].part.volume), 18000.0, delta=1e-6
        )

    def test_summary_is_geometry_free_and_json_safe(self) -> None:
        result = build_assembly(self.root, self.store)
        payload = result.summary()
        self.assertTrue(payload["ok"])
        self.assertEqual(json.loads(json.dumps(payload)), payload)
        self.assertTrue(payload["instances"][0]["has_geometry"])
        self.assertEqual(len(payload["failures"]), 0)
        self.assertEqual(payload["bom"][0]["quantity"], 1)


if __name__ == "__main__":
    unittest.main()
