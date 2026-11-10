"""Feature registry tests: catalog shape, param and ref validation."""

from __future__ import annotations

import unittest

from cadwork.design import BuildCache, BuildError, build
from cadwork.design.document import Document, Feature, Ref
from cadwork.design.features import FEATURES, catalog, resolve_params


class CatalogTests(unittest.TestCase):
    def test_feature_types(self) -> None:
        self.assertEqual(len(FEATURES), 30)
        self.assertEqual(
            set(FEATURES),
            {"hub_revolve", "blade_loft", "pattern_circular", "boolean",
             "fillet", "tag_boundary", "cavity_extraction",
             "curve_spiral", "curve_helix", "profile_rect", "sweep", "shell",
             "solid_box", "solid_cylinder", "solid_cone", "solid_sphere",
             "profile_circle", "profile_polygon", "extrude", "revolve_profile",
             "transform", "pattern_linear", "mirror_part", "chamfer",
             "offset_solid", "split_part", "scale_part", "pattern_grid",
             "thicken_faces", "hole"},
        )

    def test_catalog_is_serialisable(self) -> None:
        import json

        payload = json.dumps(catalog())
        self.assertIn("hub_revolve", payload)

    def test_unknown_param_is_rejected(self) -> None:
        spec = FEATURES["hub_revolve"]
        with self.assertRaises(Exception) as caught:
            resolve_params(spec, {"r_outt": 1.0})
        self.assertEqual(caught.exception.code, "UNKNOWN_PARAM")

    def test_out_of_range_param_is_rejected(self) -> None:
        spec = FEATURES["pattern_circular"]
        with self.assertRaises(Exception) as caught:
            resolve_params(spec, {"count": 1})
        self.assertEqual(caught.exception.code, "INVALID_PARAM")

    def test_defaults_are_applied(self) -> None:
        spec = FEATURES["pattern_circular"]
        self.assertEqual(resolve_params(spec, {})["count"], 9)


class FeatureValidationTests(unittest.TestCase):
    def test_unknown_type_fails_at_build(self) -> None:
        document = Document(id="t", name="t", features=(Feature("f1", "nope"),))
        with self.assertRaises(BuildError) as caught:
            build(document, BuildCache())
        self.assertEqual(caught.exception.code, "UNKNOWN_FEATURE_TYPE")

    def test_missing_ref_role_fails_at_build(self) -> None:
        document = Document(id="t", name="t", features=(Feature("f1", "pattern_circular"),))
        with self.assertRaises(BuildError) as caught:
            build(document, BuildCache())
        self.assertEqual(caught.exception.code, "INVALID_REFS")

    def test_wrong_ref_kind_fails_at_build(self) -> None:
        document = Document(
            id="t", name="t",
            features=(
                Feature("f1", "hub_revolve"),
                Feature("f2", "pattern_circular",
                        refs={"target": Ref("f1", "faces")}),
            ),
        )
        with self.assertRaises(BuildError) as caught:
            build(document, BuildCache())
        self.assertEqual(caught.exception.code, "INVALID_REF_KIND")


if __name__ == "__main__":
    unittest.main()
