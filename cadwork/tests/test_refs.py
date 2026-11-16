"""Tests for semantic reference resolution on generated actions."""

from __future__ import annotations

import unittest

from cadwork.design import build
from cadwork.design.build import BuildCache
from cadwork.design.document import Document, Feature, Filter, Ref
from cadwork.design.refs import RefError, count, resolve, single


def _box_document() -> Document:
    return Document(
        id="t",
        name="t",
        features=(
            Feature(
                "f1", "k_box", params={"length": 20.0, "width": 20.0, "height": 20.0}
            ),
        ),
    )


def _hole_document() -> Document:
    return Document(
        id="t",
        name="t",
        features=(
            Feature(
                "b1", "k_box", params={"length": 20.0, "width": 20.0, "height": 20.0}
            ),
            Feature("h1", "k_cylinder", params={"radius": 5.0, "height": 30.0}),
            Feature(
                "c1",
                "k_cut",
                refs={"target": Ref("b1", "self"), "others": (Ref("h1", "self"),)},
            ),
        ),
    )


class RefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = build(_box_document(), BuildCache())
        cls.outputs = cls.result.outputs

    def test_self_returns_the_part(self) -> None:
        part = resolve(Ref("f1", "self"), self.outputs)
        self.assertTrue(part.is_valid())

    def test_faces_returns_a_list(self) -> None:
        faces = resolve(Ref("f1", "faces"), self.outputs)
        self.assertEqual(count(faces), 6)

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


class RefCardinalityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.outputs = build(_box_document(), BuildCache()).outputs

    def test_one_returns_the_sole_element(self) -> None:
        face = resolve(Ref("f1", "faces", (Filter("top"), Filter("one"))), self.outputs)
        self.assertEqual(type(face).__name__, "Face")
        self.assertAlmostEqual(float(face.area), 400.0, places=3)

    def test_single_accepts_one_element(self) -> None:
        face = single(resolve(Ref("f1", "faces", (Filter("top"),)), self.outputs))
        self.assertAlmostEqual(float(face.area), 400.0, places=3)

    def test_edges_and_faces_convert(self) -> None:
        edges = resolve(Ref("f1", "faces", (Filter("edges"),)), self.outputs)
        self.assertEqual(count(edges), 12)
        faces = resolve(Ref("f1", "edges", (Filter("faces"),)), self.outputs)
        self.assertEqual(count(faces), 6)

    def test_hit_by_orders_by_distance(self) -> None:
        ref = Ref(
            "f1",
            "faces",
            (Filter("hit_by", args=([0.0, 0.0, 100.0], [0.0, 0.0, -1.0])),),
        )
        faces = list(resolve(ref, self.outputs))
        self.assertEqual(len(faces), 2)
        self.assertAlmostEqual(float(faces[0].center()[2]), 10.0, places=3)
        self.assertAlmostEqual(float(faces[1].center()[2]), -10.0, places=3)


class NewRefTests(unittest.TestCase):
    """``new(since=...)``, ``derived_from`` and ``joining`` via ``Ref`` fields."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.fillet_result = build(
            Document(
                id="t",
                name="t",
                features=(
                    Feature(
                        "f1",
                        "k_box",
                        params={"length": 20.0, "width": 20.0, "height": 20.0},
                    ),
                    Feature(
                        "f2",
                        "k_fillet",
                        params={"radius": 2.0},
                        refs={
                            "target": Ref("f1", "self"),
                            "edges": Ref(
                                "f1", "edges", (Filter("parallel_to", args=("Z",)),)
                            ),
                        },
                    ),
                ),
            ),
            BuildCache(),
        )
        cls.hole_result = build(_hole_document(), BuildCache())

    def test_new_returns_the_faces_made_by_the_operation(self) -> None:
        ref = Ref("f2", "faces", (Filter("new"),), since=("f1",))
        faces = resolve(ref, self.fillet_result.outputs)
        self.assertEqual(count(faces), 4)
        for face in faces:
            self.assertGreater(float(face.area), 0.0)

    def test_new_without_since_is_rejected(self) -> None:
        ref = Ref("f2", "faces", (Filter("new"),))
        with self.assertRaises(RefError) as caught:
            resolve(ref, self.fillet_result.outputs)
        self.assertEqual(caught.exception.code, "REF_INVALID_ARG")

    def test_derived_from_returns_the_cut_walls(self) -> None:
        ref = Ref("c1", "faces", (Filter("derived_from"),), extra=("h1",))
        faces = resolve(ref, self.hole_result.outputs)
        self.assertEqual(count(faces), 1)
        self.assertAlmostEqual(
            float(faces.first.area), 2 * 3.14159265 * 5 * 20, delta=2.0
        )

    def test_joining_returns_the_boolean_rims(self) -> None:
        ref = Ref("c1", "edges", (Filter("joining"),), extra=("b1", "h1"))
        edges = resolve(ref, self.hole_result.outputs)
        self.assertEqual(count(edges), 2)
        for edge in edges:
            self.assertAlmostEqual(float(edge.length), 2 * 3.14159265 * 5, delta=0.1)

    def test_new_since_and_joining_extra_are_independent_fields(self) -> None:
        ref = Ref("f2", "faces", since=("f1",), extra=("f1",))
        self.assertEqual(ref.since, ("f1",))
        self.assertEqual(ref.extra, ("f1",))


class TupleRefTests(unittest.TestCase):
    def test_a_many_role_resolves_every_tuple_member(self) -> None:
        document = Document(
            id="t",
            name="t",
            features=(
                Feature(
                    "a1",
                    "k_box",
                    params={"length": 10.0, "width": 10.0, "height": 10.0},
                ),
                Feature(
                    "a2",
                    "k_box",
                    params={"length": 10.0, "width": 10.0, "height": 10.0},
                ),
                Feature(
                    "a3",
                    "k_translate",
                    params={"x": 10.0},
                    refs={"target": Ref("a2", "self")},
                ),
                Feature(
                    "a4",
                    "k_fuse",
                    refs={"target": Ref("a1", "self"), "others": (Ref("a3", "self"),)},
                ),
            ),
        )
        result = build(document, BuildCache())
        self.assertAlmostEqual(float(result.final.volume), 2000.0, delta=1.0)


if __name__ == "__main__":
    unittest.main()
