"""Unit tests for Viewport scene and geometry projector."""

from __future__ import annotations

import json
import re
import unittest
from smlibpy import Box, Cylinder

from backend.adapters.viewport.projector import project_edges, project_faces, project_scene

INDEX_PATTERN = re.compile(r"\(\)\[[0-9]")


class TestViewportProjector(unittest.TestCase):
    def test_box_projection(self) -> None:
        box = Box(60, 40, 20)
        faces_data = project_faces(box)
        self.assertEqual(len(faces_data), 6)
        for f in faces_data:
            self.assertIn("vertices", f)
            self.assertIn("indices", f)
            self.assertIsNone(INDEX_PATTERN.search(f["selector"]))

        edges_data = project_edges(box)
        self.assertEqual(len(edges_data), 12)
        for e in edges_data:
            self.assertIn("points", e)
            self.assertIsNone(INDEX_PATTERN.search(e["selector"]))

        scene = project_scene(box)
        self.assertEqual(len(scene["bodies"]), 1)
        dumped = json.dumps(scene)
        self.assertIsInstance(dumped, str)

    def test_cylinder_projection(self) -> None:
        cyl = Cylinder(20, 50)
        scene = project_scene(cyl)
        self.assertEqual(len(scene["bodies"]), 1)
        body = scene["bodies"][0]
        self.assertEqual(len(body["faces"]), 3)
        self.assertIsInstance(json.dumps(scene), str)

    def test_none_geometry_projection(self) -> None:
        scene = project_scene(None)
        self.assertEqual(scene, {"bodies": []})


if __name__ == "__main__":
    unittest.main()
