"""Tests for evaluating plan expectations against fake built values."""

from __future__ import annotations

import unittest

from cadwork.design.document import Ref
from cadwork.design.plan import Expect, PlanError, PlanNode, new_plan
from cadwork.design.verify import VerifyContext, evaluate


class Vec:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.x, self.y, self.z = x, y, z

    def __getitem__(self, index: int) -> float:
        return (self.x, self.y, self.z)[index]

    def __len__(self) -> int:
        return 3

    def __iter__(self):
        return iter((self.x, self.y, self.z))


class Box:
    def __init__(self, minimum, maximum) -> None:
        self.min = Vec(*minimum)
        self.max = Vec(*maximum)
        self.size = Vec(maximum[0] - minimum[0],
                        maximum[1] - minimum[1],
                        maximum[2] - minimum[2])


class Mesh:
    def __init__(self, closed: bool) -> None:
        self._closed = closed

    def is_closed(self) -> bool:
        return self._closed


class Face:
    def __init__(self, area: float) -> None:
        self.area = area


class Part:
    def __init__(self, volume: float = 100.0, face_areas=(10.0, 20.0, 30.0),
                 edges: int = 12, solids: int = 1, closed: bool = True,
                 distance_value: float = 1.5, intersects_value: bool = True) -> None:
        self.volume = volume
        self._faces = [Face(area) for area in face_areas]
        self._edges = [object() for _ in range(edges)]
        self._solids = [object() for _ in range(solids)]
        self._box = Box((0.0, 0.0, 0.0), (10.0, 20.0, 30.0))
        self._closed = closed
        self.distance_value = distance_value
        self.intersects_value = intersects_value

    def faces(self):
        return list(self._faces)

    def edges(self):
        return list(self._edges)

    def solids(self):
        return list(self._solids)

    def is_valid(self) -> bool:
        return True

    def bbox(self):
        return self._box

    def mesh(self):
        return Mesh(self._closed)

    def distance(self, other):
        return self.distance_value

    def intersects(self, other):
        return self.intersects_value


def _plan_for(source_id: str, feature_id: str | None = None):
    return new_plan("d1", "test", 0, nodes=(
        PlanNode(source_id, "feature", "source", action="solid_box",
                 feature_id=feature_id),
    ))


class VerifyMetricTests(unittest.TestCase):
    def test_volume_comparisons(self) -> None:
        part = Part(volume=100.0)
        results = evaluate(
            (
                Expect("volume", "ge", 50.0),
                Expect("volume", "le", 50.0),
                Expect("volume", "eq", 100.0),
                Expect("volume", "between", (90.0, 110.0)),
            ),
            part,
        )
        self.assertEqual([item.ok for item in results], [True, False, True, True])
        self.assertEqual(results[0].observed["volume"], 100.0)
        self.assertIsNotNone(results[1].hint)

    def test_eq_uses_tolerance(self) -> None:
        part = Part(volume=100.0)
        self.assertFalse(evaluate(Expect("volume", "eq", 100.001), part)[0].ok)
        self.assertTrue(
            evaluate(Expect("volume", "eq", 100.001, tolerance=0.01), part)[0].ok
        )

    def test_count_metrics(self) -> None:
        part = Part(face_areas=(1.0, 2.0, 3.0, 4.0), edges=7, solids=2)
        results = evaluate(
            (
                Expect("faces", "eq", 4),
                Expect("edges", "ge", 7),
                Expect("solids", "eq", 2),
                Expect("faces", "le", 3),
            ),
            part,
        )
        self.assertEqual([item.ok for item in results], [True, True, True, False])

    def test_area_sums_faces_when_the_value_has_no_area(self) -> None:
        part = Part(face_areas=(10.0, 20.0, 30.0))
        result = evaluate(Expect("area", "eq", 60.0), part)[0]
        self.assertTrue(result.ok, result)
        self.assertEqual(result.observed["area"], 60.0)

    def test_watertight_uses_mesh(self) -> None:
        self.assertTrue(evaluate(Expect("watertight", "true"), Part(closed=True))[0].ok)
        self.assertFalse(evaluate(Expect("watertight", "true"), Part(closed=False))[0].ok)

    def test_bbox_metrics_are_vectors(self) -> None:
        part = Part()
        results = evaluate(
            (
                Expect("bbox_size", "eq", (10.0, 20.0, 30.0)),
                Expect("bbox_min", "ge", (0.0, 0.0, 0.0)),
                Expect("bbox_max", "le", (10.0, 20.0, 30.0)),
                Expect("bbox_size", "between", ((9.0, 19.0, 29.0), (11.0, 21.0, 31.0))),
                Expect("bbox_max", "eq", (1.0, 2.0, 3.0)),
            ),
            part,
        )
        self.assertEqual([item.ok for item in results], [True, True, True, True, False])

    def test_measurement_failure_is_a_failed_check_not_an_exception(self) -> None:
        class Bare:
            pass

        result = evaluate(Expect("volume", "ge", 1.0), Bare())[0]
        self.assertFalse(result.ok)
        self.assertIn("error", result.observed)
        self.assertIsNotNone(result.hint)


