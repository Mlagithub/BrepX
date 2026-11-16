"""The general vocabulary: primitives, profiles, form, place, pattern, modify.

Each test builds a tiny document from the generated action registry — no sample,
no framework shortcut — so a broken kernel binding fails here rather than in a
part file.
"""

from __future__ import annotations

import math
import unittest
from dataclasses import replace

from cadwork.design import BuildError, build
from cadwork.design.document import Document, Feature, Filter, Ref
from cadwork.design.features import (
    FEATURES,
    INPUT_KINDS,
    InputRole,
    register_input_kind,
)


def _build(*features: Feature):
    return build(Document(id="t", name="t", features=features))


def _box(**params) -> Feature:
    values = {"length": 20.0, "width": 20.0, "height": 20.0}
    values.update(params)
    return Feature("x1", "k_box", params=values)


def _top_face() -> Ref:
    return Ref("x1", "faces", (Filter("top"), Filter("one")))


class PrimitiveTests(unittest.TestCase):
    def test_each_primitive_builds_a_closed_solid(self) -> None:
        cases = (
            ("k_box", {"length": 20.0, "width": 20.0, "height": 20.0}, 8000.0),
            ("k_cylinder", {"radius": 5.0, "height": 20.0}, math.pi * 25 * 20),
            (
                "k_cone",
                {"bottom_radius": 5.0, "top_radius": 0.0, "height": 20.0},
                math.pi * 25 * 20 / 3.0,
            ),
            ("k_sphere", {"radius": 5.0}, 4.0 / 3.0 * math.pi * 125),
        )
        for type_name, params, expected in cases:
            result = _build(Feature("x1", type_name, params=params))
            final = result.final
            self.assertTrue(final.is_valid(), type_name)
            self.assertTrue(final.mesh().is_closed(), type_name)
            self.assertAlmostEqual(
                float(final.volume), expected, delta=expected * 0.01, msg=type_name
            )
            self.assertGreaterEqual(len(final.faces()), 1, type_name)

    def test_placement_moves_the_body(self) -> None:
        near = _build(_box()).final.bbox()
        far = _build(
            _box(),
            Feature(
                "x2",
                "k_translate",
                params={"x": 100.0},
                refs={"target": Ref("x1", "self")},
            ),
        ).final.bbox()
        self.assertAlmostEqual(float(far.max[0] - near.max[0]), 100.0, places=3)


class ProfileAndFormTests(unittest.TestCase):
    def test_circle_extrudes_to_a_solid(self) -> None:
        result = _build(
            Feature("x1", "k_circle", params={"radius": 10.0}),
            Feature(
                "x2",
                "k_extrude",
                params={"amount": 12.0},
                refs={"profile": Ref("x1", "self")},
            ),
        )
        final = result.final
        self.assertTrue(final.mesh().is_closed())
        self.assertEqual(len(final.faces()), 3)
        # 10 mm radius over 12 mm: 3769.9 mm³
        self.assertAlmostEqual(float(final.volume), math.pi * 100 * 12, delta=5.0)

    def test_polygon_revolve_about_the_axis(self) -> None:
        # A 4×10 rectangle at y=20..30, revolved about X: a tube of radii
        # 20..30, 4 mm long. The profile must sit beside the axis, not across it.
        result = _build(
            Feature(
                "x1",
                "k_polygon",
                params={"points": [[0.0, 20.0], [4.0, 20.0], [4.0, 30.0], [0.0, 30.0]]},
            ),
            Feature(
                "x2",
                "k_revolve",
                params={"axis": "X", "angle": 360.0},
                refs={"profile": Ref("x1", "self")},
            ),
        )
        final = result.final
        self.assertTrue(final.mesh().is_closed())
        expected = math.pi * (30**2 - 20**2) * 4
        self.assertAlmostEqual(float(final.volume), expected, delta=expected * 0.01)
        self.assertEqual(len(final.faces()), 4)

    def test_spiral_sweep_with_scale_grows_the_section(self) -> None:
        result = _build(
            Feature(
                "spiral",
                "k_spiral",
                params={
                    "start_radius": 20.0,
                    "end_radius": 40.0,
                    "turns": 0.5,
                    "plane": "XY",
                    "clockwise": False,
                },
            ),
            Feature("section", "k_rectangle", params={"width": 4.0, "height": 6.0}),
            Feature(
                "sweep",
                "k_sweep",
                params={
                    "scale_start": 0.5,
                    "scale_end": 1.0,
                    "orient": True,
                    "translational": False,
                    "twist": 0.0,
                },
                refs={"profile": Ref("section", "self"), "path": Ref("spiral", "self")},
            ),
        )
        final = result.final
        self.assertTrue(final.is_valid())
        self.assertTrue(final.mesh().is_closed())
        # A 24 mm² section swept along the spiral with the scale ramp.
        self.assertGreater(float(final.volume), 1300.0)
        self.assertLess(float(final.volume), 1400.0)
        self.assertEqual(len(final.faces()), 6)


