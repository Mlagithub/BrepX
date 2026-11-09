"""Unit tests for physical assertion handlers."""

from __future__ import annotations

import unittest
from smlibpy import Box

from backend.core.assertions import run
from backend.core.command import (
    Assertion,
    bbox_within,
    face_count_delta,
    is_solid,
    is_valid,
    no_degenerate_faces,
    volume_delta_sign,
    volume_gt,
)


class TestAssertions(unittest.TestCase):
    def setUp(self) -> None:
        self.box = Box(60, 40, 20)

    def test_valid_box_all_assertions_pass(self) -> None:
        assertions = (
            is_valid(),
            is_solid(),
            volume_gt(1000.0),
            volume_delta_sign(1),
            no_degenerate_faces(1e-4),
            bbox_within((-30.1, -20.1, -10.1, 30.1, 20.1, 10.1)),
        )
        failures = run(self.box, None, assertions)
        self.assertEqual(failures, [])

    def test_disjoint_boolean_subtraction_intercepted(self) -> None:
        box1 = Box(20, 20, 20)
        box_far = Box(10, 10, 10).translate(100, 100, 100)
        unaffected = box1 - box_far

        self.assertAlmostEqual(unaffected.volume, box1.volume)

        failures = run(unaffected, box1, (volume_delta_sign(-1),))
        self.assertEqual(len(failures), 1)
        self.assertIn("Expected volume decrease (-1)", failures[0])

    def test_unknown_assertion_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            run(self.box, None, (Assertion("unknown_custom_assertion"),))

    def test_volume_gt_failure(self) -> None:
        failures = run(self.box, None, (volume_gt(1000000.0),))
        self.assertEqual(len(failures), 1)
        self.assertIn("not strictly greater than", failures[0])

    def test_face_count_delta(self) -> None:
        smaller_box = Box(10, 10, 10)
        failures = run(self.box, smaller_box, (face_count_delta(0),))
        self.assertEqual(failures, [])

        failures_mismatch = run(self.box, smaller_box, (face_count_delta(2),))
        self.assertEqual(len(failures_mismatch), 1)
        self.assertIn("Face count delta mismatch", failures_mismatch[0])

    def test_bbox_overflow(self) -> None:
        failures = run(self.box, None, (bbox_within((0, 0, 0, 10, 10, 10)),))
        self.assertEqual(len(failures), 1)
        self.assertIn("overflows permitted region", failures[0])

    def test_none_geometry_safely_handled(self) -> None:
        failures = run(None, None, (is_valid(), is_solid()))
        self.assertEqual(len(failures), 2)


if __name__ == "__main__":
    unittest.main()
