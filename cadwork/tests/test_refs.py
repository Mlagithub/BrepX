"""Tests for semantic reference resolution."""

from __future__ import annotations

import unittest

from cadwork.design import build
from cadwork.design.build import BuildCache
from cadwork.design.document import Document, Feature, Filter, Ref
from cadwork.design.refs import RefError, count, resolve, single


def _hub_document() -> Document:
    return Document(
        id="t", name="t",
        features=(Feature("f1", "hub_revolve", params={"r_out": 20.0, "back_t": 3.0}),),
    )


class RefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = build(_hub_document(), BuildCache())
        cls.outputs = cls.result.outputs

    def test_self_returns_the_part(self) -> None:
        part = resolve(Ref("f1", "self"), self.outputs)
        self.assertTrue(part.is_valid())

    def test_faces_returns_a_list(self) -> None:
        faces = resolve(Ref("f1", "faces"), self.outputs)
        self.assertGreaterEqual(count(faces), 1)

    def test_nearest_converges_to_one(self) -> None:
        ref = Ref("f1", "faces", (Filter("nearest", args=([0.0, 0.0, 0.0],)),))
        face = single(resolve(ref, self.outputs))
        self.assertIsNotNone(face)

    def test_empty_selection_is_ref_empty(self) -> None:
        ref = Ref("f1", "edges", (Filter("concave"),))
        with self.assertRaises(RefError) as caught:
            single(resolve(ref, self.outputs))
        self.assertEqual(caught.exception.code, "REF_EMPTY")

    def test_ambiguous_selection_is_ref_ambiguous(self) -> None:
        ref = Ref("f1", "faces")
        with self.assertRaises(RefError) as caught:
            single(resolve(ref, self.outputs))
        self.assertEqual(caught.exception.code, "REF_AMBIGUOUS")

    def test_unknown_filter_is_rejected(self) -> None:
        ref = Ref("f1", "faces", (Filter("does_not_exist"),))
        with self.assertRaises(RefError) as caught:
            resolve(ref, self.outputs)
        self.assertEqual(caught.exception.code, "REF_UNSUPPORTED")

    def test_filter_on_empty_property_is_ref_empty(self) -> None:
        ref = Ref("f1", "edges", (Filter("concave"), Filter("first")))
        with self.assertRaises(RefError) as caught:
            resolve(ref, self.outputs)
        self.assertEqual(caught.exception.code, "REF_EMPTY")

    def test_missing_source_is_ref_not_found(self) -> None:
        with self.assertRaises(RefError) as caught:
            resolve(Ref("f9", "self"), self.outputs)
        self.assertEqual(caught.exception.code, "REF_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
