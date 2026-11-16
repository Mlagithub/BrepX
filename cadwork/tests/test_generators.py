"""The parameterized generators: exact geometry, driving parameters, rebuilds.

Volumes are checked against arithmetic rather than a stored snapshot, because
the constructions are exact primitives and exact booleans; a stored number
would hide a change in the geometry behind a stale constant. Rebuilds use two
independent caches so the second build cannot pass on a cache hit.
"""

from __future__ import annotations

import math
import unittest

from cadwork.design.build import BuildCache, build
from cadwork.design.document import document_from_json, document_to_json
from cadwork.design.generators import airfoil, bolt, ring


def _build(document):
    return build(document, BuildCache())


class RingGeneratorTests(unittest.TestCase):
    def test_ring_is_a_bored_cylinder(self) -> None:
        outer, inner, height = 80.0, 50.0, 20.0
        document = ring(outer, inner, height)
        self.assertEqual(document.name, "ring")
        self.assertEqual(
            [feature.id for feature in document.features],
            ["ring_outer", "ring_tool", "ring_body"],
        )
        result = _build(document)
        final = result.final
        self.assertIsNotNone(final)
        self.assertEqual(result.final_feature_id, "ring_body")
        self.assertTrue(final.is_valid())
        self.assertEqual(len(final.faces()), 4)
        expected = math.pi * ((outer / 2.0) ** 2 - (inner / 2.0) ** 2) * height
        self.assertAlmostEqual(float(final.volume), expected, delta=expected * 1e-9)
        size = [float(value) for value in final.bbox().size]
        self.assertAlmostEqual(size[0], outer, places=6)
        self.assertAlmostEqual(size[1], outer, places=6)
        self.assertAlmostEqual(size[2], height, places=6)

    def test_ring_parameters_carry_radius_and_height(self) -> None:
        document = ring(80.0, 50.0, 20.0)
        parameters = {item.name: item for item in document.parameters}
        self.assertEqual(set(parameters), {"outer_radius", "inner_radius", "height"})
        self.assertEqual(
            (parameters["outer_radius"].feature_id, parameters["outer_radius"].param),
            ("ring_outer", "radius"),
        )
        self.assertEqual(parameters["outer_radius"].default, 40.0)
        self.assertEqual(parameters["inner_radius"].default, 25.0)
        self.assertEqual(parameters["height"].default, 20.0)
        self.assertEqual(parameters["height"].unit, "mm")

    def test_ring_rejects_a_bore_that_removes_the_ring(self) -> None:
        with self.assertRaises(ValueError):
            ring(50.0, 50.0, 10.0)
        with self.assertRaises(ValueError):
            ring(50.0, 60.0, 10.0)
        with self.assertRaises(ValueError):
            ring(50.0, 20.0, 0.0)
        with self.assertRaises(ValueError):
            ring(-50.0, 20.0, 10.0)


class BoltGeneratorTests(unittest.TestCase):
    def test_bolt_fuses_shank_and_head(self) -> None:
        shank, length, head, head_height = 8.0, 50.0, 14.0, 8.0
        document = bolt(shank, length, head, head_height)
        self.assertEqual(document.name, "bolt")
        self.assertEqual(
            [feature.id for feature in document.features],
            [
                "bolt_shank",
                "bolt_shank_placed",
                "bolt_head",
                "bolt_head_placed",
                "bolt_body",
            ],
        )
        result = _build(document)
        final = result.final
        self.assertIsNotNone(final)
        self.assertEqual(result.final_feature_id, "bolt_body")
        self.assertTrue(final.is_valid())
        self.assertEqual(len(final.faces()), 5)
        expected = math.pi / 4.0 * (shank**2 * length + head**2 * head_height)
        self.assertAlmostEqual(float(final.volume), expected, delta=expected * 1e-9)
        box = final.bbox()
        self.assertAlmostEqual(float(box.min[2]), 0.0, places=6)
        self.assertAlmostEqual(float(box.max[2]), length + head_height, places=6)
        size = [float(value) for value in box.size]
        self.assertAlmostEqual(size[0], head, places=6)
        self.assertAlmostEqual(size[1], head, places=6)
        self.assertAlmostEqual(size[2], length + head_height, places=6)

    def test_bolt_parameters_carry_the_independent_radii(self) -> None:
        document = bolt(8.0, 50.0, 14.0, 8.0)
        parameters = {item.name: item for item in document.parameters}
        self.assertEqual(set(parameters), {"shank_radius", "head_radius"})
        self.assertEqual(parameters["shank_radius"].feature_id, "bolt_shank")
        self.assertEqual(parameters["shank_radius"].default, 4.0)
        self.assertEqual(parameters["head_radius"].default, 7.0)

    def test_bolt_rejects_a_non_positive_dimension(self) -> None:
        with self.assertRaises(ValueError):
            bolt(0.0, 50.0, 14.0, 8.0)
        with self.assertRaises(ValueError):
            bolt(8.0, -50.0, 14.0, 8.0)
        with self.assertRaises(ValueError):
            bolt(8.0, 50.0, 14.0, 0.0)
        with self.assertRaises(ValueError):
            bolt("8", 50.0, 14.0, 8.0)


