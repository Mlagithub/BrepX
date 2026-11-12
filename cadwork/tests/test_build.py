"""Build-engine tests: determinism, cache correctness, atomic failure."""

from __future__ import annotations

import json
import unittest

from cadwork.design import BuildCache, BuildError, build
from cadwork.design.document import apply_ops
from cadwork.samples.impeller import impeller_document


def _signature(part) -> tuple[int, float]:
    return len(part.faces()), round(float(part.volume), 6)


class BuildTests(unittest.TestCase):
    def test_impeller_builds_every_feature(self) -> None:
        document = impeller_document()
        result = build(document, BuildCache())
        self.assertEqual([item.feature_id for item in result.features],
                         [feature.id for feature in document.features])
        self.assertEqual(len(result.features), 36)
        self.assertTrue(all(check.ok for item in result.features for check in item.checks))
        self.assertEqual(sorted(result.tags), ["t_in", "t_out", "t_wall"])
        self.assertIsNotNone(result.final)
        self.assertAlmostEqual(float(result.final.volume), 152725.69, delta=1.0)

    def test_two_fresh_builds_are_identical(self) -> None:
        first = build(impeller_document(), BuildCache())
        second = build(impeller_document(), BuildCache())
        self.assertEqual(_signature(first.outputs["b_fillet"]),
                         _signature(second.outputs["b_fillet"]))
        self.assertEqual(_signature(first.final), _signature(second.final))

    def test_warm_cache_reproduces_cold_result(self) -> None:
        cache = BuildCache()
        cold = build(impeller_document(), cache)
        warm = build(impeller_document(), cache)
        # Within one build the repeated section sketches share a cache key.
        self.assertLess(cold.cache_hits, len(cold.features))
        self.assertEqual(warm.cache_hits, len(warm.features))
        self.assertEqual(_signature(cold.outputs["b_fillet"]),
                         _signature(warm.outputs["b_fillet"]))

    def test_param_edit_rebuilds_only_downstream(self) -> None:
        cache = BuildCache()
        document = impeller_document()
        build(document, cache)
        edited = apply_ops(document, [
            {"op": "update", "id": "b_pattern", "params": {"count": 11}},
        ])
        warm = build(edited, cache)
        cached = {item.feature_id for item in warm.features if item.cached}
        ids = [feature.id for feature in edited.features]
        self.assertEqual(cached, set(ids[:ids.index("b_pattern")]))

    def test_disabling_a_leaf_feature_removes_it(self) -> None:
        document = apply_ops(impeller_document(), [
            {"op": "update", "id": "c1", "enabled": False},
        ])
        result = build(document, BuildCache())
        self.assertNotIn("c1", result.outputs)
        self.assertIs(result.final, result.outputs["t_wall"])

    def test_fillet_failure_is_structured_and_leaves_version(self) -> None:
        document = impeller_document(fillet_radius=2.0)
        before = document.version
        with self.assertRaises(BuildError) as caught:
            build(document, BuildCache())
        error = caught.exception
        self.assertEqual(error.code, "BUILD_FAILED")
        self.assertEqual(error.feature_id, "b_fillet")
        self.assertEqual(document.version, before)
        payload = json.loads(json.dumps(error.to_json()))
        self.assertIn("blocked_downstream", payload)
        self.assertEqual(payload["blocked_downstream"], ["t_in", "t_out", "t_wall", "c1"])
        self.assertTrue(error.hint)

    def test_count_change_keeps_boundaries(self) -> None:
        baseline = len(build(impeller_document(), BuildCache()).final.faces())
        for count in (9, 11):
            result = build(impeller_document(count=count), BuildCache())
            self.assertEqual(sorted(result.tags), ["t_in", "t_out", "t_wall"], f"count={count}")
            self.assertGreaterEqual(result.tags["t_in"]["faces"], 1)
            self.assertGreaterEqual(result.tags["t_out"]["faces"], 1)
            if count == 11:
                self.assertNotEqual(len(result.final.faces()), baseline)

    def test_fluid_domain_is_watertight(self) -> None:
        result = build(impeller_document(), BuildCache())
        checks = {check.name: check.ok for item in result.features for check in item.checks}
        self.assertTrue(checks["watertight"])
        self.assertGreater(len(result.final.solids()), 0)

    def test_impeller_json_roundtrip_builds_identically(self) -> None:
        from cadwork.design import document_from_json, document_to_json

        document = impeller_document()
        payload = json.loads(json.dumps(document_to_json(document)))
        restored = document_from_json(payload)
        first = build(document, BuildCache())
        second = build(restored, BuildCache())
        self.assertEqual(_signature(first.outputs["b_fillet"]),
                         _signature(second.outputs["b_fillet"]))
        self.assertEqual(sorted(first.tags), sorted(second.tags))
        self.assertEqual(document_to_json(restored), document_to_json(document))


if __name__ == "__main__":
    unittest.main()
