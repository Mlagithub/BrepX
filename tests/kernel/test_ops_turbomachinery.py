"""Unit tests for turbomachinery domain operators (volute, blade_runner)."""

from __future__ import annotations

import unittest

from backend.core.errors import PreconditionError
from backend.kernel import ops_turbomachinery
from backend.kernel.registry import default_registry


class TestOpsTurbomachinery(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = default_registry()

    def test_volute_generation_and_validity(self) -> None:
        volute = ops_turbomachinery.op_volute(
            None,
            None,
            None,
            {
                "base_radius": 40.0,
                "spiral_k": 0.18,
                "turns": 1.0,
                "throat_radius": 12.0,
                "height": 30.0,
            },
        )
        self.assertTrue(volute.is_valid())
        self.assertGreater(volute.volume, 0)

        with self.assertRaises(PreconditionError):
            ops_turbomachinery.op_volute(
                None, None, None, {"base_radius": -10.0, "throat_radius": 12.0}
            )

    def test_blade_runner_generation_and_blade_count_scaling(self) -> None:
        runner_6 = ops_turbomachinery.op_blade_runner(
            None,
            None,
            None,
            {
                "hub_radius": 20.0,
                "tip_radius": 45.0,
                "height": 25.0,
                "blade_count": 6,
                "twist_deg": 25.0,
                "thickness": 3.0,
            },
        )
        self.assertTrue(runner_6.is_valid())
        faces_6 = len(list(runner_6.faces()))
        self.assertGreater(faces_6, 20)

        runner_3 = ops_turbomachinery.op_blade_runner(
            None,
            None,
            None,
            {
                "hub_radius": 20.0,
                "tip_radius": 45.0,
                "height": 25.0,
                "blade_count": 3,
                "twist_deg": 25.0,
                "thickness": 3.0,
            },
        )
        self.assertTrue(runner_3.is_valid())
        faces_3 = len(list(runner_3.faces()))
        self.assertLess(faces_3, faces_6)

        with self.assertRaises(PreconditionError):
            ops_turbomachinery.op_blade_runner(
                None, None, None, {"hub_radius": 50.0, "tip_radius": 20.0}
            )


if __name__ == "__main__":
    unittest.main()
