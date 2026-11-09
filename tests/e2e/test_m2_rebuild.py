"""End-to-end parametric rebuild and selector failure diagnostic tests for M2."""

from __future__ import annotations

import unittest
from fastapi.testclient import TestClient

from backend.session import session
from server import app


class TestM2Rebuild(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        session.design = session.design.empty()

    def test_parametric_rebuild_downstream_cascade(self) -> None:
        res1 = self.client.post("/api/command", json={
            "command_id": "c1_box",
            "op": "box",
            "params": {"length": 60.0, "width": 40.0, "height": 20.0},
            "idempotency_key": "k_m2_c1",
        })
        self.assertEqual(res1.status_code, 200)

        res2 = self.client.post("/api/command", json={
            "command_id": "c2_hole",
            "op": "hole",
            "target": {"base": "prev", "expr": "faces().top()"},
            "params": {"radius": 6.0, "depth": 40.0},
            "idempotency_key": "k_m2_c2",
        })
        self.assertEqual(res2.status_code, 200)

        res3 = self.client.post("/api/command", json={
            "command_id": "c3_fillet",
            "op": "fillet",
            "target": {"base": "prev", "expr": "edges().nearest([30.0, 20.0, 0.0])"},
            "params": {"radius": 2.0},
            "idempotency_key": "k_m2_c3",
        })
        self.assertEqual(res3.status_code, 200)
        orig_vol = res3.json()["body"]["volume"]

        patch_res = self.client.patch("/api/command/c1_box/params", json={
            "params": {"height": 30.0},
        })
        self.assertEqual(patch_res.status_code, 200)
        data = patch_res.json()
        self.assertTrue(data["ok"])
        self.assertIn("c2_hole", data["rebuilt"])
        self.assertIn("c3_fillet", data["rebuilt"])
        self.assertNotIn("c1_box", data["rebuilt"])
        self.assertGreater(data["body"]["volume"], orig_vol)
        self.assertTrue(data["body"]["is_valid"])

    def test_selector_failure_returns_structured_diagnostic(self) -> None:
        res1 = self.client.post("/api/command", json={
            "command_id": "c1_box",
            "op": "box",
            "params": {"length": 60.0, "width": 40.0, "height": 20.0},
            "idempotency_key": "k_m2_fail_c1",
        })
        self.assertEqual(res1.status_code, 200)

        res2 = self.client.post("/api/command", json={
            "command_id": "c2_hole",
            "op": "hole",
            "target": {"base": "prev", "expr": "faces().top()"},
            "params": {"radius": 6.0, "depth": 40.0},
            "idempotency_key": "k_m2_fail_c2",
        })
        self.assertEqual(res2.status_code, 200)

        version_before = session.design.version
        vol_before = session.design.geometry.volume

        fail_patch_res = self.client.patch("/api/command/c2_hole/params", json={
            "params": {"radius": -10.0},
        })
        self.assertEqual(fail_patch_res.status_code, 400)
        err_data = fail_patch_res.json()

        self.assertFalse(err_data["ok"])
        self.assertEqual(err_data["failed_command"], "c2_hole")
        self.assertIn("error", err_data)

        self.assertEqual(session.design.version, version_before)
        self.assertAlmostEqual(session.design.geometry.volume, vol_before, delta=1e-4)


if __name__ == "__main__":
    unittest.main()
