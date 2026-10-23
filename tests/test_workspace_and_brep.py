"""Unit tests for WorkspaceSession and B-Rep topological graphic serialization."""

from __future__ import annotations

import unittest
from smlibpy import Box
from backend.workspace import WorkspaceSession, SecurityViolationError
from backend.brep_graphic import serialize_body


class TestWorkspaceAndBrep(unittest.TestCase):
    def setUp(self) -> None:
        self.ws = WorkspaceSession()

    def test_brep_serialization_box(self) -> None:
        part = Box(60, 40, 20)
        container = serialize_body("part", "part", part)
        self.assertEqual(container["faces_count"], 6)
        self.assertEqual(container["edges_count"], 12)
        self.assertEqual(container["vertices_count"], 8)
        self.assertAlmostEqual(container["volume"], 48000.0, places=1)
        for idx, face in enumerate(container["faces"]):
            self.assertEqual(face["face_index"], idx)
            self.assertEqual(face["expr"], f"part.faces()[{idx}]")
            self.assertEqual(face["geom_type"], "plane")
            self.assertGreater(len(face["indices"]), 0)

    def test_ast_security_sandbox(self) -> None:
        with self.assertRaises(SecurityViolationError):
            self.ws.execute_step("import os\npart = Box(10, 10, 10)")
        with self.assertRaises(SecurityViolationError):
            self.ws.execute_step("import subprocess\npart = Box(10, 10, 10)")
        with self.assertRaises(SecurityViolationError):
            self.ws.execute_step("open('hack.txt', 'w')\npart = Box(10, 10, 10)")

    def test_execute_undo_redo_and_adjust_last(self) -> None:
        st1 = self.ws.execute_step("part = Box(60, 40, 20)", label="Create Box", operator_id="box", params={"length": 60})
        self.assertAlmostEqual(st1["scene"]["summary"]["volume"], 48000.0, places=1)

        st2 = self.ws.execute_step(
            "part = part - Cylinder(10, 30)",
            label="Cut Hole",
            operator_id="hole",
            params={"radius": 10},
        )
        vol_with_r10 = st2["scene"]["summary"]["volume"]
        self.assertLess(vol_with_r10, 48000.0)

        # Adjust last operation (change hole radius from 10 to 5 without stacking twice)
        st_adj = self.ws.adjust_last_step(
            "part = part - Cylinder(5, 30)",
            new_params={"radius": 5},
            label="Cut Hole (R=5)",
        )
        vol_with_r5 = st_adj["scene"]["summary"]["volume"]
        self.assertGreater(vol_with_r5, vol_with_r10)
        self.assertLess(vol_with_r5, 48000.0)

        # Undo back to pure Box
        st_undo = self.ws.undo()
        self.assertAlmostEqual(st_undo["scene"]["summary"]["volume"], 48000.0, places=1)

        # Redo back to R=5 hole
        st_redo = self.ws.redo()
        self.assertAlmostEqual(st_redo["scene"]["summary"]["volume"], vol_with_r5, places=1)


if __name__ == "__main__":
    unittest.main()
