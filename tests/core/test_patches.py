"""Unit tests for CFD boundary patches, store management, and rebinding."""

from __future__ import annotations

import unittest
from smlibpy import Box, Hole

from backend.core.assertions import run as run_assertions
from backend.core.command import Assertion
from backend.core.patches import BoundaryPatch, PatchStore, create_patch, rebind


class TestPatches(unittest.TestCase):
    def setUp(self) -> None:
        self.box = Box(60, 40, 20)
        self.store = PatchStore()

    def test_patch_creation_and_color_assignment(self) -> None:
        p1 = create_patch("p1", "inlet_1", "inlet", "faces().facing(Z)", area=2400.0)
        self.assertEqual(p1.color_hex, "#3a86ff")
        self.assertEqual(p1.area, 2400.0)
        self.assertEqual(p1.to_dict()["name"], "inlet_1")

        with self.assertRaises(ValueError):
            BoundaryPatch(
                patch_id="p_bad",
                name="bad",
                semantic_type="invalid_type",
                selector_expr="faces().top()",
                color_hex="#ffffff",
            )

    def test_patch_store_crud_and_deduplication(self) -> None:
        p1 = create_patch("p1", "inlet_1", "inlet", "faces().facing(Z)")
        self.store.add(p1)
        self.assertEqual(len(self.store), 1)

        # Adding another patch targeting the exact same face should override old patch
        p2 = create_patch("p2", "wall_1", "wall", "faces().facing(Z)")
        self.store.add(p2)
        self.assertEqual(len(self.store), 1)
        self.assertEqual(self.store.all()[0].name, "wall_1")

        self.store.remove("p2")
        self.assertEqual(len(self.store), 0)

    def test_rebind_updates_area_on_dimensional_change(self) -> None:
        p_top = create_patch("p1", "inlet_top", "inlet", "faces().facing(Z)")
        self.store.add(p_top)

        # Initial area on 60x40x20
        store_rebound, fails = rebind(self.store, self.box)
        self.assertEqual(fails, [])
        self.assertAlmostEqual(store_rebound.all()[0].area, 2400.0, delta=1e-3)

        # Larger box 100x50x20 -> area becomes 5000
        box_larger = Box(100, 50, 20)
        store_rebound_large, fails_large = rebind(self.store, box_larger)
        self.assertEqual(fails_large, [])
        self.assertAlmostEqual(store_rebound_large.all()[0].area, 5000.0, delta=1e-3)

    def test_rebind_tracks_lost_patches_without_crashing(self) -> None:
        p_cylinder = create_patch("p_cyl", "fluid_bore", "wall", "faces().cylinders()")
        self.store.add(p_cylinder)

        store_rebound, fails = rebind(self.store, self.box)
        self.assertIn("fluid_bore", fails)
        self.assertEqual(len(store_rebound), 1)

    def test_patches_preserved_assertion(self) -> None:
        p_top = create_patch("p1", "inlet_top", "inlet", "faces().facing(Z)")
        self.store.add(p_top)

        failures = run_assertions(self.box, None, (Assertion("patches_preserved", (self.store,)),))
        self.assertEqual(failures, [])

        p_cyl = create_patch("p2", "inlet_bore", "wall", "faces().cylinders()")
        self.store.add(p_cyl)
        failures_lost = run_assertions(self.box, None, (Assertion("patches_preserved", (self.store,)),))
        self.assertEqual(len(failures_lost), 1)
        self.assertIn("Boundary patches lost during operation", failures_lost[0])


if __name__ == "__main__":
    unittest.main()
