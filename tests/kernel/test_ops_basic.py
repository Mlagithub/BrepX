"""Unit tests for basic geometric operators (primitives and features)."""

from __future__ import annotations

import unittest
from smlibpy import Box, Cylinder, Z

from backend.core.errors import PreconditionError
from backend.kernel import ops_features, ops_primitives, smlib_bridge
from backend.kernel.registry import default_registry


class TestOpsBasic(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = default_registry()

    def test_all_operator_specs_have_six_sections(self) -> None:
        ops = ["box", "cylinder", "extrude", "hole", "fillet", "chamfer", "shell"]
        required_keys = ("用途", "场景", "区别", "参数", "约束", "示例")
        for op in ops:
            spec = self.registry.get(op)
            for key in required_keys:
                self.assertIn(key, spec.doc, f"Operator '{op}' doc missing section '{key}'")

    def test_box_and_cylinder_primitives(self) -> None:
        box = ops_primitives.op_box(None, None, None, {"length": 60.0, "width": 40.0, "height": 20.0})
        self.assertTrue(box.is_valid())
        self.assertAlmostEqual(box.volume, 48000.0, delta=1e-3)

        cyl = ops_primitives.op_cylinder(None, None, None, {"radius": 20.0, "height": 50.0})
        self.assertTrue(cyl.is_valid())
        self.assertGreater(cyl.volume, 0)

    def test_hole_reduces_volume(self) -> None:
        box = Box(60, 40, 20)
        top_face = list(box.faces().top())[0]
        holed = ops_features.op_hole(box, top_face, None, {"radius": 6.0, "depth": 40.0})
        self.assertTrue(holed.is_valid())
        self.assertLess(holed.volume, box.volume)

    def test_hole_on_non_planar_face_raises_precondition_error(self) -> None:
        cyl = Cylinder(20, 50)
        side_face = list(cyl.faces().cylinders())[0]
        with self.assertRaises(PreconditionError) as ctx:
            ops_features.op_hole(cyl, side_face, None, {"radius": 4.0, "depth": 10.0})
        self.assertIn("非平面面不可贴合", ctx.exception.reason)

    def test_extrude_positive_and_negative(self) -> None:
        box = Box(60, 40, 20)
        top_face = list(box.faces().top())[0]

        boss = ops_features.op_extrude(box, top_face, None, {"height": 10.0})
        self.assertTrue(boss.is_valid())
        self.assertGreater(boss.volume, box.volume)

        cut = ops_features.op_extrude(box, top_face, None, {"height": -5.0})
        self.assertTrue(cut.is_valid())
        self.assertLess(cut.volume, box.volume)

    def test_fillet_and_chamfer(self) -> None:
        box = Box(60, 40, 20)
        edge = list(box.edges().parallel_to(Z))[0]

        filleted = ops_features.op_fillet(box, edge, None, {"radius": 4.0})
        self.assertTrue(filleted.is_valid())

        chamfered = ops_features.op_chamfer(box, edge, None, {"distance": 3.0})
        self.assertTrue(chamfered.is_valid())

    def test_fillet_excessive_radius_raises_kernel_error(self) -> None:
        box = Box(60, 40, 20)
        edge = list(box.edges().parallel_to(Z))[0]
        with self.assertRaises(smlib_bridge.KernelError):
            ops_features.op_fillet(box, edge, None, {"radius": 1000.0})

    def test_shell_operator(self) -> None:
        box = Box(60, 40, 20)
        top_face = list(box.faces().top())[0]
        shelled = ops_features.op_shell(box, top_face, None, {"thickness": 2.0})
        self.assertTrue(shelled.is_valid())
        self.assertLess(shelled.volume, box.volume)


if __name__ == "__main__":
    unittest.main()
