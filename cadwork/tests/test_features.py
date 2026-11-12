"""Feature registry tests: generated actions, param coercion and ref validation."""

from __future__ import annotations

import json
import unittest

from cadwork.design import BuildCache, BuildError, build
from cadwork.design.document import Document, Feature, Ref
from cadwork.design.features import (
    FEATURES,
    FeatureError,
    Param,
    catalog,
    resolve_params,
    spec_for,
    validate_feature,
)


class CatalogTests(unittest.TestCase):
    def test_registry_is_the_generated_actions_plus_adapters(self) -> None:
        names = set(FEATURES)
        self.assertIn("k_box", names)
        self.assertIn("k_cylinder", names)
        self.assertIn("k_extrude", names)
        self.assertIn("pattern", names)
        self.assertIn("cavity", names)
        self.assertIn("tag_boundary", names)
        # The hand-written v1 types are gone: the kernel generates the steps.
        for old in ("hub_revolve", "blade_loft", "solid_box", "boolean",
                    "pattern_circular", "solid_cylinder"):
            self.assertNotIn(old, names)
        self.assertGreaterEqual(len(names), 90)

    def test_tiers_and_origins_are_declared(self) -> None:
        box = spec_for("k_box")
        self.assertEqual(box.tier, "kernel")
        self.assertTrue(box.origin.startswith("kernel:smlibpy."))
        self.assertEqual(box.return_kind, "part")
        pattern = spec_for("pattern")
        self.assertEqual(pattern.tier, "adapter")
        self.assertEqual(pattern.origin, "adapter:pattern")
        tag = spec_for("tag_boundary")
        self.assertEqual(tag.tier, "annotation")
        self.assertEqual(tag.return_kind, "same")
        cavity = spec_for("cavity")
        self.assertEqual(cavity.origin, "adapter:cavity")

    def test_catalog_is_serialisable_and_matches_the_registry(self) -> None:
        entries = catalog()
        payload = json.dumps(entries)
        self.assertIn('"k_box"', payload)
        self.assertIn('"pattern"', payload)
        self.assertIn('"cavity"', payload)
        self.assertEqual({entry["type"] for entry in entries}, set(FEATURES))
        box = next(entry for entry in entries if entry["type"] == "k_box")
        self.assertEqual(set(box["params"]), {"length", "width", "height"})
        self.assertTrue(box["params"]["length"]["required"])
        self.assertEqual(box["inputs"], [])

    def test_spec_for_unknown_is_none(self) -> None:
        self.assertIsNone(spec_for("no_such_action"))


class ParamCoercionTests(unittest.TestCase):
    def test_float_accepts_numbers_and_rejects_bool_and_infinity(self) -> None:
        param = Param("float")
        self.assertEqual(param.coerce("v", 3), 3.0)
        self.assertIsInstance(param.coerce("v", 3), float)
        with self.assertRaises(FeatureError) as caught:
            param.coerce("v", True)
        self.assertEqual(caught.exception.code, "INVALID_PARAM")
        with self.assertRaises(FeatureError):
            param.coerce("v", float("inf"))
        with self.assertRaises(FeatureError):
            param.coerce("v", "3")

    def test_int_accepts_whole_floats_and_rejects_fractions(self) -> None:
        param = Param("int")
        self.assertEqual(param.coerce("v", 3.0), 3)
        self.assertIs(type(param.coerce("v", 3.0)), int)
        with self.assertRaises(FeatureError):
            param.coerce("v", 3.5)
        with self.assertRaises(FeatureError):
            param.coerce("v", True)

    def test_bool_is_strict(self) -> None:
        param = Param("bool")
        self.assertIs(param.coerce("v", False), False)
        for bad in (1, 0, "true"):
            with self.assertRaises(FeatureError):
                param.coerce("v", bad)

    def test_enum_honours_choices(self) -> None:
        param = Param("enum", "XY", choices=("XY", "XZ", "YZ"))
        self.assertEqual(param.coerce("plane", "XZ"), "XZ")
        with self.assertRaises(FeatureError) as caught:
            param.coerce("plane", "AB")
        self.assertIn("XY", str(caught.exception))

    def test_vector_needs_three_numbers(self) -> None:
        param = Param("vector")
        self.assertEqual(param.coerce("v", (1, 2, 3)), [1.0, 2.0, 3.0])
        for bad in ([1, 2], [1, 2, 3, 4], ["a", 2, 3], [1, True, 3]):
            with self.assertRaises(FeatureError):
                param.coerce("v", bad)

    def test_points_accept_two_and_three_dimensional_points(self) -> None:
        param = Param("points")
        result = param.coerce("points", [[0, 0], (1.5, 2.5), [0.0, 0.0, 3.0]])
        self.assertEqual(result[0], [0.0, 0.0])
        self.assertEqual(result[1], [1.5, 2.5])
        self.assertEqual(result[2], [0.0, 0.0, 3.0])
        with self.assertRaises(FeatureError):
            param.coerce("points", [])
        with self.assertRaises(FeatureError):
            param.coerce("points", [[0, 0, 0, 0]])
        with self.assertRaises(FeatureError):
            param.coerce("points", [[0, "x"]])

    def test_required_param_has_no_default(self) -> None:
        param = Param("float", required=True)
        with self.assertRaises(FeatureError) as caught:
            param.coerce("amount", None)
        self.assertEqual(caught.exception.code, "INVALID_PARAM")
        self.assertIn("required", str(caught.exception))

    def test_bounds_are_enforced(self) -> None:
        param = Param("float", 1.0, minimum=0.0, maximum=2.0)
        self.assertEqual(param.coerce("v", 2.0), 2.0)
        with self.assertRaises(FeatureError) as low:
            param.coerce("v", -1.0)
        self.assertIn(">=", str(low.exception))
        with self.assertRaises(FeatureError) as high:
            param.coerce("v", 3.0)
        self.assertIn("<=", str(high.exception))


