"""End-to-end integration flow tests for BrepX M1 milestone."""

from __future__ import annotations

import re
import unittest
from fastapi.testclient import TestClient

from backend.session import session
from server import app

INDEX_PATTERN = re.compile(r"\(\)\[[0-9]")


class TestM1Flow(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        session.design = session.design.empty()

    def test_complete_m1_cad_lifecycle(self) -> None:
        res_h = self.client.get("/api/health")
        self.assertEqual(res_h.status_code, 200)

        box_payload = {
            "command_id": "c1_box",
            "op": "box",
            "params": {"length": 60.0, "width": 40.0, "height": 20.0},
            "idempotency_key": "k_m1_box",
        }
        res_box = self.client.post("/api/command", json=box_payload)
        self.assertEqual(res_box.status_code, 200)
        box_data = res_box.json()
        self.assertTrue(box_data["ok"])
        self.assertEqual(box_data["version"], 2)
        initial_vol = box_data["body"]["volume"]
        initial_faces = box_data["body"]["face_count"]
        self.assertAlmostEqual(initial_vol, 48000.0, delta=1e-3)
        self.assertEqual(initial_faces, 6)

        res_query = self.client.get("/api/query")
        self.assertEqual(res_query.status_code, 200)
        body = res_query.json()["body"]
        self.assertEqual(body["face_count"], 6)

        top_selector = None
        for face in body["faces"]:
            self.assertIsNone(INDEX_PATTERN.search(face["selector"]))
            if face["normal"] == [0.0, 0.0, 1.0] and face["is_planar"]:
                top_selector = face["selector"]

        self.assertIsNotNone(top_selector)

        hole_payload = {
            "command_id": "c2_hole",
            "op": "hole",
            "target": {"base": "prev", "expr": top_selector},
            "params": {"radius": 6.0, "depth": 40.0},
            "idempotency_key": "k_m1_hole",
        }
        res_hole = self.client.post("/api/command", json=hole_payload)
        self.assertEqual(res_hole.status_code, 200)
        hole_data = res_hole.json()
        self.assertTrue(hole_data["ok"])
        self.assertEqual(hole_data["version"], 3)
        holed_vol = hole_data["body"]["volume"]
        self.assertLess(holed_vol, initial_vol)

        res_scene = self.client.get("/api/scene")
        self.assertEqual(res_scene.status_code, 200)
        bodies = res_scene.json()["bodies"]
        self.assertEqual(len(bodies), 1)
        self.assertGreater(len(bodies[0]["faces"]), 6)

        res_undo = self.client.post("/api/undo")
        self.assertEqual(res_undo.status_code, 200)
        undo_data = res_undo.json()
        self.assertEqual(undo_data["version"], 4)
        self.assertAlmostEqual(undo_data["body"]["volume"], initial_vol, delta=1e-3)

        res_redo = self.client.post("/api/redo")
        self.assertEqual(res_redo.status_code, 200)
        redo_data = res_redo.json()
        self.assertEqual(redo_data["version"], 5)
        self.assertAlmostEqual(redo_data["body"]["volume"], holed_vol, delta=1e-3)


if __name__ == "__main__":
    unittest.main()
