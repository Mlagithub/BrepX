"""Interface contracts and configuration lookup for part documents."""

from __future__ import annotations

import unittest
from dataclasses import replace

from cadwork.design import BuildCache, build
from cadwork.design.document import (
    DocumentError,
    Interface,
    apply_ops,
    document_from_json,
    document_to_json,
    interface_compatibility,
    new_document,
)


class InterfaceCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        document = new_document("interfaces", "d_interfaces")
        self.document = apply_ops(
            document,
            [
                {
                    "op": "add",
                    "feature": {
                        "id": "base",
                        "type": "k_box",
                        "params": {"length": 20.0, "width": 10.0, "height": 5.0},
                    },
                }
            ],
        )

    def test_document_lookup_and_json(self) -> None:
        document = replace(
            self.document,
            interfaces=(
                Interface("shaft", "axis", "base", {"direction": [0.0, 0.0, 1.0]}),
                Interface(
                    "bolt",
                    "bolt_pattern",
                    "base",
                    {"count": 8, "diameter": 8.4, "circle_radius": 45.0},
                ),
            ),
        )
        self.assertEqual(document.interface("shaft").kind, "axis")
        restored = document_from_json(document_to_json(document))
        self.assertEqual(restored.interface("bolt").params["count"], 8)
        with self.assertRaises(DocumentError):
            document.interface("missing")

    def test_axis_direction_compatibility(self) -> None:
        left = Interface("a", "axis", "base", {"direction": [0.0, 0.0, 2.0]})
        right = Interface("b", "axis", "base", {"direction": [0.0, 0.0, -3.0]})
        compatible, reasons = interface_compatibility(left, right)
        self.assertTrue(compatible)
        self.assertEqual(reasons, ())
        skew = Interface("c", "axis", "base", {"direction": [0.0, 1.0, 0.0]})
        compatible, reasons = interface_compatibility(left, skew)
        self.assertFalse(compatible)
        self.assertEqual(reasons, ("direction is not parallel",))

    def test_bolt_pattern_compatibility(self) -> None:
        left = Interface(
            "a",
            "bolt_pattern",
            "base",
            {"count": 8, "diameter": 8.4, "circle_radius": 45.0},
        )
        right = Interface(
            "b",
            "bolt_pattern",
            "base",
            {"count": 8, "diameter": 8.4, "circle_radius": 45.0},
        )
        self.assertEqual(interface_compatibility(left, right), (True, ()))
        different = Interface(
            "c",
            "bolt_pattern",
            "base",
            {"count": 12, "diameter": 6.6, "circle_radius": 45.0},
        )
        compatible, reasons = interface_compatibility(left, different)
        self.assertFalse(compatible)
        self.assertIn("count 8 != 12", reasons)
        self.assertIn("diameter 8.4 != 6.6", reasons)

    def test_kind_mismatch(self) -> None:
        axis = Interface("a", "axis", "base", {"direction": [0.0, 0.0, 1.0]})
        plane = Interface("b", "plane", "base", {"normal": [0.0, 0.0, 1.0]})
        compatible, reasons = interface_compatibility(axis, plane)
        self.assertFalse(compatible)
        self.assertIn("kind", reasons[0])

    def test_invalid_interface_values(self) -> None:
        with self.assertRaises(DocumentError):
            Interface("bad", "axis", "base", {"direction": [0.0, 0.0, 0.0]})
        with self.assertRaises(DocumentError):
            Interface("bad", "bolt_pattern", "base", {"count": 0})
        with self.assertRaises(DocumentError):
            Interface("bad", "plane", "base", {"normal": [0.0, 0.0, 0.0]})

    def test_configuration_lookup_and_build(self) -> None:
        document = replace(
            self.document,
            configurations={"long": {"base": {"length": 40.0}}},
        )
        self.assertEqual(document.configuration("default"), {})
        self.assertEqual(document.configuration("long")["base"]["length"], 40.0)
        with self.assertRaises(DocumentError):
            document.configuration("missing")
        default = build(document, BuildCache())
        long = build(document, BuildCache(), configuration="long")
        self.assertAlmostEqual(
            float(long.final.volume), 2 * float(default.final.volume)
        )


if __name__ == "__main__":
    unittest.main()