class VerifyReferenceTests(unittest.TestCase):
    def test_distance_and_intersects_resolve_refs(self) -> None:
        target = Part(distance_value=1.5, intersects_value=True)
        other = Part()
        context = VerifyContext(outputs={"f1": other})
        results = evaluate(
            (
                Expect("distance", "le", 2.0, ref=Ref("f1", "self")),
                Expect("intersects", "true", ref=Ref("f1", "self")),
            ),
            target,
            context,
        )
        self.assertTrue(results[0].ok, results[0])
        self.assertTrue(results[1].ok, results[1])
        self.assertEqual(results[0].observed["ref"], "f1")

    def test_distance_and_intersects_fail_when_the_expectation_fails(self) -> None:
        target = Part(distance_value=5.0, intersects_value=False)
        other = Part()
        results = evaluate(
            (
                Expect("distance", "le", 2.0, ref=Ref("f1", "self")),
                Expect("intersects", "true", ref=Ref("f1", "self")),
            ),
            target,
            {"outputs": {"f1": other}},
        )
        self.assertFalse(results[0].ok)
        self.assertFalse(results[1].ok)

    def test_ref_source_can_be_a_plan_node_id(self) -> None:
        target = Part(distance_value=1.0)
        other = Part()
        plan = _plan_for("n1", feature_id="f_real")
        context = VerifyContext(outputs={"f_real": other}, plan=plan)
        result = evaluate(
            Expect("distance", "le", 2.0, ref=Ref("n1", "self")), target, context
        )[0]
        self.assertTrue(result.ok, result)

    def test_ref_source_can_be_a_variable(self) -> None:
        target = Part(distance_value=1.0)
        other = Part()
        plan = _plan_for("n1", feature_id="f_real")
        context = VerifyContext(outputs={"nn1": other}, plan=plan)
        result = evaluate(
            Expect("distance", "le", 2.0, ref=Ref("n1", "self")), target, context
        )[0]
        self.assertTrue(result.ok, result)

    def test_a_bare_output_mapping_is_accepted_as_context(self) -> None:
        target = Part(distance_value=1.0)
        other = Part()
        result = evaluate(
            Expect("distance", "le", 2.0, ref=Ref("f1", "self")),
            target,
            {"f1": other},
        )[0]
        self.assertTrue(result.ok, result)

    def test_missing_output_is_a_failed_check(self) -> None:
        result = evaluate(
            Expect("distance", "le", 2.0, ref=Ref("missing", "self")),
            Part(),
            VerifyContext(outputs={}),
        )[0]
        self.assertFalse(result.ok)
        self.assertIn("error", result.observed)

    def test_distance_to_is_supported(self) -> None:
        class DistanceOnly:
            def distance_to(self, other):
                return 2.5

        result = evaluate(
            Expect("distance", "le", 3.0, ref=Ref("f1", "self")),
            DistanceOnly(),
            {"f1": Part()},
        )[0]
        self.assertTrue(result.ok, result)
        self.assertEqual(result.observed["distance"], 2.5)

    def test_boolean_intersect_result_is_supported(self) -> None:
        class IntersectOnly:
            def intersect(self, other):
                return type("Shape", (), {"volume": 5.0})()

        result = evaluate(
            Expect("intersects", "true", ref=Ref("f1", "self")),
            IntersectOnly(),
            {"f1": Part()},
        )[0]
        self.assertTrue(result.ok, result)


class VerifyApiTests(unittest.TestCase):
    def test_single_expect_is_accepted(self) -> None:
        results = evaluate(Expect("volume", "eq", 100.0), Part())
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].ok)

    def test_none_expects_returns_empty_list(self) -> None:
        self.assertEqual(evaluate(None, Part()), [])

    def test_unknown_metric_and_op_raise_plan_error(self) -> None:
        with self.assertRaises(PlanError) as caught:
            evaluate(Expect("weight", "ge", 1.0), Part())
        self.assertEqual(caught.exception.code, "PLAN_INVALID")

        with self.assertRaises(PlanError) as caught:
            evaluate(Expect("volume", "roughly", 1.0), Part())
        self.assertEqual(caught.exception.code, "PLAN_INVALID")

    def test_distance_without_ref_raises_plan_error(self) -> None:
        with self.assertRaises(PlanError) as caught:
            evaluate(Expect("distance", "le", 1.0), Part())
        self.assertEqual(caught.exception.code, "PLAN_INVALID")

    def test_result_names_are_metrics(self) -> None:
        results = evaluate(
            (Expect("volume", "ge", 1.0), Expect("faces", "ge", 1)), Part()
        )
        self.assertEqual([item.name for item in results], ["volume", "faces"])


if __name__ == "__main__":
    unittest.main()
