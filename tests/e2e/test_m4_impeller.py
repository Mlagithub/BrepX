"""End-to-end integration test for parametric impeller generation and CFD delivery (M4)."""

from __future__ import annotations

import json
import unittest
from fastapi.testclient import TestClient

from backend.session import session
from server import app


class TestM4Impeller(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        session.design = session.design.empty()

    def test_parametric_impeller_generation_and_cfd_export(self) -> None:
        res_runner = self.client.post("/api/command", json={
            "command_id": "c1_runner",
            "op": "blade_runner",
            "params": {
                "hub_radius": 20.0,
                "tip_radius": 45.0,
                "height": 25.0,
                "blade_count": 6,
                "twist_deg": 25.0,
                "thickness": 3.0,
            },
            "idempotency_key": "k_m4_runner",
        })
        self.assertEqual(res_runner.status_code, 200)
        body = res_runner.json()["body"]
        self.assertTrue(body["is_valid"])
        self.assertGreater(body["volume"], 0)
        self.assertGreater(body["face_count"], 20)

        res_inlet = self.client.post("/api/command", json={
            "command_id": "c2_inlet",
            "op": "tag_boundary",
            "target": {"base": "prev", "expr": "faces().nearest([0.0, 0.0, 25.0], normal=[0.0, 0.0, 1.0])"},
            "params": {"semantic_type": "inlet", "name": "impeller_inlet"},
            "idempotency_key": "k_m4_inlet",
        })
        self.assertEqual(res_inlet.status_code, 200)

        res_wall = self.client.post("/api/command", json={
            "command_id": "c3_wall",
            "op": "tag_boundary",
            "target": {"base": "prev", "expr": "faces().cylinders()"},
            "params": {"semantic_type": "wall", "name": "hub_casing_wall"},
            "idempotency_key": "k_m4_wall",
        })
        self.assertEqual(res_wall.status_code, 200)

        res_cfd = self.client.get("/api/export/cfd-dict")
        self.assertEqual(res_cfd.status_code, 200)
        cfd_payload = json.loads(res_cfd.content.decode("utf-8"))
        self.assertEqual(cfd_payload["boundary_count"], 2)
        names = [b["name"] for b in cfd_payload["boundaries"]]
        self.assertIn("impeller_inlet", names)
        self.assertIn("hub_casing_wall", names)

        res_step = self.client.get("/api/export/step")
        self.assertEqual(res_step.status_code, 200)
        self.assertGreater(len(res_step.content), 1000)

        res_stl = self.client.get("/api/export/stl")
        self.assertEqual(res_stl.status_code, 200)
        self.assertGreater(len(res_stl.content), 500)

        res_py = self.client.get("/api/export/python")
        self.assertEqual(res_py.status_code, 200)
        py_code = res_py.content.decode("utf-8")
        compiled = compile(py_code, "<gen_script>", "exec")
        self.assertIsNotNone(compiled)


if __name__ == "__main__":
    unittest.main()
