"""Tests for the smlibpy kernel inventory.

The inventory is the classification contract for every public kernel callable:
the generated baseline under ``cadwork/design/`` must cover it exactly, and no
callable may be left unclassified.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cadwork.design import kernel_inventory as inventory

EXPECTED_CLASSES = {
    "Align",
    "Axis",
    "Bend",
    "BoundBox",
    "ClosestPoints",
    "Continuity",
    "Curvature",
    "DrawingView",
    "Edge",
    "Face",
    "FitReport",
    "FlatPattern",
    "FontError",
    "Hit",
    "KernelError",
    "Lattice",
    "Location",
    "Locations",
    "MassProperties",
    "Mesh",
    "ModelingError",
    "Nurbs",
    "NurbsSurface",
    "Part",
    "Plane",
    "Problem",
    "Profile",
    "RepairReport",
    "SectionProperties",
    "Shape",
    "ShapeList",
    "Shell",
    "Sketch",
    "StepCurve",
    "StepFrame",
    "StepModel",
    "StepPoint",
    "StitchReport",
    "Vector",
    "Vertex",
    "Wire",
}

EXPECTED_METHOD_COUNTS = {
    "Part": 74,
    "Sketch": 53,
    "Profile": 12,
    "ShapeList": 60,
    "Face": 39,
}

EXPECTED_TOP_LEVEL = 156
EXPECTED_CLASSES_COUNT = 41

# ShapeList splits into explicit sets, matching refs.py: selectors and the
# relationship helpers are REF; callable criteria and BoundBox filters are
# DEFER; container/mutation/metadata helpers are N/A.
SHAPELIST_REF = {
    "at",
    "back",
    "bottom",
    "circles",
    "concave",
    "convex",
    "count",
    "cylinders",
    "derived_from",
    "edges",
    "facing",
    "faces",
    "fillets",
    "front",
    "g1",
    "g2",
    "group_by",
    "hit_by",
    "joining",
    "largest",
    "left",
    "lines",
    "max_by",
    "min_by",
    "nearest",
    "new",
    "of_type",
    "one",
    "parallel_to",
    "perpendicular_to",
    "planar",
    "right",
    "shared",
    "smallest",
    "smooth",
    "sort_by",
    "sort_by_distance",
    "tangent_chain",
    "top",
    "vertices",
    "wires",
}
SHAPELIST_DEFER = {"filter", "filter_by", "within"}
SHAPELIST_NA = {
    "append",
    "bbox",
    "center",
    "clear",
    "copy",
    "extend",
    "index",
    "insert",
    "moved",
    "on",
    "pop",
    "remove",
    "reverse",
    "rotate",
    "sort",
    "translate",
}


def _baseline_path() -> Path:
    return Path(inventory.__file__).with_name("kernel_actions.baseline.json")


class InventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = inventory.inventory()
        cls.baseline = inventory.baseline_document()

    def test_no_unclassified(self) -> None:
        self.assertEqual(inventory.unclassified(), [])

    def test_no_stale_table_entries(self) -> None:
        self.assertEqual(inventory.stale_entries(), [])

    def test_top_level_function_count(self) -> None:
        self.assertEqual(len(inventory.top_level_functions()), EXPECTED_TOP_LEVEL)
        top_level_records = [r for r in self.records if r["owner"] == "smlibpy"]
        self.assertEqual(len(top_level_records), EXPECTED_TOP_LEVEL)

    def test_known_public_classes(self) -> None:
        self.assertEqual(len(inventory.public_classes()), EXPECTED_CLASSES_COUNT)
        self.assertEqual(set(inventory.public_classes()), EXPECTED_CLASSES)

    def test_explicit_method_tables_are_complete(self) -> None:
        for owner, expected in EXPECTED_METHOD_COUNTS.items():
            with self.subTest(owner=owner):
                self.assertEqual(len(inventory.public_methods(owner)), expected)
                classified = [
                    r
                    for r in self.records
                    if r["owner"] == owner and r["destination"] is not None
                ]
                self.assertEqual(len(classified), expected)

    def test_shape_list_destination_sets(self) -> None:
        shape_list = {
            record["name"]: record["destination"]
            for record in self.records
            if record["owner"] == "ShapeList"
        }
        self.assertEqual(
            set(shape_list),
            SHAPELIST_REF | SHAPELIST_DEFER | SHAPELIST_NA,
        )
        by_destination: dict[str, set[str]] = {}
        for name, destination in shape_list.items():
            by_destination.setdefault(destination, set()).add(name)
        self.assertEqual(by_destination.get("REF"), SHAPELIST_REF)
        self.assertEqual(by_destination.get("DEFER"), SHAPELIST_DEFER)
        self.assertEqual(by_destination.get("N/A"), SHAPELIST_NA)
        self.assertEqual(len(shape_list), 60)

    def test_shape_list_property_selectors(self) -> None:
        # ``count`` is an ordinary method; ``first``/``last`` are properties,
        # so they are not enumerated as callables but are still REF in refs.py.
        cls = inventory.smlibpy.ShapeList
        for name in ("first", "last"):
            self.assertFalse(callable(getattr(cls, name)))
            self.assertNotIn(
                ("ShapeList", name),
                {(record["owner"], record["name"]) for record in self.records},
            )
        count = [
            record
            for record in self.records
            if record["owner"] == "ShapeList" and record["name"] == "count"
        ]
        self.assertEqual(count[0]["destination"], "REF")

    def test_gen_count_at_least_80(self) -> None:
        gen = [r for r in self.records if r["destination"] == inventory.GEN]
        self.assertGreaterEqual(len(gen), 80)

    def test_records_sorted_unique(self) -> None:
        keys = [(r["owner"], r["name"]) for r in self.records]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_record_is_well_formed(self) -> None:
        for record in self.records:
            self.assertEqual(set(record), {"owner", "name", "destination", "reason"})
            self.assertIn(record["destination"], inventory.DESTINATIONS)
            self.assertIsInstance(record["reason"], str)
            self.assertTrue(record["reason"])

    def test_destination_counts_add_up(self) -> None:
        counts = inventory.destination_counts(self.records)
        self.assertEqual(counts["unclassified"], 0)
        self.assertEqual(sum(counts.values()), len(self.records))

    def test_baseline_document_metadata(self) -> None:
        self.assertEqual(self.baseline["schema_version"], inventory.SCHEMA_VERSION)
        self.assertEqual(self.baseline["smlibpy_version"], inventory.kernel_version())
        self.assertEqual(self.baseline["records"], self.records)

    def test_baseline_file_covers_every_callable(self) -> None:
        path = _baseline_path()
        self.assertTrue(path.is_file(), f"missing generated baseline {path}")
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(on_disk, self.baseline)
        actual = {(r["owner"], r["name"]) for r in inventory.inventory()}
        baseline = {(r["owner"], r["name"]) for r in on_disk["records"]}
        self.assertEqual(baseline, actual)

    def test_generated_artifacts_roundtrip_in_tempdir(self) -> None:
        # The CLI writes these two artifacts; make sure the rendered text is
        # deterministic and self-consistent without touching the repository.
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            docs = tmpdir / "kernel-inventory.md"
            baseline = tmpdir / "kernel_actions.baseline.json"
            docs.write_text(inventory.render_markdown(), encoding="utf-8", newline="\n")
            baseline.write_text(
                inventory.baseline_json(), encoding="utf-8", newline="\n"
            )

            markdown = docs.read_text(encoding="utf-8")
            self.assertIn("| Owner | Name | Destination | Reason |", markdown)
            callables = markdown.split("## Callables", 1)[1]
            row_count = sum(
                1
                for line in callables.splitlines()
                if line.startswith("| ")
                and not line.startswith("| Owner")
                and not line.startswith("|---")
            )
            self.assertEqual(row_count, len(self.records))

            loaded = json.loads(baseline.read_text(encoding="utf-8"))
            self.assertEqual(loaded, inventory.baseline_document())
            self.assertEqual(inventory.baseline_json(), inventory.baseline_json())


if __name__ == "__main__":
    unittest.main()
