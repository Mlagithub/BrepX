"""Tests for the document model: edits are atomic and always produce a new value."""

from __future__ import annotations

import unittest

from cadwork.design.document import (
    Document,
    DocumentError,
    Feature,
    Ref,
    apply_ops,
    document_from_json,
    document_to_json,
    new_document,
)


def _feature(feature_id: str, feature_type: str = "hub_revolve", **refs: Ref) -> dict:
    return {
        "op": "add",
        "feature": {
            "id": feature_id,
            "type": feature_type,
            "params": {},
            "refs": {role: _ref_json(ref) for role, ref in refs.items()},
        },
    }


def _ref_json(ref: Ref) -> dict:
    from cadwork.design.document import ref_to_json

    return ref_to_json(ref)


class DocumentEditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.doc = new_document("test", "d_test")

    def test_new_document_is_empty(self) -> None:
        self.assertEqual(self.doc.version, 1)
        self.assertEqual(self.doc.features, ())

    def test_add_bumps_version_and_keeps_order(self) -> None:
        doc = apply_ops(self.doc, [_feature("f1"), _feature("f2", "blade_loft")])
        self.assertEqual(doc.version, 2)
        self.assertEqual([item.id for item in doc.features], ["f1", "f2"])
        self.assertEqual(len(doc.history), 1)

    def test_update_merges_params(self) -> None:
        doc = apply_ops(self.doc, [{
            "op": "add",
            "feature": {
                "id": "f1", "type": "hub_revolve",
                "params": {"r_out": 30.0, "back_t": 5.0},
            },
        }])
        doc = apply_ops(doc, [{"op": "update", "id": "f1", "params": {"r_out": 40.0}}])
        self.assertEqual(doc.features[0].params["r_out"], 40.0)
        self.assertEqual(doc.features[0].params["back_t"], 5.0)

    def test_update_can_remove_ref(self) -> None:
        doc = apply_ops(self.doc, [{
            "op": "add",
            "feature": {
                "id": "f1", "type": "hub_revolve",
                "refs": {},
            },
        }, {
            "op": "add",
            "feature": {
                "id": "f2", "type": "boolean", "params": {"kind": "join"},
                "refs": {"target": _ref_json(Ref("f1", "self"))},
            },
        }])
        doc = apply_ops(doc, [{"op": "update", "id": "f2", "refs": {"target": None}}])
        self.assertEqual(doc.features[1].refs, {})

    def test_remove_rejects_dangling_ref(self) -> None:
        doc = apply_ops(self.doc, [
            _feature("f1"),
            _feature("f2", "pattern_circular", target=Ref("f1", "self")),
        ])
        with self.assertRaises(DocumentError) as caught:
            apply_ops(doc, [{"op": "remove", "id": "f1"}])
        self.assertEqual(caught.exception.code, "DANGLING_REF")

    def test_forward_ref_is_rejected(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            apply_ops(self.doc, [_feature("f2", "pattern_circular", target=Ref("f1", "self"))])
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
            _feature("f2", "pattern_circular", target=Ref("f1", "self")),
            _feature("f3"),
        ])
        moved = apply_ops(doc, [{"op": "reorder", "id": "f3", "before": "f1"}])
        self.assertEqual([item.id for item in moved.features], ["f3", "f1", "f2"])

    def test_reorder_that_breaks_refs_is_rejected(self) -> None:
        doc = apply_ops(self.doc, [
            _feature("f1"),
            _feature("f2", "pattern_circular", target=Ref("f1", "self")),
        ])
        with self.assertRaises(DocumentError) as caught:
            apply_ops(doc, [{"op": "reorder", "id": "f2", "before": "f1"}])
        self.assertEqual(caught.exception.code, "FORWARD_REF")

    def test_json_roundtrip(self) -> None:
        doc = apply_ops(self.doc, [
            _feature("f1"),
            _feature("f2", "pattern_circular", target=Ref("f1", "self")),
        ])
        restored = document_from_json(document_to_json(doc))
        self.assertEqual(document_to_json(restored), document_to_json(doc))


if __name__ == "__main__":
    unittest.main()
