"""Assembly document storage, version pins and reference validation."""

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
from cadwork.design.document import apply_ops
from cadwork.service.store import Store, StoreError


class AssemblyStoreTests(unittest.TestCase):
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
        self.part = self.store.save(part)
        self.part = replace(
            self.part,
            version=2,
            configurations={"long": {"base": {"length": 20.0}}},
        )
        self.store.save(self.part)

    def tearDown(self) -> None:
        self.folder.cleanup()

    def _assembly_with_part(self, part_ref: PartRef | None = None, version: int = 1):
        document = new_assembly_document("assembly", seq=1)
        instance = Instance(
            "blade_1",
            part_ref or PartRef(self.part.id, 2),
            Transform(),
        )
        return replace(document, version=version, instances=(instance,))

    def test_assembly_crud_and_versions(self) -> None:
        assembly = self._assembly_with_part()
        self.store.save_assembly(assembly)
        loaded = self.store.get_assembly(assembly.id)
        self.assertEqual(loaded.version, 1)
        self.assertEqual(loaded.instances[0].id, "blade_1")

        second = replace(assembly, version=2, name="assembly revised")
        self.store.save_assembly(second)
        self.assertEqual(self.store.get_assembly(assembly.id).version, 2)
        self.assertEqual(
            self.store.get_assembly_version(assembly.id, 1).name, "assembly"
        )
        self.assertEqual(
            self.store.get_assembly_version(assembly.id, 2).name, "assembly revised"
        )
        self.assertEqual(self.store.list_assembly_versions(assembly.id), [1, 2])

    def test_list_reports_part_and_assembly_kind(self) -> None:
        assembly = self._assembly_with_part()
        self.store.save_assembly(assembly)
        kinds = {entry["id"]: entry["kind"] for entry in self.store.list()}
        self.assertEqual(kinds[self.part.id], "part")
        self.assertEqual(kinds[assembly.id], "assembly")

    def test_missing_part_version_is_rejected(self) -> None:
        assembly = self._assembly_with_part(PartRef(self.part.id, 99))
        with self.assertRaises(StoreError) as caught:
            self.store.save_assembly(assembly)
        self.assertEqual(caught.exception.code, "REF_NOT_FOUND")

    def test_missing_configuration_is_rejected(self) -> None:
        assembly = self._assembly_with_part(PartRef(self.part.id, 2, "missing"))
        with self.assertRaises(StoreError) as caught:
            self.store.save_assembly(assembly)
        self.assertEqual(caught.exception.code, "REF_CONFIG_NOT_FOUND")

    def test_nested_assembly_reference_resolves(self) -> None:
        child = self._assembly_with_part()
        self.store.save_assembly(child)
        parent = new_assembly_document("parent", seq=2)
        parent = replace(
            parent, instances=(Instance("sub", AssemblyRef(child.id, 1), Transform()),)
        )
        self.store.save_assembly(parent)
        self.assertEqual(
            self.store.get_assembly(parent.id).instances[0].ref.document_id, child.id
        )

    def test_same_version_cannot_be_rewritten(self) -> None:
        assembly = self._assembly_with_part()
        self.store.save_assembly(assembly)
        with self.assertRaises(StoreError) as caught:
            self.store.save_assembly(replace(assembly, name="different"))
        self.assertEqual(caught.exception.code, "IMMUTABLE_VERSION")

    def test_delete_removes_assembly_and_versions(self) -> None:
        assembly = self._assembly_with_part()
        self.store.save_assembly(assembly)
        self.store.delete(assembly.id)
        with self.assertRaises(StoreError):
            self.store.get_assembly(assembly.id)
        self.assertFalse(self.store.list_assembly_versions(assembly.id))


if __name__ == "__main__":
    unittest.main()