class AirfoilGeneratorTests(unittest.TestCase):
    def test_airfoil_lofts_closed_sections(self) -> None:
        chord, span = 120.0, 80.0
        document = airfoil(chord, span)
        ids = [feature.id for feature in document.features]
        self.assertEqual(ids[0], "section_0_curve")
        self.assertEqual(ids[1], "section_0_face")
        self.assertEqual(ids[2], "section_0_placed")
        self.assertEqual(ids[-1], "airfoil_body")
        self.assertEqual(len(ids), 3 * 5 + 1)
        self.assertEqual(document.parameters, ())

        result = _build(document)
        final = result.final
        self.assertIsNotNone(final)
        self.assertEqual(result.final_feature_id, "airfoil_body")
        self.assertTrue(final.is_valid())
        self.assertEqual(len(final.faces()), 3)

        curve = result.outputs["section_0_curve"]
        self.assertTrue(curve.is_closed)

        size = [float(value) for value in final.bbox().size]
        self.assertAlmostEqual(size[0], chord, places=6)
        self.assertAlmostEqual(size[2], span, places=6)
        thickness = 0.12 * chord
        self.assertAlmostEqual(size[1], thickness, delta=thickness * 0.01)

        section_area = float(result.outputs["section_0_face"].area)
        expected = section_area * span
        self.assertAlmostEqual(float(final.volume), expected, delta=expected * 1e-9)

    def test_airfoil_volume_does_not_depend_on_section_count(self) -> None:
        coarse = _build(airfoil(120.0, 80.0, sections=3)).final
        fine = _build(airfoil(120.0, 80.0, sections=9)).final
        self.assertIsNotNone(coarse)
        self.assertIsNotNone(fine)
        self.assertGreater(float(coarse.volume), 0.0)
        self.assertAlmostEqual(
            float(fine.volume), float(coarse.volume), delta=float(coarse.volume) * 1e-6
        )

    def test_airfoil_camber_changes_the_section(self) -> None:
        symmetric = _build(airfoil(120.0, 80.0)).final
        cambered = _build(airfoil(120.0, 80.0, camber=0.04)).final
        self.assertIsNotNone(cambered)
        self.assertTrue(cambered.is_valid())
        self.assertGreater(float(cambered.volume), 0.0)
        self.assertNotAlmostEqual(
            float(cambered.volume), float(symmetric.volume), places=3
        )

    def test_airfoil_rejects_impossible_inputs(self) -> None:
        with self.assertRaises(ValueError):
            airfoil(0.0, 80.0)
        with self.assertRaises(ValueError):
            airfoil(120.0, -80.0)
        with self.assertRaises(ValueError):
            airfoil(120.0, 80.0, thickness_ratio=0.0)
        with self.assertRaises(ValueError):
            airfoil(120.0, 80.0, sections=1)
        with self.assertRaises(ValueError):
            airfoil(120.0, 80.0, camber=float("nan"))


class RebuildStabilityTests(unittest.TestCase):
    def test_every_generator_rebuilds_to_the_same_body(self) -> None:
        documents = (
            ring(80.0, 50.0, 20.0),
            bolt(8.0, 50.0, 14.0, 8.0),
            airfoil(120.0, 80.0),
        )
        for document in documents:
            with self.subTest(document=document.id):
                first = _build(document)
                second = _build(document)
                self.assertIsNotNone(first.final)
                self.assertIsNotNone(second.final)
                self.assertEqual(len(first.final.faces()), len(second.final.faces()))
                self.assertEqual(float(first.final.volume), float(second.final.volume))

    def test_generated_documents_survive_json(self) -> None:
        documents = (
            ring(80.0, 50.0, 20.0),
            bolt(8.0, 50.0, 14.0, 8.0),
            airfoil(120.0, 80.0),
        )
        for document in documents:
            with self.subTest(document=document.id):
                restored = document_from_json(document_to_json(document))
                self.assertEqual(
                    [feature.id for feature in restored.features],
                    [feature.id for feature in document.features],
                )
                self.assertEqual(
                    float(_build(restored).final.volume),
                    float(_build(document).final.volume),
                )

    def test_a_second_build_of_one_document_hits_the_cache(self) -> None:
        for document in (
            ring(80.0, 50.0, 20.0),
            bolt(8.0, 50.0, 14.0, 8.0),
            airfoil(120.0, 80.0),
        ):
            with self.subTest(document=document.id):
                cache = BuildCache()
                build(document, cache)
                second = build(document, cache)
                self.assertEqual(second.cache_hits, len(document.features))


if __name__ == "__main__":
    unittest.main()