class PlacementTests(unittest.TestCase):
    def test_rotate_then_translate(self) -> None:
        base = _build(
            Feature(
                "x1", "k_box", params={"length": 40.0, "width": 10.0, "height": 10.0}
            )
        ).final
        moved = _build(
            Feature(
                "x1", "k_box", params={"length": 40.0, "width": 10.0, "height": 10.0}
            ),
            Feature(
                "x2",
                "k_rotate",
                params={"axis": "Z", "angle": 90.0},
                refs={"target": Ref("x1", "self")},
            ),
            Feature(
                "x3",
                "k_translate",
                params={"x": 100.0},
                refs={"target": Ref("x2", "self")},
            ),
        ).final
        self.assertAlmostEqual(float(moved.volume), float(base.volume), delta=1.0)
        self.assertAlmostEqual(float(moved.bbox().max[0]), 105.0, delta=0.5)

    def test_linear_pattern_repeats_the_body(self) -> None:
        result = _build(
            _box(),
            Feature(
                "x2",
                "pattern",
                params={"kind": "linear", "count": 4, "dx": 30.0},
                refs={"target": Ref("x1", "self")},
            ),
        )
        final = result.final
        self.assertEqual(len(final.solids()), 4)
        self.assertAlmostEqual(float(final.volume), 8000.0 * 4, delta=40.0)

    def test_mirror_preserves_volume_and_flips_the_body(self) -> None:
        result = _build(
            _box(),
            Feature(
                "x1t",
                "k_translate",
                params={"x": 40.0},
                refs={"target": Ref("x1", "self")},
            ),
            Feature(
                "x2",
                "k_mirror",
                params={"plane": "YZ"},
                refs={"target": Ref("x1t", "self")},
            ),
        )
        self.assertAlmostEqual(float(result.final.volume), 8000.0, delta=1.0)
        self.assertLess(float(result.final.bbox().min[0]), 0.0)

    def test_place_on_a_face(self) -> None:
        result = _build(
            _box(),
            Feature("x2", "k_rectangle", params={"width": 4.0, "height": 4.0}),
            Feature(
                "x3", "place_on", refs={"shape": Ref("x2", "self"), "face": _top_face()}
            ),
        )
        sketch = result.outputs["x3"]
        self.assertAlmostEqual(float(sketch.bbox().min[2]), 10.0, places=3)
        self.assertAlmostEqual(float(sketch.bbox().max[2]), 10.0, places=3)
        self.assertAlmostEqual(float(sketch.bbox().min[0]), -2.0, places=3)
        self.assertAlmostEqual(float(sketch.bbox().max[0]), 2.0, places=3)

    def test_place_on_a_plane_with_an_offset(self) -> None:
        result = _build(
            Feature("x1", "k_rectangle", params={"width": 4.0, "height": 4.0}),
            Feature(
                "x2",
                "place_on",
                params={"plane": "XY", "offset": 5.0},
                refs={"shape": Ref("x1", "self")},
            ),
        )
        sketch = result.outputs["x2"]
        self.assertAlmostEqual(float(sketch.bbox().min[2]), 5.0, places=3)
        self.assertAlmostEqual(float(sketch.bbox().max[2]), 5.0, places=3)


