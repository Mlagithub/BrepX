"""Tests for the document model: edits are atomic and always produce a new value."""

from __future__ import annotations

import unittest

from cadwork.design.document import (
    Document,
    DocumentError,
    Feature,
    Filter,
    Ref,
    apply_ops,
    document_from_json,
    document_to_json,
    feature_from_json,
    feature_to_json,
    milestone_from_json,
    milestone_to_json,
    new_document,
    ref_from_json,
    ref_to_json,
)


def _feature(feature_id: str, feature_type: str = "k_box", **refs: Ref) -> dict:
    return {
        "op": "add",
        "feature": {
            "id": feature_id,
            "type": feature_type,
            "params": {},
            "refs": {role: ref_to_json(ref) for role, ref in refs.items()},
        },
    }


class DocumentEditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.doc = new_document("test", "d_test")

    def test_new_document_is_empty(self) -> None:
        self.assertEqual(self.doc.version, 0)
        self.assertEqual(self.doc.features, ())
        self.assertEqual(len(self.doc.milestones), 1)
        self.assertEqual(self.doc.milestones[0].version, 0)
        self.assertEqual(self.doc.milestones[0].parent_version, None)

    def test_add_bumps_version_and_keeps_order(self) -> None:
        doc = apply_ops(self.doc, [_feature("f1"), _feature("f2", "k_cylinder")])
        self.assertEqual(doc.version, 1)
        self.assertEqual([item.id for item in doc.features], ["f1", "f2"])
        self.assertEqual(len(doc.history), 1)
        self.assertEqual(doc.milestones[-1].version, 1)
        self.assertEqual(doc.milestones[-1].parent_version, 0)

    def test_update_merges_params(self) -> None:
        doc = apply_ops(self.doc, [{
            "op": "add",
            "feature": {
                "id": "f1", "type": "k_box",
                "params": {"length": 30.0, "width": 5.0},
            },
        }])
        doc = apply_ops(doc, [{"op": "update", "id": "f1", "params": {"length": 40.0}}])
        self.assertEqual(doc.features[0].params["length"], 40.0)
        self.assertEqual(doc.features[0].params["width"], 5.0)

    def test_update_can_remove_ref(self) -> None:
        doc = apply_ops(self.doc, [{
            "op": "add",
            "feature": {"id": "f1", "type": "k_box", "refs": {}},
        }, {
            "op": "add",
            "feature": {
                "id": "f2", "type": "pattern", "params": {"kind": "linear"},
                "refs": {"target": ref_to_json(Ref("f1", "self"))},
            },
        }])
        doc = apply_ops(doc, [{"op": "update", "id": "f2", "refs": {"target": None}}])
        self.assertEqual(doc.features[1].refs, {})

    def test_remove_rejects_dangling_ref(self) -> None:
        doc = apply_ops(self.doc, [
            _feature("f1"),
            _feature("f2", "pattern", target=Ref("f1", "self")),
        ])
        with self.assertRaises(DocumentError) as caught:
            apply_ops(doc, [{"op": "remove", "id": "f1"}])
        self.assertEqual(caught.exception.code, "DANGLING_REF")

    def test_remove_sees_since_and_extra(self) -> None:
        doc = apply_ops(self.doc, [
            _feature("f1"),
            _feature("f2"),
            _feature("f3", "pattern",
                     target=Ref("f2", "self", extra=("f1",))),
        ])
        with self.assertRaises(DocumentError) as caught:
            apply_ops(doc, [{"op": "remove", "id": "f1"}])
        self.assertEqual(caught.exception.code, "DANGLING_REF")

    def test_forward_ref_is_rejected(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            apply_ops(self.doc, [_feature("f2", "pattern", target=Ref("f1", "self"))])
        self.assertEqual(caught.exception.code, "FORWARD_REF")

    def test_forward_since_or_extra_is_rejected(self) -> None:
        for ref in (Ref("f1", "faces", since=("f0",)),
                    Ref("f1", "faces", extra=("f0",))):
            with self.assertRaises(DocumentError) as caught:
                apply_ops(self.doc, [
                    _feature("f1", "k_box"),
                    _feature("f2", "pattern", target=ref),
                ])
            self.assertEqual(caught.exception.code, "FORWARD_REF")

    def test_duplicate_id_is_rejected(self) -> None:
        doc = apply_ops(self.doc, [_feature("f1")])
        with self.assertRaises(DocumentError) as caught:
            apply_ops(doc, [_feature("f1")])
        self.assertEqual(caught.exception.code, "DUPLICATE_ID")

    def test_stale_base_version_is_rejected(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            apply_ops(self.doc, [_feature("f1")], base_version=7)
        self.assertEqual(caught.exception.code, "STALE_VERSION")

    def test_failed_batch_leaves_document_untouched(self) -> None:
        doc = apply_ops(self.doc, [_feature("f1")])
        before = document_to_json(doc)
        with self.assertRaises(DocumentError):
            apply_ops(doc, [_feature("f2"), {"op": "remove", "id": "nope"}])
        self.assertEqual(document_to_json(doc), before)

    def test_reorder_keeps_valid_layout(self) -> None:
        doc = apply_ops(self.doc, [
            _feature("f1"),
            _feature("f2", "pattern", target=Ref("f1", "self")),
            _feature("f3"),
        ])
        moved = apply_ops(doc, [{"op": "reorder", "id": "f3", "before": "f1"}])
        self.assertEqual([item.id for item in moved.features], ["f3", "f1", "f2"])

    def test_reorder_that_breaks_refs_is_rejected(self) -> None:
        doc = apply_ops(self.doc, [
            _feature("f1"),
            _feature("f2", "pattern", target=Ref("f1", "self")),
        ])
        with self.assertRaises(DocumentError) as caught:
            apply_ops(doc, [{"op": "reorder", "id": "f2", "before": "f1"}])
        self.assertEqual(caught.exception.code, "FORWARD_REF")


class V2ValueRoundtripTests(unittest.TestCase):
    def setUp(self) -> None:
        self.doc = new_document("test", "d_test")

    def test_vector_and_points_params_roundtrip(self) -> None:
        doc = apply_ops(self.doc, [{
            "op": "add",
            "feature": {
                "id": "f1", "type": "k_polygon",
                "params": {
                    "points": [[0, 0], [10, 0], [10, 5]],
                    "direction": [0, 0, 1],
                },
            },
        }])
        self.assertEqual(doc.features[0].params["points"][1], [10, 0])
        restored = document_from_json(document_to_json(doc))
        self.assertEqual(restored.features[0].params["points"][2], [10, 5])
        self.assertEqual(restored.features[0].params["direction"], [0, 0, 1])
        self.assertEqual(document_to_json(restored), document_to_json(doc))

    def test_invalid_param_values_are_rejected(self) -> None:
        for bad in ({"nested": {"a": 1}}, [], [[]], [True, False]):
            with self.assertRaises(DocumentError) as caught:
                apply_ops(self.doc, [{
                    "op": "add",
                    "feature": {"id": "f1", "type": "k_box", "params": {"p": bad}},
                }])
            self.assertEqual(caught.exception.code, "INVALID_VALUE")

    def test_tuple_refs_roundtrip(self) -> None:
        doc = apply_ops(self.doc, [
            _feature("f1"),
            _feature("f2"),
            {"op": "add", "feature": {
                "id": "f3", "type": "k_loft",
                "refs": {"sections": [
                    ref_to_json(Ref("f1", "self")),
                    ref_to_json(Ref("f2", "self")),
                ]},
            }},
        ])
        refs = doc.features[2].refs["sections"]
        self.assertIsInstance(refs, tuple)
        self.assertEqual(len(refs), 2)
        restored = document_from_json(document_to_json(doc))
        self.assertIsInstance(restored.features[2].refs["sections"], tuple)
        self.assertEqual(restored.features[2].refs, doc.features[2].refs)
        self.assertEqual(document_to_json(restored), document_to_json(doc))

    def test_ref_since_and_extra_roundtrip(self) -> None:
        ref = Ref("f2", "faces",
                  filters=(Filter("nearest", args=([0.0, 0.0, 1.0],)),),
                  since=("f1",), extra=("f4",))
        payload = ref_to_json(ref)
        self.assertEqual(payload["since"], ["f1"])
        self.assertEqual(payload["extra"], ["f4"])
        self.assertEqual(ref_from_json(payload), ref)
        self.assertEqual(ref_to_json(ref_from_json(payload)), payload)

    def test_since_and_extra_survive_a_document_roundtrip(self) -> None:
        ref = Ref("f2", "faces", since=("f1",), extra=("f1",))
        doc = apply_ops(self.doc, [
            _feature("f1"),
            _feature("f2"),
            _feature("f3", "pattern", target=ref),
        ])
        stored = doc.features[2].refs["target"]
        self.assertEqual(stored.since, ("f1",))
        self.assertEqual(stored.extra, ("f1",))
        restored = document_from_json(document_to_json(doc))
        self.assertEqual(restored.features[2].refs["target"], ref)

    def test_feature_to_json_roundtrip_keeps_new_fields(self) -> None:
        feature = feature_from_json({
            "id": "f1",
            "type": "pattern",
            "params": {"count": 4},
            "refs": {
                "target": ref_to_json(Ref("f0", "self", since=("f9",), extra=("f8",))),
            },
        })
        self.assertEqual(feature.params, {"count": 4})
        self.assertEqual(feature_to_json(feature)["refs"]["target"]["since"], ["f9"])
        self.assertIsInstance(feature, Feature)


class MilestoneV2Tests(unittest.TestCase):
    def test_apply_records_plan_and_node_identity(self) -> None:
        doc = new_document("test", "d_test")
        doc = apply_ops(
            doc,
            [{"op": "add", "feature": {"id": "b1", "type": "k_box",
                                       "params": {"length": 10.0}}}],
            milestone_title="step one",
            plan_id="p_demo",
            node_id="n1",
        )
        latest = doc.milestones[-1]
        self.assertEqual(latest.plan_id, "p_demo")
        self.assertEqual(latest.node_id, "n1")
        self.assertEqual(latest.changed_features, ("b1",))

    def test_milestone_json_keeps_plan_and_node_identity(self) -> None:
        doc = new_document("test", "d_test")
        doc = apply_ops(
            doc,
            [{"op": "add", "feature": {"id": "b1", "type": "k_box"}}],
            plan_id="p_demo",
            node_id="n7",
        )
        latest = doc.milestones[-1]
        payload = milestone_to_json(latest)
        self.assertEqual(payload["plan_id"], "p_demo")
        self.assertEqual(payload["node_id"], "n7")
        self.assertEqual(milestone_from_json(payload), latest)
        restored = document_from_json(document_to_json(doc))
        self.assertEqual(restored.milestones[-1].plan_id, "p_demo")
        self.assertEqual(restored.milestones[-1].node_id, "n7")

    def test_milestone_without_plan_identity_is_null(self) -> None:
        doc = new_document("test", "d_test")
        doc = apply_ops(doc, [{"op": "add", "feature": {"id": "b1", "type": "k_box"}}])
        self.assertIsNone(doc.milestones[-1].plan_id)
        self.assertIsNone(doc.milestones[-1].node_id)
        restored = document_from_json(document_to_json(doc))
        self.assertIsNone(restored.milestones[-1].plan_id)


if __name__ == "__main__":
    unittest.main()
