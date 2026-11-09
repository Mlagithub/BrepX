"""End-to-end integration test validating frontend workbench contracts and API endpoints (M5)."""

from __future__ import annotations

import json
import unittest
from fastapi.testclient import TestClient

from backend.session import session
from server import app


class TestM5FrontendIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        session.design = session.design.empty()

    def test_full_workbench_lifecycle_and_exports(self) -> None:
        res_box = self.client.post("/api/command", json={
            "command_id": "c1_box",
            "op": "box",
            "params": {"length": 60.0, "width": 40.0, "height": 20.0},
            "idempotency_key": "k_m5_box",
        })
        self.assertEqual(res_box.status_code, 200)
        self.assertEqual(res_box.json()["version"], 2)

        res_scene = self.client.get("/api/scene")
        self.assertEqual(res_scene.status_code, 200)
        bodies = res_scene.json()["bodies"]
        self.assertEqual(len(bodies), 1)
        self.assertEqual(len(bodies[0]["faces"]), 6)
        self.assertEqual(len(bodies[0]["edges"]), 12)

        res_hole = self.client.post("/api/command", json={
            "command_id": "c2_hole",
            "op": "hole",
            "target": {"base": "prev", "expr": "faces().facing(Z)"},
            "params": {"radius": 6.0, "depth": 40.0},
            "idempotency_key": "k_m5_hole",
        })
        self.assertEqual(res_hole.status_code, 200)
        self.assertEqual(res_hole.json()["version"], 3)

        patch_res = self.client.patch("/api/command/c1_box/params", json={
            "params": {"length": 80.0},
        })
        self.assertEqual(patch_res.status_code, 200)
        self.assertTrue(patch_res.json()["ok"])
        self.assertIn("c2_hole", patch_res.json()["rebuilt"])

        tag_res = self.client.post("/api/command", json={
            "command_id": "c3_tag",
            "op": "tag_boundary",
            "target": {"base": "prev", "expr": "faces().facing(Z)"},
            "params": {"semantic_type": "inlet", "name": "box_inlet"},
            "idempotency_key": "k_m5_tag",
        })
        self.assertEqual(tag_res.status_code, 200)

        step_res = self.client.get("/api/export/step")
        self.assertEqual(step_res.status_code, 200)

        stl_res = self.client.get("/api/export/stl")
        self.assertEqual(stl_res.status_code, 200)

        dxf_res = self.client.get("/api/export/dxf")
        self.assertEqual(dxf_res.status_code, 200)

        cfd_res = self.client.get("/api/export/cfd-dict")
        self.assertEqual(cfd_res.status_code, 200)
        cfd_data = json.loads(cfd_res.content.decode("utf-8"))
        self.assertEqual(cfd_data["boundary_count"], 1)

        py_res = self.client.get("/api/export/python")
        self.assertEqual(py_res.status_code, 200)
        self.assertIn("build_model", py_res.content.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
