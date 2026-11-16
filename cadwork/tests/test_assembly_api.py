"""HTTP surface for assembly documents."""

from __future__ import annotations

import tempfile
import unittest

from fastapi.testclient import TestClient

from cadwork.design.assembly import Instance, PartRef, Transform, instance_to_json
from cadwork.service import create_app


class AssemblyApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.client = TestClient(create_app(self.folder.name))
        response = self.client.post("/api/docs", json={"name": "blade"})
        self.assertEqual(response.status_code, 200, response.text)
        self.part_id = response.json()["id"]
        response = self.client.put(
            f"/api/docs/{self.part_id}",
            json={
                "base_version": 0,
                "ops": [
                    {
                        "op": "add",
                        "feature": {
                            "id": "base",
                            "type": "k_box",
                            "params": {"length": 10.0, "width": 6.0, "height": 4.0},
                        },
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)

        response = self.client.post("/api/assemblies", json={"name": "assembly"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assembly_id = response.json()["assembly"]["id"]

    def _add_instance(self, base_version: int = 1) -> dict:
        payload = instance_to_json(
            Instance("blade_a", PartRef(self.part_id, 1), Transform())
        )
        response = self.client.put(
            f"/api/assemblies/{self.assembly_id}",
            json={
                "base_version": base_version,
                "ops": [{"op": "add", "instance": payload}],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_assembly_state_scene_bom_and_references(self) -> None:
        state = self._add_instance()
        self.assertEqual(state["assembly"]["version"], 2)
        self.assertEqual(len(state["assembly"]["instances"]), 1)
        self.assertEqual(state["build"]["bom"][0]["quantity"], 1)

        scene = self.client.get(f"/api/assemblies/{self.assembly_id}/scene").json()
        self.assertEqual(len(scene["instances"]), 1)
        self.assertEqual(len(scene["definitions"]), 1)

        bom = self.client.get(f"/api/assemblies/{self.assembly_id}/bom").json()
        self.assertEqual(sum(row["quantity"] for row in bom["summary"]), 1)

        references = self.client.get(
            f"/api/assemblies/{self.assembly_id}/references"
        ).json()
        self.assertFalse(references["references"][0]["outdated"])

    def test_part_update_then_explicit_reference_update(self) -> None:
        self._add_instance()
        response = self.client.put(
            f"/api/docs/{self.part_id}",
            json={
                "base_version": 1,
                "ops": [{"op": "update", "id": "base", "params": {"length": 20.0}}],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        references = self.client.get(
            f"/api/assemblies/{self.assembly_id}/references"
        ).json()
        self.assertTrue(references["outdated"])
        response = self.client.post(
            f"/api/assemblies/{self.assembly_id}/update-references",
            json={"base_version": 2},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["assembly"]["version"], 3)
        self.assertEqual(response.json()["references"][0]["pinned_version"], 2)

    def test_stale_edit_is_rejected(self) -> None:
        self._add_instance()
        payload = instance_to_json(
            Instance("blade_b", PartRef(self.part_id, 1), Transform())
        )
        response = self.client.put(
            f"/api/assemblies/{self.assembly_id}",
            json={
                "base_version": 1,
                "ops": [{"op": "add", "instance": payload}],
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "STALE_VERSION")

    def test_bad_reference_on_save_is_rejected(self) -> None:
        payload = instance_to_json(
            Instance("ghost", PartRef("part_missing", 1), Transform())
        )
        response = self.client.put(
            f"/api/assemblies/{self.assembly_id}",
            json={
                "base_version": 1,
                "ops": [{"op": "add", "instance": payload}],
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "REF_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
