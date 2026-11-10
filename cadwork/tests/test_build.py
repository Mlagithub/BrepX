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
    def test_impeller_builds_nine_features(self) -> None:
        result = build(impeller_document(), BuildCache())
        self.assertEqual([item.feature_id for item in result.features],
                         ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9"])
        self.assertTrue(all(check.ok for item in result.features for check in item.checks))
        self.assertEqual(sorted(result.tags), ["f6", "f7", "f8"])
        self.assertIsNotNone(result.final)

    def test_two_fresh_builds_are_identical(self) -> None:
        first = build(impeller_document(), BuildCache())
        second = build(impeller_document(), BuildCache())
        self.assertEqual(_signature(first.outputs["f5"]), _signature(second.outputs["f5"]))
        self.assertEqual(_signature(first.final), _signature(second.final))

    def test_warm_cache_reproduces_cold_result(self) -> None:
        cache = BuildCache()
        cold = build(impeller_document(), cache)
        warm = build(impeller_document(), cache)
        self.assertEqual(cold.cache_hits, 0)
        self.assertEqual(warm.cache_hits, len(warm.features))
        self.assertEqual(_signature(cold.outputs["f5"]), _signature(warm.outputs["f5"]))

    def test_param_edit_rebuilds_only_downstream(self) -> None:
        cache = BuildCache()
        build(impeller_document(), cache)
        edited = apply_ops(impeller_document(), [
            {"op": "update", "id": "f3", "params": {"count": 11}},
        ])
        warm = build(edited, cache)
        cached = {item.feature_id for item in warm.features if item.cached}
        self.assertEqual(cached, {"f1", "f2"})

    def test_disabling_a_leaf_feature_removes_it(self) -> None:
        document = apply_ops(impeller_document(), [
            {"op": "update", "id": "f9", "enabled": False},
        ])
        result = build(document, BuildCache())
        self.assertNotIn("f9", result.outputs)
        self.assertEqual(result.final is result.outputs["f8"], True)

    def test_fillet_failure_is_structured_and_leaves_version(self) -> None:
        document = impeller_document(fillet_radius=2.0)
        before = document.version
        with self.assertRaises(BuildError) as caught:
            build(document, BuildCache())
        error = caught.exception
        self.assertEqual(error.code, "BUILD_FAILED")
        self.assertEqual(error.feature_id, "f5")
        self.assertEqual(document.version, before)
        payload = json.loads(json.dumps(error.to_json()))
        self.assertIn("blocked_downstream", payload)
        self.assertEqual(payload["blocked_downstream"], ["f6", "f7", "f8", "f9"])
        self.assertTrue(error.hint)

    def test_count_change_keeps_boundaries(self) -> None:
        for count in (9, 11):
            result = build(impeller_document(count=count), BuildCache())
            self.assertEqual(sorted(result.tags), ["f6", "f7", "f8"], f"count={count}")
            self.assertGreaterEqual(result.tags["f6"]["faces"], 1)
            self.assertGreaterEqual(result.tags["f7"]["faces"], 1)

    def test_fluid_domain_is_watertight(self) -> None:
        result = build(impeller_document(), BuildCache())
        checks = {check.name: check.ok for item in result.features for check in item.checks}
        self.assertTrue(checks["watertight"])

    def test_impeller_json_roundtrip_builds_identically(self) -> None:
        from cadwork.design import document_from_json, document_to_json

        document = impeller_document()
        payload = json.loads(json.dumps(document_to_json(document)))
        restored = document_from_json(payload)
        first = build(document, BuildCache())
        second = build(restored, BuildCache())
        self.assertEqual(_signature(first.outputs["f5"]), _signature(second.outputs["f5"]))
        self.assertEqual(sorted(first.tags), sorted(second.tags))
        self.assertEqual(document_to_json(restored), document_to_json(document))


if __name__ == "__main__":
    unittest.main()
