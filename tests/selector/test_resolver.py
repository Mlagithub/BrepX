"""Unit tests for topological selector resolver and ambiguity checking."""

from __future__ import annotations

import unittest
from smlibpy import Box, Cylinder

from backend.selector.errors import SelectorResolutionError
from backend.selector.resolver import SelectorResolver


class TestSelectorResolver(unittest.TestCase):
    def setUp(self) -> None:
        self.box = Box(60, 40, 20)
        self.cyl = Cylinder(20, 50)

    def test_box_unique_resolution(self) -> None:
        top_face = SelectorResolver.resolve(self.box, "faces().top()")
        self.assertIsNotNone(top_face)

        bottom_face = SelectorResolver.resolve(self.box, "faces().bottom()")
        self.assertIsNotNone(bottom_face)

        facing_z = SelectorResolver.resolve(self.box, "faces().facing(Z)")
        self.assertIsNotNone(facing_z)

        facing_neg_z = SelectorResolver.resolve(self.box, "faces().facing(-Z)")
        self.assertIsNotNone(facing_neg_z)

        facing_x = SelectorResolver.resolve(self.box, "faces().facing(X)")
        self.assertIsNotNone(facing_x)

    def test_cylinder_unique_resolution(self) -> None:
        cyl_face = SelectorResolver.resolve(self.cyl, "faces().cylinders()")
        self.assertIsNotNone(cyl_face)

        top_planar = SelectorResolver.resolve(self.cyl, "faces().planar().top()")
        self.assertIsNotNone(top_planar)

    def test_ambiguity_raises_error_with_candidates(self) -> None:
        with self.assertRaises(SelectorResolutionError) as ctx:
            SelectorResolver.resolve(self.box, "faces().planar()")
        self.assertEqual(ctx.exception.reason, "ambiguous")
        self.assertGreater(len(ctx.exception.candidates), 1)

    def test_syntax_and_unsupported_errors(self) -> None:
        with self.assertRaises(SelectorResolutionError) as ctx:
            SelectorResolver.resolve(self.box, "invalid_root()")
        self.assertEqual(ctx.exception.reason, "unsupported")

        with self.assertRaises(SelectorResolutionError) as ctx:
            SelectorResolver.resolve(self.box, "faces().facing(INVALID_AXIS)")
        self.assertEqual(ctx.exception.reason, "bad_syntax")

        with self.assertRaises(SelectorResolutionError) as ctx:
            SelectorResolver.resolve(self.box, "faces().parallel_to(Z)")
        self.assertEqual(ctx.exception.reason, "unsupported")

        with self.assertRaises(SelectorResolutionError) as ctx:
            SelectorResolver.resolve(self.box, "faces(unmatched_parentheses")
        self.assertEqual(ctx.exception.reason, "bad_syntax")

    def test_no_match_scenario(self) -> None:
        with self.assertRaises(SelectorResolutionError) as ctx:
            SelectorResolver.resolve(self.box, "faces().cylinders()")
        self.assertEqual(ctx.exception.reason, "no_match")


if __name__ == "__main__":
    unittest.main()
