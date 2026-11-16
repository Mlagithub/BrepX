"""Reference pins, explicit updates and BOM projection."""

from __future__ import annotations

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
from cadwork.design.assembly_refs import (
    bom_rows,
    bom_summary,
    reference_status,
    update_references,
)
from cadwork.design.document import apply_ops
from cadwork.service.store import Store


class ReferenceUpdateTests(unittest.TestCase):
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
                        "params": {"length": 10.0, "width": 10.0, "height": 10.0},
                    },
                }
            ],
        )
        self.part_v1 = self.store.save(part)
        self.part_v2 = replace(
            self.part_v1, version=2, configurations={"long": {"base": {"length": 20.0}}}
        )
        self.store.save(self.part_v2)

    def tearDown(self) -> None:
        self.folder.cleanup()

    def _assembly(self, version: int = 1) -> object:
        document = new_assembly_document("assembly", seq=1)
        return replace(
            document,
            version=version,
            instances=(
                Instance("blade_a", PartRef(self.part_v1.id, 1), Transform()),
                Instance(
                    "blade_b",
                    PartRef(self.part_v1.id, 2, "long"),
                    Transform(translation=(20.0, 0.0, 0.0)),
                ),
            ),
        )

    def test_status_marks_outdated_and_reports_configuration(self) -> None:
        assembly = self._assembly()
        status = reference_status(assembly, self.store)
        self.assertTrue(status[0]["outdated"])
        self.assertFalse(status[1]["outdated"])
        self.assertTrue(all(row["configuration_ok"] for row in status))
        self.assertEqual(status[1]["configuration"], "long")

    def test_update_references_creates_one_new_version(self) -> None:
        assembly = self._assembly()
        self.store.save_assembly(assembly)
        updated = update_references(assembly, self.store)
        self.assertEqual(updated.version, 2)
        self.assertTrue(
            all(
                row["pinned_version"] == 2
                for row in reference_status(updated, self.store)
            )
        )
        self.store.save_assembly(updated)
        self.assertEqual(self.store.get_assembly_version(assembly.id, 1).version, 1)
        self.assertEqual(self.store.get_assembly_version(assembly.id, 2).version, 2)

    def test_update_is_noop_when_current(self) -> None:
        assembly = self._assembly()
        updated = update_references(assembly, self.store)
        again = update_references(updated, self.store)
        self.assertIs(again, updated)

    def test_missing_reference_is_reported_and_update_fails(self) -> None:
        document = new_assembly_document("missing", seq=2)
        document = replace(
            document,
            instances=(Instance("ghost", PartRef("part_missing", 1), Transform()),),
        )
        status = reference_status(document, self.store)
        self.assertFalse(status[0]["available"])
        self.assertFalse(status[0]["outdated"])
        with self.assertRaises(Exception):
            update_references(document, self.store)

    def test_bom_rows_and_summary_include_nested_assembly(self) -> None:
        child = self._assembly()
        self.store.save_assembly(child)
        parent = new_assembly_document("parent", seq=2)
        parent = replace(
            parent,
            instances=(Instance("child", AssemblyRef(child.id, 1), Transform()),),
        )
        self.store.save_assembly(parent)
        rows = bom_rows(parent, self.store)
        self.assertEqual(rows[0]["kind"], "assembly")
        self.assertEqual(len([row for row in rows if row["kind"] == "part"]), 2)
        summary = bom_summary(rows)
        self.assertEqual(sum(row["quantity"] for row in summary), 2)
        self.assertTrue(
            all(row["configuration"] in {None, "default", "long"} for row in summary)
        )


if __name__ == "__main__":
    unittest.main()