class SolidEditTests(unittest.TestCase):
    def test_offset_grows_the_body(self) -> None:
        result = _build(
            _box(),
            Feature(
                "x2",
                "k_offset",
                params={"distance": 2.0},
                refs={"target": Ref("x1", "self")},
            ),
        )
        final = result.final
        self.assertTrue(final.mesh().is_closed())
        self.assertAlmostEqual(float(final.volume), 24**3, delta=5.0)

    def test_split_keeps_one_side(self) -> None:
        result = _build(
            Feature(
                "x1", "k_box", params={"length": 40.0, "width": 20.0, "height": 10.0}
            ),
            Feature(
                "x2",
                "k_split",
                params={"plane": "XY", "keep": "above"},
                refs={"target": Ref("x1", "self")},
            ),
        )
        self.assertAlmostEqual(float(result.final.volume), 4000.0, delta=20.0)

    def test_scale_cubes_the_volume(self) -> None:
        result = _build(
            _box(),
            Feature(
                "x2",
                "k_scale",
                params={"factor": 1.5},
                refs={"target": Ref("x1", "self")},
            ),
        )
        self.assertAlmostEqual(float(result.final.volume), 27000.0, delta=100.0)

    def test_grid_pattern_counts_solids(self) -> None:
        result = _build(
            _box(),
            Feature(
                "x2",
                "pattern",
                params={
                    "kind": "grid",
                    "x_count": 2,
                    "y_count": 3,
                    "x_spacing": 30.0,
                    "y_spacing": 30.0,
                },
                refs={"target": Ref("x1", "self")},
            ),
        )
        self.assertEqual(len(result.final.solids()), 6)

    def test_thicken_turns_a_face_into_a_solid(self) -> None:
        result = _build(
            _box(),
            Feature(
                "x2",
                "k_face_to_shell",
                refs={
                    "target": Ref(
                        "x1", "faces", (Filter("nearest", args=([0.0, 0.0, 10.0],)),)
                    )
                },
            ),
            Feature(
                "x3",
                "k_thicken",
                params={"thickness": 3.0},
                refs={"surface": Ref("x2", "self")},
            ),
        )
        final = result.final
        self.assertTrue(final.mesh().is_closed())
        # a 20×20 face thick by 3 mm
        self.assertAlmostEqual(float(final.volume), 1200.0, delta=20.0)
        self.assertEqual(len(final.faces()), 6)

    def test_face_extrude_adds_material_from_the_face(self) -> None:
        result = _build(
            _box(),
            Feature(
                "x2",
                "k_face_extrude",
                params={"amount": 5.0},
                refs={"target": _top_face()},
            ),
        )
        final = result.final
        self.assertTrue(final.mesh().is_closed())
        self.assertAlmostEqual(float(final.volume), 20.0 * 20.0 * 5.0, delta=1.0)
        self.assertEqual(len(final.faces()), 6)
        self.assertAlmostEqual(float(final.bbox().min[2]), 10.0, places=3)
        self.assertAlmostEqual(float(final.bbox().max[2]), 15.0, places=3)

    def test_draft_tilts_a_named_side_face(self) -> None:
        result = _build(
            _box(),
            Feature(
                "x2",
                "k_draft",
                params={"angle": 10.0, "neutral_plane": "XY"},
                refs={
                    "target": Ref("x1", "self"),
                    "faces": Ref(
                        "x1", "faces", (Filter("nearest", args=([10.0, 0.0, 0.0],)),)
                    ),
                },
            ),
        )
        final = result.final
        self.assertTrue(final.is_valid())
        self.assertTrue(final.mesh().is_closed())
        # The face tilts around its mid-line: the shear changes the envelope but
        # not the volume.
        self.assertAlmostEqual(float(final.volume), 8000.0, delta=1.0)
        self.assertEqual(len(final.faces()), 6)
        self.assertGreater(float(final.bbox().max[0]), 10.5)


class OptionalInputTests(unittest.TestCase):
    def test_closed_shell_without_openings(self) -> None:
        result = _build(
            _box(),
            Feature(
                "x2",
                "k_shell",
                params={"thickness": 2.0},
                refs={"target": Ref("x1", "self")},
            ),
        )
        self.assertTrue(result.final.mesh().is_closed())
        self.assertAlmostEqual(float(result.final.volume), 3904.0, delta=10.0)

    def test_openings_remove_the_named_face(self) -> None:
        closed = _build(
            _box(),
            Feature(
                "x2",
                "k_shell",
                params={"thickness": 2.0},
                refs={"target": Ref("x1", "self")},
            ),
        ).final
        opened = _build(
            _box(),
            Feature(
                "x2",
                "k_shell",
                params={"thickness": 2.0},
                refs={
                    "target": Ref("x1", "self"),
                    "openings": Ref(
                        "x1", "faces", (Filter("nearest", args=([0.0, 0.0, 10.0],)),)
                    ),
                },
            ),
        ).final
        self.assertLess(float(opened.volume), float(closed.volume))
        self.assertAlmostEqual(float(opened.volume), 3392.0, delta=10.0)

    def test_missing_required_role_still_fails(self) -> None:
        with self.assertRaises(BuildError) as caught:
            _build(
                _box(),
                Feature(
                    "x2",
                    "k_chamfer",
                    params={"length": 1.0},
                    refs={"target": Ref("x1", "self")},
                ),
            )
        self.assertEqual(caught.exception.code, "INVALID_REFS")


