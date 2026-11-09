"""Unit tests for CFD defeaturing and cavity extraction operators."""

from __future__ import annotations

import unittest
from smlibpy import Box, Cylinder, Hole, Z

from backend.kernel import ops_cfd, ops_features
from backend.kernel.registry import default_registry


class TestOpsCFD(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = default_registry()

    def test_remove_faces_and_heal(self) -> None:
        box = Box(40, 40, 20)
        top_f = list(box.faces().top())[0]
        holed = ops_features.op_hole(box, top_f, None, {"radius": 4.0, "depth": 20.0})
        self.assertEqual(len(list(holed.faces())), 7)

        cyl_face = list(holed.faces().cylinders())[0]
        healed = ops_cfd.op_remove_faces(holed, cyl_face, None, {})
        self.assertTrue(healed.is_valid())
        self.assertEqual(len(list(healed.faces())), 6)
        self.assertAlmostEqual(healed.volume, box.volume, delta=1e-3)

        healed_again = ops_cfd.op_heal(healed, None, None, {})
        self.assertTrue(healed_again.is_valid())

    def test_remove_fillets(self) -> None:
        box = Box(40, 40, 20)
        edge = list(box.edges().parallel_to(Z))[0]
        filleted = ops_features.op_fillet(box, edge, None, {"radius": 2.0})
        self.assertEqual(len(list(filleted.faces())), 7)

        unfilleted = ops_cfd.op_remove_fillets(filleted, None, None, {})
        self.assertTrue(unfilleted.is_valid())
        self.assertEqual(len(list(unfilleted.faces())), 6)


if __name__ == "__main__":
    unittest.main()
