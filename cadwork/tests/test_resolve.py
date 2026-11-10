"""Naming features the way a person does, and resolving those names."""

from __future__ import annotations

import unittest

from cadwork.design.document import Document, Feature, Ref
from cadwork.service.resolve import resolve, summarize


def plate() -> Document:
    return Document(id="p", name="板", features=(
        Feature("h1", "solid_box",
                params={"length": 80, "width": 60, "height": 14}),
        Feature("h2", "hole",
                params={"x": -22, "y": 0, "diameter": 10, "depth": 0,
                        "kind": "counterbore", "cb_diameter": 18, "cb_depth": 6},
                refs={"target": Ref("h1", "self")}),
        Feature("h3", "hole",
                params={"x": 22, "y": 0, "diameter": 10, "depth": 0,
                        "kind": "countersink", "cs_diameter": 20, "cs_depth": 5},
                refs={"target": Ref("h2", "self")}),
    ))


class DescribeTests(unittest.TestCase):
    def test_features_are_named_in_plain_words(self) -> None:
        payload = summarize(plate())
        names = [entry["what"] for entry in payload["features"]]
        self.assertTrue(names[0].startswith("板"), names[0])
        self.assertIn("沉头孔", names[1])
        self.assertIn("Ø18", names[1])
        self.assertIn("沉孔", names[2])
        self.assertIn("Ø20", names[2])

    def test_summary_carries_the_editable_parameters(self) -> None:
        payload = summarize(plate())
        hole = payload["features"][1]
        self.assertEqual(hole["params"]["cb_diameter"], 18)
        self.assertEqual(hole["enabled"], True)
        self.assertIn("板", payload["vocabulary"])
        self.assertIn("沉头孔", payload["vocabulary"])


class ResolveTests(unittest.TestCase):
    def _top(self, phrase: str) -> dict:
        payload = resolve(plate(), phrase)
        self.assertTrue(payload["matches"], phrase)
        return payload

    def test_left_counterbore(self) -> None:
        payload = self._top("把左边的沉头改大一点")
        self.assertEqual(payload["matches"][0]["id"], "h2")
        self.assertTrue(payload["confident"])
        self.assertIsNone(payload["question"])

    def test_right_countersink(self) -> None:
        payload = self._top("右边那个沉孔再深两毫米")
        self.assertEqual(payload["matches"][0]["id"], "h3")
        self.assertTrue(payload["confident"])

    def test_bare_noun_is_ambiguous_and_asks(self) -> None:
        payload = self._top("把那个孔改大点")
        self.assertFalse(payload["confident"])
        self.assertIsNotNone(payload["question"])
        self.assertGreaterEqual(len(payload["matches"]), 2)

    def test_a_number_picks_one(self) -> None:
        payload = self._top("Ø20 那个孔")
        self.assertEqual(payload["matches"][0]["id"], "h3")
        self.assertTrue(payload["confident"])

    def test_the_last_thing_just_added(self) -> None:
        payload = self._top("最后那个再改一下")
        self.assertEqual(payload["matches"][0]["id"], "h3")
        self.assertTrue(payload["confident"])

    def test_the_plate_itself(self) -> None:
        payload = self._top("这块板厚一点")
        self.assertEqual(payload["matches"][0]["id"], "h1")
        self.assertTrue(payload["confident"])

    def test_nothing_matches_asks_back(self) -> None:
        payload = resolve(plate(), "把颜色改成蓝色")
        self.assertFalse(payload["confident"])
        self.assertFalse(payload["matches"])
        self.assertIn("没找到", payload["question"])


if __name__ == "__main__":
    unittest.main()
