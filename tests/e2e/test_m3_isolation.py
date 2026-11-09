"""End-to-end process isolation tests for BrepX CAD host and Agent service."""

from __future__ import annotations

import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.adapters.agent.main import app as agent_app
from backend.session import session
from server import app as host_app


class TestM3Isolation(unittest.TestCase):
    def setUp(self) -> None:
        self.host_client = TestClient(host_app)
        self.agent_client = TestClient(agent_app)
        session.design = session.design.empty()

    def test_isolated_agent_turn_execution_mocked(self) -> None:
        mock_reply = '{"explanation": "create box", "commands": [{"op": "box", "params": {"length": 60, "width": 40, "height": 20}}]}'

        with patch("backend.adapters.agent.service.chat", return_value=mock_reply):
            def mock_exec_in_host(url, cmd):
                res = self.host_client.post("/api/command", json=cmd)
                return res.json()

            with patch("backend.adapters.agent.service._execute_command_via_http", side_effect=mock_exec_in_host):
                res_box = self.host_client.post("/api/command", json={
                    "command_id": "c1_init",
                    "op": "box",
                    "params": {"length": 60, "width": 40, "height": 20},
                    "idempotency_key": "k_init_box",
                })
                self.assertEqual(res_box.status_code, 200)

                q_res = self.host_client.get("/api/query")
                self.assertEqual(q_res.status_code, 200)
                self.assertIsNotNone(q_res.json()["body"])

    def test_cad_host_fully_operates_when_agent_process_is_dead(self) -> None:
        del self.agent_client

        box_res = self.host_client.post("/api/command", json={
            "command_id": "c_box_no_agent",
            "op": "box",
            "params": {"length": 50.0, "width": 50.0, "height": 20.0},
            "idempotency_key": "k_no_agent_1",
        })
        self.assertEqual(box_res.status_code, 200)
        self.assertTrue(box_res.json()["ok"])
        initial_vol = box_res.json()["body"]["volume"]

        hole_res = self.host_client.post("/api/command", json={
            "command_id": "c_hole_no_agent",
            "op": "hole",
            "target": {"base": "prev", "expr": "faces().top()"},
            "params": {"radius": 5.0, "depth": 20.0},
            "idempotency_key": "k_no_agent_2",
        })
        self.assertEqual(hole_res.status_code, 200)
        self.assertLess(hole_res.json()["body"]["volume"], initial_vol)

        undo_res = self.host_client.post("/api/undo")
        self.assertEqual(undo_res.status_code, 200)
        self.assertAlmostEqual(undo_res.json()["body"]["volume"], initial_vol, delta=1e-3)

        redo_res = self.host_client.post("/api/redo")
        self.assertEqual(redo_res.status_code, 200)
        self.assertAlmostEqual(redo_res.json()["body"]["volume"], hole_res.json()["body"]["volume"], delta=1e-3)


if __name__ == "__main__":
    unittest.main()
