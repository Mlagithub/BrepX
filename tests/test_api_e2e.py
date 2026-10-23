"""End-to-end integration tests for SMLib Studio Next backend & API."""

from __future__ import annotations

import unittest
from fastapi.testclient import TestClient
from server import app
from backend.workspace import workspace_session
from backend.semantic_patches import semantic_patch_manager


class TestApiE2E(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        workspace_session.clear()
        semantic_patch_manager.clear()

    def test_info(self) -> None:
        resp = self.client.get("/api/info")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["product"], "SMLib Studio Next")
        self.assertEqual(data["status"], "ready")

    def test_workspace_state_and_clear(self) -> None:
        resp = self.client.get("/api/workspace/state")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertGreater(data["scene"]["summary"]["volume"], 0)

        resp_clear = self.client.post("/api/workspace/clear")
        self.assertEqual(resp_clear.status_code, 200)
        data_clear = resp_clear.json()
        self.assertTrue(data_clear["ok"])

    def test_execute_operator_and_adjust_last(self) -> None:
        # Create Cylinder
        resp = self.client.post("/api/workspace/execute_operator", json={
            "operator": "cylinder",
            "params": {"radius": 15.0, "height": 40.0},
            "replace_all": True
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        vol1 = data["scene"]["summary"]["volume"]
        self.assertAlmostEqual(vol1, 28274.33, delta=50.0)

        # Adjust last operator (change height to 60)
        resp_adj = self.client.post("/api/workspace/adjust_last", json={
            "params": {"height": 60.0}
        })
        self.assertEqual(resp_adj.status_code, 200)
        data_adj = resp_adj.json()
        vol2 = data_adj["scene"]["summary"]["volume"]
        self.assertAlmostEqual(vol2, 42411.50, delta=50.0)

    def test_undo_redo(self) -> None:
        self.client.post("/api/workspace/execute_operator", json={
            "operator": "box",
            "params": {"length": 50, "width": 50, "height": 20},
            "replace_all": True
        })
        resp_hole = self.client.post("/api/workspace/execute_operator", json={
            "operator": "hole",
            "params": {"radius": 10.0, "depth": 30.0}
        })
        vol_hole = resp_hole.json()["scene"]["summary"]["volume"]

        resp_undo = self.client.post("/api/workspace/undo")
        self.assertEqual(resp_undo.status_code, 200)
        vol_undo = resp_undo.json()["scene"]["summary"]["volume"]
        self.assertAlmostEqual(vol_undo, 50000.0, delta=10.0)

        resp_redo = self.client.post("/api/workspace/redo")
        self.assertEqual(resp_redo.status_code, 200)
        self.assertAlmostEqual(resp_redo.json()["scene"]["summary"]["volume"], vol_hole, delta=10.0)

    def test_semantic_patches_and_export(self) -> None:
        self.client.post("/api/workspace/execute_operator", json={
            "operator": "box",
            "params": {"length": 60, "width": 40, "height": 20},
            "replace_all": True
        })
        # Assign Face #0 as inlet
        resp_patch = self.client.post("/api/semantic/patch", json={
            "face_indices": [0],
            "semantic_type": "inlet",
            "name": "inlet_main"
        })
        self.assertEqual(resp_patch.status_code, 200)
        patches = resp_patch.json()["patches"]
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0]["name"], "inlet_main")

        # Export CFD meta JSON
        resp_cfd = self.client.get("/api/export/cfd_meta")
        self.assertEqual(resp_cfd.status_code, 200)
        cfd_meta = resp_cfd.json()
        self.assertIn("inlet_main", cfd_meta["boundaries"])

        # Export STEP with semantics
        resp_step = self.client.get("/api/export/step")
        self.assertEqual(resp_step.status_code, 200)
        self.assertGreater(len(resp_step.content), 100)

    def test_agent_embodied_chat(self) -> None:
        # Initial cylinder
        self.client.post("/api/workspace/execute_operator", json={
            "operator": "cylinder",
            "params": {"radius": 20.0, "height": 50.0},
            "replace_all": True
        })
        # Agent cuts a hole on selected face
        resp_agent = self.client.post("/api/agent/chat", json={
            "prompt": "在顶面上开一个半径为8的通孔",
            "selections": ["part.faces()[0]"]
        })
        self.assertEqual(resp_agent.status_code, 200)
        res = resp_agent.json()
        self.assertTrue(res["ok"])
        self.assertIn("part =", res["code"])


if __name__ == "__main__":
    unittest.main()