class HoleTests(unittest.TestCase):
    def test_hole_is_a_cylinder_primitive(self) -> None:
        result = _build(Feature("x1", "k_hole", params={"radius": 5.0, "depth": 30.0}))
        final = result.final
        self.assertTrue(final.mesh().is_closed())
        self.assertAlmostEqual(float(final.volume), math.pi * 25 * 30, delta=2.0)
        self.assertEqual(len(final.faces()), 3)

    def test_through_cut_removes_a_cylinder(self) -> None:
        result = _build(
            _box(),
            Feature("x2", "k_cylinder", params={"radius": 5.0, "height": 30.0}),
            Feature(
                "x3",
                "k_cut",
                refs={"target": Ref("x1", "self"), "others": (Ref("x2", "self"),)},
            ),
        )
        expected = 8000.0 - math.pi * 25 * 20
        self.assertTrue(result.final.mesh().is_closed())
        self.assertAlmostEqual(
            float(result.final.volume), expected, delta=expected * 0.001
        )
        self.assertEqual(len(result.final.faces()), 7)

    def test_hole_primitive_can_be_cut_through(self) -> None:
        result = _build(
            _box(),
            Feature("x2", "k_hole", params={"radius": 5.0, "depth": 30.0}),
            Feature(
                "x3",
                "k_translate",
                params={"z": 10.0},
                refs={"target": Ref("x2", "self")},
            ),
            Feature(
                "x4",
                "k_cut",
                refs={"target": Ref("x1", "self"), "others": (Ref("x3", "self"),)},
            ),
        )
        expected = 8000.0 - math.pi * 25 * 20
        self.assertAlmostEqual(
            float(result.final.volume), expected, delta=expected * 0.01
        )


class InputKindTests(unittest.TestCase):
    def test_every_declared_kind_is_registered(self) -> None:
        for spec in FEATURES.values():
            for role in spec.inputs:
                self.assertIn(
                    role.kind, INPUT_KINDS, f"{spec.type}.{role.role} uses {role.kind}"
                )

    def test_unknown_kind_fails_with_the_known_ones(self) -> None:
        original = FEATURES["k_chamfer"]
        FEATURES["k_chamfer"] = replace(
            original,
            inputs=(InputRole("target", "part"), InputRole("edges", "no_such_kind")),
        )
        try:
            with self.assertRaises(BuildError) as caught:
                _build(
                    _box(),
                    Feature(
                        "x2",
                        "k_chamfer",
                        params={"length": 1.0},
                        refs={
                            "target": Ref("x1", "self"),
                            "edges": Ref(
                                "x1", "edges", (Filter("parallel_to", args=("Z",)),)
                            ),
                        },
                    ),
                )
            self.assertEqual(caught.exception.code, "UNKNOWN_KIND")
            self.assertIn("known kinds", caught.exception.hint or "")
        finally:
            FEATURES["k_chamfer"] = original

    def test_a_new_kind_needs_only_a_registration(self) -> None:
        original = FEATURES["k_chamfer"]
        register_input_kind("edge_set_test", ("edges",))
        FEATURES["k_chamfer"] = replace(
            original,
            inputs=(InputRole("target", "part"), InputRole("edges", "edge_set_test")),
        )
        try:
            result = _build(
                _box(),
                Feature(
                    "x2",
                    "k_chamfer",
                    params={"length": 2.0},
                    refs={
                        "target": Ref("x1", "self"),
                        "edges": Ref(
                            "x1", "edges", (Filter("parallel_to", args=("Z",)),)
                        ),
                    },
                ),
            )
            self.assertLess(float(result.final.volume), 8000.0)
        finally:
            FEATURES["k_chamfer"] = original


class ModifyTests(unittest.TestCase):
    def test_chamfer_removes_material_from_named_edges(self) -> None:
        result = _build(
            _box(),
            Feature(
                "x2",
                "k_chamfer",
                params={"length": 2.0},
                refs={
                    "target": Ref("x1", "self"),
                    "edges": Ref("x1", "edges", (Filter("parallel_to", args=("Z",)),)),
                },
            ),
        )
        final = result.final
        self.assertTrue(final.mesh().is_closed())
        self.assertAlmostEqual(float(final.volume), 7840.0, delta=5.0)
        self.assertEqual(len(final.faces()), 10)

    def test_fillet_rounds_named_edges(self) -> None:
        result = _build(
            _box(),
            Feature(
                "x2",
                "k_fillet",
                params={"radius": 2.0},
                refs={
                    "target": Ref("x1", "self"),
                    "edges": Ref("x1", "edges", (Filter("parallel_to", args=("Z",)),)),
                },
            ),
        )
        final = result.final
        self.assertTrue(final.mesh().is_closed())
        self.assertLess(float(final.volume), 8000.0)
        self.assertEqual(len(final.faces()), 10)


if __name__ == "__main__":
    unittest.main()
