"""Scene exposes every feature body while keeping the final shape."""

from __future__ import annotations

import tempfile
import unittest

from fastapi.testclient import TestClient

from cadwork.service import create_app


def _ops() -> list[dict]:
    return [
        {
            "op": "add",
            "feature": {
                "id": "base",
                "type": "k_box",
                "params": {"length": 20.0, "width": 10.0, "height": 5.0},
            },
        },
        {
            "op": "add",
            "feature": {
                "id": "boss",
                "type": "k_cylinder",
                "params": {"radius": 3.0, "height": 10.0},
            },
        },
        {
            "op": "add",
            "feature": {
                "id": "joined",
                "type": "k_fuse",
                "refs": {
                    "target": {"source": "base", "select": "self"},
                    "others": [{"source": "boss", "select": "self"}],
                },
            },
        },
    ]


class SceneBodyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.client = TestClient(create_app(self.folder.name))
        response = self.client.post("/api/docs", json={"name": "bodies"})
        self.assertEqual(response.status_code, 200, response.text)
        self.document_id = response.json()["id"]
        response = self.client.put(
            f"/api/docs/{self.document_id}", json={"base_version": 0, "ops": _ops()}
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_scene_lists_bodies(self) -> None:
        response = self.client.get(f"/api/docs/{self.document_id}/scene")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        bodies = {body["feature_id"]: body for body in payload["bodies"]}
        self.assertEqual(set(bodies), {"base", "boss", "joined"})
        self.assertTrue(bodies["joined"]["is_final"])
        self.assertFalse(bodies["base"]["is_final"])
        self.assertGreater(bodies["base"]["metrics"]["volume"], 0.0)
        self.assertIn("faces", payload)
        self.assertEqual(payload["feature"], "joined")

    def test_body_scene_can_be_requested_by_feature(self) -> None:
        response = self.client.get(
            f"/api/docs/{self.document_id}/scene", params={"feature": "base"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["feature"], "base")
        self.assertEqual(payload["metrics"]["volume"], 1000.0)
        self.assertEqual(
            {body["feature_id"] for body in payload["bodies"]},
            {"base", "boss", "joined"},
        )

    def test_state_lists_bodies(self) -> None:
        response = self.client.get(f"/api/docs/{self.document_id}/state")
        self.assertEqual(response.status_code, 200, response.text)
        bodies = response.json()["bodies"]
        self.assertEqual(
            {body["feature_id"] for body in bodies}, {"base", "boss", "joined"}
        )


if __name__ == "__main__":
    unittest.main()
