"""Stability test fixtures across parametric dimension sweeps (validating A1)."""

from __future__ import annotations

import unittest
from smlibpy import Box, Hole

from backend.selector.canonicalizer import canonicalize_face
from backend.selector.resolver import SelectorResolver


def make_flange(length: float, width: float, thickness: float, hole_radius: float) -> object:
    base = Box(length, width, thickness)
    top_f = list(base.faces().top())[0]
    hole = Hole(hole_radius, thickness * 2).on(top_f)
    return base - hole


class TestSelectorStability(unittest.TestCase):
    def test_parametric_sweep_semantic_preservation(self) -> None:
        params_list = [
            (60.0, 40.0, 20.0, 6.0),
            (80.0, 50.0, 25.0, 8.0),
            (100.0, 60.0, 15.0, 5.0),
            (70.0, 30.0, 10.0, 4.0),
            (90.0, 45.0, 18.0, 7.0),
        ]

        base_part = make_flange(*params_list[0])
        semantic_targets: list[tuple[str, str]] = [
            ("top_face", "faces().facing(Z)"),
            ("bottom_face", "faces().facing(-Z)"),
            ("front_face", "faces().facing(Y)"),
            ("back_face", "faces().facing(-Y)"),
            ("right_face", "faces().facing(X)"),
            ("left_face", "faces().facing(-X)"),
            ("hole_wall", "faces().cylinders()"),
            ("largest_planar", "faces().planar().largest()"),
            ("smallest_planar", "faces().planar().smallest()"),
        ]

        for name, expr in semantic_targets:
            res_base = SelectorResolver.resolve(base_part, expr)
            self.assertIsNotNone(res_base, f"Failed to resolve {name} on base part")

            for params in params_list[1:]:
                variant_part = make_flange(*params)
                res_variant = SelectorResolver.resolve(variant_part, expr)
                self.assertIsNotNone(res_variant, f"Failed to resolve {name} on variant {params}")
                if "facing" in expr:
                    self.assertTrue(res_variant.is_planar)
                elif "cylinders" in expr:
                    self.assertEqual(res_variant.geom_type, "cylinder")


if __name__ == "__main__":
    unittest.main()
