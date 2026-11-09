"""Unit tests for pattern, transformation, and boolean operators."""

from __future__ import annotations

import unittest
from smlibpy import Box, Cylinder

from backend.kernel import ops_patterns, ops_transforms
from backend.kernel.registry import default_registry


class TestOpsPatterns(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = default_registry()

    def test_transformations_translate_rotate_scale(self) -> None:
        box = Box(10, 10, 10)
        t = ops_transforms.op_translate(box, None, None, {"dx": 10.0, "dy": 0.0, "dz": 0.0})
        self.assertTrue(t.is_valid())
        self.assertAlmostEqual(t.volume, box.volume)

        r = ops_transforms.op_rotate(box, None, None, {"angle": 90.0, "axis": "Z"})
        self.assertTrue(r.is_valid())

        s = ops_transforms.op_scale(box, None, None, {"factor": 2.0})
        self.assertTrue(s.is_valid())
        self.assertAlmostEqual(s.volume, box.volume * 8.0, delta=1e-3)

    def test_booleans_and_arrays(self) -> None:
        box = Box(20, 20, 20)
        cyl = Cylinder(5, 30).translate(0, 0, -5)

        cut = ops_patterns.op_boolean_cut(box, None, cyl, {})
        self.assertTrue(cut.is_valid())
        self.assertLess(cut.volume, box.volume)

        join = ops_patterns.op_boolean_join(box, None, cyl, {})
        self.assertTrue(join.is_valid())
        self.assertGreater(join.volume, box.volume)

        inter = ops_patterns.op_boolean_intersect(box, None, cyl, {})
        self.assertTrue(inter.is_valid())
        self.assertLess(inter.volume, box.volume)

        polar = ops_patterns.op_polar_array(box, None, None, {"count": 4, "axis": "Z", "total_angle": 360.0})
        self.assertTrue(polar.is_valid())


if __name__ == "__main__":
    unittest.main()
