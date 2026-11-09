"""Unit tests for complete set of 3D geometric primitive operators."""

from __future__ import annotations

import unittest

from backend.core.errors import PreconditionError
from backend.kernel import ops_primitives
from backend.kernel.registry import default_registry


class TestOpsPrimitives(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = default_registry()

    def test_all_six_primitives_have_six_sections(self) -> None:
        primitives = ["box", "cylinder", "sphere", "cone", "torus", "wedge"]
        required_keys = ("用途", "场景", "区别", "参数", "约束", "示例")
        for op in primitives:
            spec = self.registry.get(op)
            for k in required_keys:
                self.assertIn(k, spec.doc, f"Primitive '{op}' doc missing '{k}'")

    def test_sphere_operator(self) -> None:
        sphere = ops_primitives.op_sphere(None, None, None, {"radius": 25.0})
        self.assertTrue(sphere.is_valid())
        self.assertAlmostEqual(sphere.volume, (4.0 / 3.0) * 3.1415926535 * (25.0**3), delta=50.0)

    def test_cone_operator(self) -> None:
        cone = ops_primitives.op_cone(None, None, None, {"radius1": 20.0, "radius2": 10.0, "height": 40.0})
        self.assertTrue(cone.is_valid())
        self.assertGreater(cone.volume, 0)

    def test_torus_operator_and_constraint(self) -> None:
        torus = ops_primitives.op_torus(None, None, None, {"radius_major": 30.0, "radius_minor": 8.0})
        self.assertTrue(torus.is_valid())
        self.assertGreater(torus.volume, 0)

        with self.assertRaises(PreconditionError):
            ops_primitives.op_torus(None, None, None, {"radius_major": 10.0, "radius_minor": 15.0})

    def test_wedge_operator_and_constraint(self) -> None:
        wedge = ops_primitives.op_wedge(None, None, None, {"length": 60.0, "width": 40.0, "height": 25.0, "top_length": 20.0})
        self.assertTrue(wedge.is_valid())
        self.assertEqual(wedge.volume, 40000.0)

        with self.assertRaises(PreconditionError):
            ops_primitives.op_wedge(None, None, None, {"length": 30.0, "width": 20.0, "height": 10.0, "top_length": 50.0})


if __name__ == "__main__":
    unittest.main()
