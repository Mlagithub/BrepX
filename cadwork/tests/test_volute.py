"""The volute proves the registry is general: no step knows the part name."""

from __future__ import annotations

import unittest

from cadwork.design import build
from cadwork.design.features import FEATURES
from cadwork.samples.volute import volute_document


class VoluteTests(unittest.TestCase):
    def test_builds_from_generic_steps_only(self) -> None:
        document = volute_document()
        result = build(document)

        self.assertEqual(
            [item.feature_id for item in result.features],
            ["spiral", "section", "sweep", "shell"],
        )
        checks = [check for item in result.features for check in item.checks]
        self.assertEqual(len(checks), 10)
        self.assertTrue(all(check.ok for check in checks))
        final = result.final
        self.assertTrue(final.is_valid())
        self.assertTrue(final.mesh().is_closed())
        self.assertEqual(len(final.faces()), 12)
        self.assertAlmostEqual(float(final.volume), 13458.29, delta=10.0)

    def test_registry_has_no_part_specific_step(self) -> None:
        for name, spec in FEATURES.items():
            self.assertNotIn("volute", name)
            self.assertNotIn("volute", spec.summary.lower())

    def test_wall_too_thick_fails_the_build(self) -> None:
        document = volute_document(wall=6.0)
        with self.assertRaises(Exception) as caught:
            build(document)
        self.assertIn("shell", str(caught.exception).lower())


if __name__ == "__main__":
    unittest.main()
