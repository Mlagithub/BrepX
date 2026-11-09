"""Unit tests for advanced geometric features (revolve, draft, offset, etc.)."""

from __future__ import annotations

import unittest
from smlibpy import Box, Plane, Rectangle, X, Z

from backend.core.errors import PreconditionError
from backend.kernel import ops_features, ops_surfaces
from backend.kernel.registry import default_registry


class TestOpsFeatures(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = default_registry()

    def test_revolve_and_draft_operators(self) -> None:
        rect = Rectangle(10, 20).on(Plane.XZ).translate(15, 0, 0)
        rev = ops_surfaces.op_revolve(rect, None, None, {"angle": 360.0, "axis": "Z"})
        self.assertTrue(rev.is_valid())
        self.assertGreater(rev.volume, 0)

        box = Box(20, 20, 20)
        side_face = list(box.faces().facing(X))[0]
        drafted = ops_surfaces.op_draft(box, side_face, None, {"angle": 5.0, "neutral_plane": "XY"})
        self.assertTrue(drafted.is_valid())

    def test_offset_operator(self) -> None:
        box = Box(20, 20, 20)
        expanded = ops_surfaces.op_offset(box, None, None, {"distance": 2.0})
        self.assertTrue(expanded.is_valid())
        self.assertGreater(expanded.volume, box.volume)

        with self.assertRaises(PreconditionError):
            ops_surfaces.op_offset(box, None, None, {"distance": 0.0})


if __name__ == "__main__":
    unittest.main()
