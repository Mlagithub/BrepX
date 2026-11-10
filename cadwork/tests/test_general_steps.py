"""The general vocabulary: primitives, profiles, form, place, pattern, modify.

Each test builds a tiny document from the public step registry — no sample, no
framework shortcut — so a broken step fails here rather than in a part file.
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from cadwork.design import BuildError, build
from cadwork.design.document import Document, Feature, Filter, Ref
from cadwork.design.features import FEATURES, INPUT_KINDS, register_input_kind


def _build(*features: Feature):
    return build(Document(id="t", name="t", features=features))


def _box(x: float = 0.0) -> Feature:
    return Feature("x1", "solid_box",
                   params={"length": 20.0, "width": 20.0, "height": 20.0, "x": x})


class PrimitiveTests(unittest.TestCase):
    def test_each_primitive_builds_a_closed_solid(self) -> None:
        for type_name in ("solid_box", "solid_cylinder", "solid_cone", "solid_sphere"):
            result = _build(Feature("x1", type_name))
            final = result.final
            self.assertTrue(final.is_valid(), type_name)
            self.assertTrue(final.mesh().is_closed(), type_name)
            self.assertGreater(float(final.volume), 0.0, type_name)

    def test_placement_moves_the_body(self) -> None:
        near = _build(_box(0.0)).final.mesh().vertices[:, 0].max()
        far = _build(_box(100.0)).final.mesh().vertices[:, 0].max()
        self.assertAlmostEqual(float(far - near), 100.0, places=3)


class ProfileAndFormTests(unittest.TestCase):
    def test_circle_extrudes_to_a_solid(self) -> None:
        result = _build(
            Feature("x1", "profile_circle", params={"radius": 10.0}),
            Feature("x2", "extrude", params={"amount": 12.0},
                    refs={"profile": Ref("x1", "self")}),
        )
        final = result.final
        self.assertTrue(final.mesh().is_closed())
        # 10 mm radius over 12 mm: 3769.9 mm³
        self.assertAlmostEqual(float(final.volume), 3.14159265 * 100 * 12, delta=5.0)

    def test_polygon_revolve_about_the_axis(self) -> None:
        # A 4×10 rectangle at y=25, revolved about X: a tube of radii 20..30,
        # 4 mm long. The profile must sit beside the axis, not across it.
        result = _build(
            Feature("x1", "profile_rect",
                    params={"width": 4.0, "height": 10.0, "y": 25.0}),
            Feature("x2", "revolve_profile", params={"axis": "X", "angle": 360.0},
                    refs={"profile": Ref("x1", "self")}),
        )
        self.assertTrue(result.final.mesh().is_closed())
        expected = 3.14159265 * (30 ** 2 - 20 ** 2) * 4
        self.assertAlmostEqual(float(result.final.volume), expected, delta=expected * 0.01)


class PlacementTests(unittest.TestCase):
    def test_transform_rotates_then_moves(self) -> None:
        base = _build(Feature("x1", "solid_box",
                              params={"length": 40.0, "width": 10.0, "height": 10.0})).final
        moved = _build(
            Feature("x1", "solid_box",
                    params={"length": 40.0, "width": 10.0, "height": 10.0}),
            Feature("x2", "transform", params={"rz": 90.0, "dx": 100.0},
                    refs={"target": Ref("x1", "self")}),
        ).final
        self.assertAlmostEqual(float(moved.volume), float(base.volume), delta=1.0)
        self.assertAlmostEqual(float(moved.mesh().vertices[:, 0].max()), 100.0 + 5.0, delta=0.5)

    def test_linear_pattern_repeats_the_body(self) -> None:
        result = _build(
            _box(),
            Feature("x2", "pattern_linear", params={"count": 4, "dx": 30.0},
                    refs={"target": Ref("x1", "self")}),
        )
        final = result.final
        self.assertEqual(len(final.solids()), 4)
        self.assertAlmostEqual(float(final.volume), 8000.0 * 4, delta=40.0)

    def test_mirror_preserves_volume(self) -> None:
        result = _build(
            _box(40.0),
            Feature("x2", "mirror_part", params={"plane": "YZ"},
                    refs={"target": Ref("x1", "self")}),
        )
        self.assertAlmostEqual(float(result.final.volume), 8000.0, delta=1.0)
        self.assertLess(float(result.final.mesh().vertices[:, 0].min()), 0.0)


class SolidEditTests(unittest.TestCase):
    def test_offset_grows_the_body(self) -> None:
        result = _build(
            _box(),
            Feature("x2", "offset_solid", params={"distance": 2.0},
                    refs={"target": Ref("x1", "self")}),
        )
        self.assertTrue(result.final.mesh().is_closed())
        self.assertGreater(float(result.final.volume), 8000.0)

    def test_split_keeps_one_side(self) -> None:
        result = _build(
            Feature("x1", "solid_box",
                    params={"length": 40.0, "width": 20.0, "height": 10.0}),
            Feature("x2", "split_part", params={"plane": "XY", "keep": "above"},
                    refs={"target": Ref("x1", "self")}),
        )
        self.assertAlmostEqual(float(result.final.volume), 4000.0, delta=20.0)

    def test_scale_cubes_the_volume(self) -> None:
        result = _build(
            _box(),
            Feature("x2", "scale_part", params={"factor": 1.5},
                    refs={"target": Ref("x1", "self")}),
        )
        self.assertAlmostEqual(float(result.final.volume), 27000.0, delta=100.0)

    def test_grid_pattern_counts_solids(self) -> None:
        result = _build(
            _box(),
            Feature("x2", "pattern_grid", params={"x_count": 2, "y_count": 3},
                    refs={"target": Ref("x1", "self")}),
        )
        self.assertEqual(len(result.final.solids()), 6)

    def test_thicken_turns_a_face_into_a_solid(self) -> None:
        result = _build(
            Feature("x1", "solid_box",
                    params={"length": 30.0, "width": 20.0, "height": 10.0}),
            Feature("x2", "thicken_faces", params={"thickness": 3.0},
                    refs={"faces": Ref("x1", "faces",
                                       (Filter("nearest", args=([0.0, 0.0, 5.0],)),))}),
        )
        final = result.final
        self.assertTrue(final.mesh().is_closed())
        self.assertAlmostEqual(float(final.volume), 1800.0, delta=20.0)


class OptionalInputTests(unittest.TestCase):
    def test_closed_shell_without_openings(self) -> None:
        result = _build(_box(), Feature("x2", "shell", params={"thickness": 2.0},
                                        refs={"target": Ref("x1", "self")}))
        self.assertTrue(result.final.mesh().is_closed())
        self.assertLess(float(result.final.volume), 8000.0)

    def test_openings_remove_the_named_face(self) -> None:
        closed = _build(_box(), Feature("x2", "shell", params={"thickness": 2.0},
                                        refs={"target": Ref("x1", "self")})).final
        opened = _build(
            _box(),
            Feature("x2", "shell", params={"thickness": 2.0},
                    refs={"target": Ref("x1", "self"),
                          "openings": Ref("x1", "faces",
                                          (Filter("nearest", args=([0.0, 0.0, 10.0],)),))}),
        ).final
        self.assertLess(float(opened.volume), float(closed.volume))

    def test_missing_required_role_still_fails(self) -> None:
        with self.assertRaises(BuildError) as caught:
            _build(_box(), Feature("x2", "chamfer", params={"length": 1.0},
                                   refs={"target": Ref("x1", "self")}))
        self.assertEqual(caught.exception.code, "INVALID_REFS")


class HoleTests(unittest.TestCase):
    def test_through_hole_removes_a_cylinder(self) -> None:
        result = _build(
            _box(),
            Feature("x2", "hole", params={"diameter": 10.0, "depth": 0.0},
                    refs={"target": Ref("x1", "self")}),
        )
        expected = 8000.0 - 3.14159265 * 25 * 20
        self.assertTrue(result.final.mesh().is_closed())
        self.assertAlmostEqual(float(result.final.volume), expected, delta=expected * 0.02)

    def test_blind_hole_removes_less(self) -> None:
        blind = _build(
            _box(),
            Feature("x2", "hole", params={"diameter": 10.0, "depth": 6.0},
                    refs={"target": Ref("x1", "self")}),
        )
        self.assertLess(float(blind.final.volume), 8000.0)
        self.assertGreater(float(blind.final.volume), 8000.0 - 3.14159265 * 25 * 7)

    def test_counterbore_removes_more_than_a_plain_hole(self) -> None:
        def build_with(kind: str):
            return _build(
                _box(),
                Feature("x2", "hole",
                        params={"diameter": 10.0, "depth": 0.0, "kind": kind,
                                "cb_diameter": 16.0, "cb_depth": 5.0},
                        refs={"target": Ref("x1", "self")}),
            ).final

        plain = build_with("simple")
        counterbore = build_with("counterbore")
        self.assertLess(float(counterbore.volume), float(plain.volume))
        extra = 3.14159265 * (8 ** 2 - 5 ** 2) * 5
        self.assertAlmostEqual(float(plain.volume) - float(counterbore.volume), extra,
                               delta=extra * 0.1)


class InputKindTests(unittest.TestCase):
    def test_every_declared_kind_is_registered(self) -> None:
        for spec in FEATURES.values():
            for role, kind in spec.inputs:
                self.assertIn(kind, INPUT_KINDS, f"{spec.type}.{role} uses {kind}")

    def test_unknown_kind_fails_with_the_known_ones(self) -> None:
        original = FEATURES["chamfer"]
        FEATURES["chamfer"] = replace(
            original, inputs=(("target", "part"), ("edges", "no_such_kind")))
        try:
            with self.assertRaises(BuildError) as caught:
                _build(
                    _box(),
                    Feature("x2", "chamfer", params={"length": 1.0},
                            refs={"target": Ref("x1", "self"),
                                  "edges": Ref("x1", "edges",
                                               (Filter("parallel_to", args=("Z",)),))}),
                )
            self.assertEqual(caught.exception.code, "UNKNOWN_KIND")
            self.assertIn("known kinds", caught.exception.hint or "")
        finally:
            FEATURES["chamfer"] = original

    def test_a_new_kind_needs_only_a_registration(self) -> None:
        original = FEATURES["chamfer"]
        register_input_kind("edge_set", ("edges",))
        FEATURES["chamfer"] = replace(
            original, inputs=(("target", "part"), ("edges", "edge_set")))
        try:
            result = _build(
                _box(),
                Feature("x2", "chamfer", params={"length": 2.0},
                        refs={"target": Ref("x1", "self"),
                              "edges": Ref("x1", "edges",
                                           (Filter("parallel_to", args=("Z",)),))}),
            )
            self.assertLess(float(result.final.volume), 8000.0)
        finally:
            FEATURES["chamfer"] = original


class ModifyTests(unittest.TestCase):
    def test_chamfer_removes_material_from_named_edges(self) -> None:
        result = _build(
            _box(),
            Feature("x2", "chamfer", params={"length": 2.0},
                    refs={
                        "target": Ref("x1", "self"),
                        "edges": Ref("x1", "edges", (Filter("parallel_to", args=("Z",)),)),
                    }),
        )
        final = result.final
        self.assertTrue(final.mesh().is_closed())
        self.assertLess(float(final.volume), 8000.0)


if __name__ == "__main__":
    unittest.main()
