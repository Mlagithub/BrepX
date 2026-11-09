"""Integration tests for FastAPI REST routes using TestClient."""

from __future__ import annotations

import unittest
from fastapi.testclient import TestClient

from backend.session import session
from server import app


class TestAPIRoutes(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        session.design = session.design.empty()

    def test_health_check(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_empty_query_and_scene(self) -> None:
        q_res = self.client.get("/api/query")
        self.assertEqual(q_res.status_code, 200)
        self.assertIsNone(q_res.json()["body"])

        s_res = self.client.get("/api/scene")
        self.assertEqual(s_res.status_code, 200)
        self.assertEqual(s_res.json()["bodies"], [])

    def test_command_box_and_hole_lifecycle(self) -> None:
        box_payload = {
            "command_id": "c1",
            "op": "box",
            "params": {"length": 60.0, "width": 40.0, "height": 20.0},
            "idempotency_key": "k_api_box",
        }
        res_box = self.client.post("/api/command", json=box_payload)
        self.assertEqual(res_box.status_code, 200)
        data_box = res_box.json()
        self.assertTrue(data_box["ok"])
        self.assertEqual(data_box["version"], 2)
        initial_vol = data_box["body"]["volume"]

        hole_payload = {
            "command_id": "c2",
            "op": "hole",
            "target": {"base": "prev", "expr": "faces().top()"},
            "params": {"radius": 6.0, "depth": 40.0},
            "idempotency_key": "k_api_hole",
        }
        res_hole = self.client.post("/api/command", json=hole_payload)
        self.assertEqual(res_hole.status_code, 200)
        data_hole = res_hole.json()
        self.assertTrue(data_hole["ok"])
        self.assertEqual(data_hole["version"], 3)
        self.assertLess(data_hole["body"]["volume"], initial_vol)

        res_scene = self.client.get("/api/scene")
        self.assertEqual(res_scene.status_code, 200)
        self.assertEqual(len(res_scene.json()["bodies"]), 1)

        res_undo = self.client.post("/api/undo")
        self.assertEqual(res_undo.status_code, 200)
        self.assertEqual(res_undo.json()["version"], 4)
        self.assertAlmostEqual(res_undo.json()["body"]["volume"], initial_vol, delta=1e-3)

        res_redo = self.client.post("/api/redo")
        self.assertEqual(res_redo.status_code, 200)
        self.assertEqual(res_redo.json()["version"], 5)
        self.assertAlmostEqual(res_redo.json()["body"]["volume"], data_hole["body"]["volume"], delta=1e-3)

    def test_domain_error_status_and_diagnostic(self) -> None:
        bad_op_payload = {
            "command_id": "c_bad_op",
            "op": "unknown_operator_name",
            "params": {},
            "idempotency_key": "k_bad_op",
        }
        res = self.client.post("/api/command", json=bad_op_payload)
        self.assertEqual(res.status_code, 400)
        err_data = res.json()
        self.assertFalse(err_data["ok"])
        self.assertEqual(err_data["error"]["error"], "OperatorNotFoundError")

        box_payload = {
            "command_id": "c1",
            "op": "box",
            "params": {"length": 60.0, "width": 40.0, "height": 20.0},
            "idempotency_key": "k_api_box_2",
        }
        self.client.post("/api/command", json=box_payload)

        raw_index_payload = {
            "command_id": "c_idx",
            "op": "hole",
            "target": {"base": "prev", "expr": "faces()[3]"},
            "params": {"radius": 6.0, "depth": 40.0},
            "idempotency_key": "k_bad_idx",
        }
        res_idx = self.client.post("/api/command", json=raw_index_payload)
        self.assertEqual(res_idx.status_code, 400)
        self.assertIn("Topological raw integer index forbidden", res_idx.json()["error"]["message"])


if __name__ == "__main__":
    unittest.main()
