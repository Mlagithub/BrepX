"""Unit tests for canonical selector generation and roundtrip resolution."""

from __future__ import annotations

import re
import unittest
from smlibpy import Box, Cylinder

from backend.selector.canonicalizer import canonicalize_edge, canonicalize_face
from backend.selector.resolver import SelectorResolver

INDEX_REGEX = re.compile(r"\(\)\[[0-9]")


class TestCanonicalizer(unittest.TestCase):
    def test_box_face_and_edge_roundtrip(self) -> None:
        box = Box(60, 40, 20)
        for face in box.faces():
            sel = canonicalize_face(face, box)
            self.assertIsNone(INDEX_REGEX.search(sel))
            resolved = SelectorResolver.resolve(box, sel)
            self.assertEqual(resolved, face)

        for edge in box.edges():
            sel = canonicalize_edge(edge, box)
            self.assertIsNone(INDEX_REGEX.search(sel))

    def test_cylinder_roundtrip(self) -> None:
        cyl = Cylinder(20, 50)
        for face in cyl.faces():
            sel = canonicalize_face(face, cyl)
            self.assertIsNone(INDEX_REGEX.search(sel))
            resolved = SelectorResolver.resolve(cyl, sel)
            self.assertEqual(resolved, face)


if __name__ == "__main__":
    unittest.main()
