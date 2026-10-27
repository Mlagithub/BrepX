"""Unit tests for WorkspaceSession and B-Rep topological graphic serialization."""

from __future__ import annotations

import unittest
from smlibpy import Box
from backend.workspace import WorkspaceSession, SecurityViolationError
from backend.brep_graphic import serialize_body
from backend.operators import build_operator_code


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

    def test_selection_sensitive_operators(self) -> None:
        # 1. Create Box
        code, lbl, rep = build_operator_code("box", {"length": 60, "width": 40, "height": 20})
        st = self.ws.execute_step(code, lbl, "box", replace_all=rep)
        self.assertEqual(st["scene"]["summary"]["faces_count"], 6)

        # 2. Fillet only specific selected edges (edge 0 and edge 1)
        code, lbl, _ = build_operator_code(
            "fillet",
            {"radius": 3.0},
            selections=["part.edges()[0]", "part.edges()[1]"],
            has_existing_part=True,
        )
        st_fillet = self.ws.execute_step(code, lbl, "fillet")
        self.assertLess(st_fillet["scene"]["summary"]["volume"], 48000.0)
        self.assertEqual(st_fillet["scene"]["summary"]["faces_count"], 8)

        # 3. Defeature: remove_fillets restores exact 6-face Box
        code, lbl, _ = build_operator_code("remove_fillets", {}, has_existing_part=True)
        st_unfillet = self.ws.execute_step(code, lbl, "remove_fillets")
        self.assertAlmostEqual(st_unfillet["scene"]["summary"]["volume"], 48000.0, places=1)
        self.assertEqual(st_unfillet["scene"]["summary"]["faces_count"], 6)

        # 4. Extrude on a specific selected face (e.g. face 0 by +10 mm)
        code, lbl, _ = build_operator_code(
            "extrude",
            {"height": 10.0, "mode": "join"},
            selections=["part.faces()[0]"],
            has_existing_part=True,
        )
        st_ext = self.ws.execute_step(code, lbl, "extrude")
        self.assertGreater(st_ext["scene"]["summary"]["volume"], 48000.0)

        # 5. Shell with selected opening face
        self.ws.undo()
        code, lbl, _ = build_operator_code(
            "shell",
            {"thickness": 2.0},
            selections=["part.faces()[0]"],
            has_existing_part=True,
        )
        st_shell = self.ws.execute_step(code, lbl, "shell")
        self.assertLess(st_shell["scene"]["summary"]["volume"], 20000.0)

    def test_cavity_extraction_manifold(self) -> None:
        """验证内流体域水密提取算子生成闭合流形实体"""
        code_init, _, _ = build_operator_code("box", {"length": 50, "width": 50, "height": 20})
        self.ws.execute_step(code_init, "init", replace_all=True)
        code_hole, _, _ = build_operator_code("hole", {"radius": 8.0, "depth": 30.0}, selections=["part.faces()[0]"], has_existing_part=True)
        self.ws.execute_step(code_hole, "hole")

        code_cavity, lbl, _ = build_operator_code("cavity_extraction", {}, has_existing_part=True)
        st_cavity = self.ws.execute_step(code_cavity, lbl, "cavity_extraction")
        part = self.ws.primary_part()
        self.assertIsNotNone(part)
        self.assertTrue(part.is_valid())
        self.assertGreater(st_cavity["scene"]["summary"]["volume"], 0.0)

    def test_draft_adaptive_neutral_plane(self) -> None:
        """验证拔模算子在中性面方向上的自适应求解与流形有效性"""
        code_init, _, _ = build_operator_code("box", {"length": 50, "width": 50, "height": 20})
        self.ws.execute_step(code_init, "init", replace_all=True)
        code_draft, lbl, _ = build_operator_code("draft", {"angle": 5.0}, selections=["part.faces()[0]"], has_existing_part=True)
        st_draft = self.ws.execute_step(code_draft, lbl, "draft")
        part = self.ws.primary_part()
        self.assertIsNotNone(part)
        self.assertTrue(part.is_valid())

    def test_remove_faces_resilience(self) -> None:
        """验证特征面消除算子在复杂边界下的容错求解与自愈"""
        code_init, _, _ = build_operator_code("box", {"length": 50, "width": 50, "height": 20})
        self.ws.execute_step(code_init, "init", replace_all=True)
        code_remove, lbl, _ = build_operator_code("remove_faces", {}, selections=["part.faces()[0]"], has_existing_part=True)
        st_remove = self.ws.execute_step(code_remove, lbl, "remove_faces")
        part = self.ws.primary_part()
        self.assertIsNotNone(part)
        self.assertTrue(part.is_valid())


if __name__ == "__main__":
    unittest.main()
