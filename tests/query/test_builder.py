"""Unit tests for Query builder and body summary generation."""

from __future__ import annotations

import json
import re
import unittest
from smlibpy import Box

from backend.query.builder import build_body
from backend.selector.resolver import SelectorResolver

INDEX_PATTERN = re.compile(r"\(\)\[[0-9]")


class TestQueryBuilder(unittest.TestCase):
    def test_box_query_building(self) -> None:
        box = Box(60, 40, 20)
        info = build_body(box)
        self.assertEqual(info.face_count, 6)
        self.assertEqual(info.edge_count, 12)
        self.assertTrue(info.is_valid)

        for face_info in info.faces:
            self.assertIsNone(INDEX_PATTERN.search(face_info.selector))
            resolved = SelectorResolver.resolve(box, face_info.selector)
            self.assertIsNotNone(resolved)

        d = info.to_dict()
        self.assertIsInstance(json.dumps(d), str)

    def test_none_geometry_query(self) -> None:
        info = build_body(None)
        self.assertEqual(info.face_count, 0)
        self.assertEqual(info.edge_count, 0)
        self.assertFalse(info.is_valid)


if __name__ == "__main__":
    unittest.main()