class RegistryParamTests(unittest.TestCase):
    def test_defaults_are_applied(self) -> None:
        spec = spec_for("pattern")
        resolved = resolve_params(spec, {})
        self.assertEqual(resolved["kind"], "circular")
        self.assertEqual(resolved["count"], 9)

    def test_unknown_param_is_rejected(self) -> None:
        with self.assertRaises(FeatureError) as caught:
            resolve_params(spec_for("k_box"), {"length": 1.0, "r_outt": 1.0})
        self.assertEqual(caught.exception.code, "UNKNOWN_PARAM")

    def test_required_param_is_enforced(self) -> None:
        with self.assertRaises(FeatureError) as caught:
            resolve_params(spec_for("k_box"), {"length": 1.0})
        self.assertEqual(caught.exception.code, "INVALID_PARAM")
        self.assertIn("width", str(caught.exception))

    def test_out_of_range_param_is_rejected(self) -> None:
        with self.assertRaises(FeatureError) as caught:
            resolve_params(spec_for("pattern"), {"count": 0})
        self.assertEqual(caught.exception.code, "INVALID_PARAM")

    def test_enum_choice_is_enforced(self) -> None:
        with self.assertRaises(FeatureError) as caught:
            resolve_params(spec_for("k_draft"), {"angle": 3.0, "neutral_plane": "AB"})
        self.assertEqual(caught.exception.code, "INVALID_PARAM")

    def test_points_param_is_required_for_polygon(self) -> None:
        with self.assertRaises(FeatureError) as caught:
            resolve_params(spec_for("k_polygon"), {})
        self.assertEqual(caught.exception.code, "INVALID_PARAM")
        resolved = resolve_params(spec_for("k_polygon"),
                                  {"points": [[0, 0], [10, 0], [10, 10]]})
        self.assertEqual(resolved["points"][1], [10.0, 0.0])


class InputRoleTests(unittest.TestCase):
    def test_many_and_optional_roles_are_declared(self) -> None:
        cut = spec_for("k_cut")
        roles = {role.role: role for role in cut.inputs}
        self.assertTrue(roles["others"].many)
        self.assertFalse(roles["others"].optional)
        shell = spec_for("k_shell")
        roles = {role.role: role for role in shell.inputs}
        self.assertTrue(roles["openings"].optional)
        self.assertFalse(roles["openings"].many)
        loft = spec_for("k_loft")
        self.assertTrue(loft.inputs[0].many)

    def test_optional_role_may_be_omitted(self) -> None:
        validate_feature("k_shell", {"target": Ref("f1", "self")})

    def test_missing_required_role_is_rejected(self) -> None:
        with self.assertRaises(FeatureError) as caught:
            validate_feature("pattern", {})
        self.assertEqual(caught.exception.code, "INVALID_REFS")

    def test_unexpected_role_is_rejected(self) -> None:
        with self.assertRaises(FeatureError) as caught:
            validate_feature("pattern", {"target": Ref("f1", "self"),
                                         "faces": Ref("f1", "faces")})
        self.assertEqual(caught.exception.code, "INVALID_REFS")

    def test_many_role_builds_from_two_bodies(self) -> None:
        document = Document(id="t", name="t", features=(
            Feature("c1", "k_cylinder", params={"radius": 5.0, "height": 20.0}),
            Feature("c2", "k_cylinder", params={"radius": 5.0, "height": 20.0}),
            Feature("c3", "k_translate", params={"x": 20.0},
                    refs={"target": Ref("c2", "self")}),
            Feature("b1", "k_box", params={"length": 20.0, "width": 20.0, "height": 20.0}),
            Feature("b2", "k_cut",
                    refs={"target": Ref("b1", "self"),
                          "others": (Ref("c1", "self"), Ref("c3", "self"))}),
        ))
        result = build(document, BuildCache())
        self.assertLess(float(result.final.volume), 8000.0)
        self.assertEqual(result.features[-1].feature_id, "b2")


class FeatureValidationTests(unittest.TestCase):
    def test_unknown_type_fails_at_build(self) -> None:
        document = Document(id="t", name="t", features=(Feature("f1", "nope"),))
        with self.assertRaises(BuildError) as caught:
            build(document, BuildCache())
        self.assertEqual(caught.exception.code, "UNKNOWN_FEATURE_TYPE")

    def test_unknown_param_fails_at_build(self) -> None:
        document = Document(id="t", name="t", features=(
            Feature("f1", "k_box",
                    params={"length": 1.0, "width": 1.0, "height": 1.0, "nope": 2}),
        ))
        with self.assertRaises(BuildError) as caught:
            build(document, BuildCache())
        self.assertEqual(caught.exception.code, "UNKNOWN_PARAM")

    def test_missing_ref_role_fails_at_build(self) -> None:
        document = Document(id="t", name="t", features=(Feature("f1", "pattern"),))
        with self.assertRaises(BuildError) as caught:
            build(document, BuildCache())
        self.assertEqual(caught.exception.code, "INVALID_REFS")

    def test_wrong_ref_kind_fails_at_build(self) -> None:
        document = Document(
            id="t", name="t",
            features=(
                Feature("f1", "k_box",
                        params={"length": 10.0, "width": 10.0, "height": 10.0}),
                Feature("f2", "pattern",
                        refs={"target": Ref("f1", "faces")}),
            ),
        )
        with self.assertRaises(BuildError) as caught:
            build(document, BuildCache())
        self.assertEqual(caught.exception.code, "INVALID_REF_KIND")


if __name__ == "__main__":
    unittest.main()
