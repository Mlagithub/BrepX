"""Assembly STEP export keeps one product per placed part and a BOM sidecar."""

from __future__ import annotations

import re
import tempfile
import unittest
from dataclasses import replace

from fastapi.testclient import TestClient

from cadwork.design.assembly import Instance, PartRef, Transform, new_assembly_document
from cadwork.design.document import apply_ops
from cadwork.service import create_app
from cadwork.service.service import CADService
from cadwork.service.store import Store


class AssemblyExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
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

    def test_step_has_root_and_two_products(self) -> None:
        raw, media, sidecar = self.service.assembly_export(self.assembly.id)
        self.assertEqual(media, "application/step")
        text = raw.decode("utf-8", "replace")
        self.assertIn("ISO-10303-21", text)
        self.assertEqual(len(re.findall(r"=PRODUCT\(", text)), 3)
        self.assertEqual(sum(row["quantity"] for row in sidecar["bom"]), 2)
        self.assertEqual(sidecar["placed_parts"], 2)
        self.assertEqual(sidecar["failures"], [])

    def test_http_export_returns_attachment(self) -> None:
        client = TestClient(create_app(self.folder.name))
        response = client.get(f"/api/assemblies/{self.assembly.id}/export")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("ISO-10303-21", response.text)
        self.assertIn("attachment", response.headers["content-disposition"])


if __name__ == "__main__":
    unittest.main()
