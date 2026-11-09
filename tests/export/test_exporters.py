"""Unit tests for STEP, STL, DXF, and CFD dictionary exporters."""

from __future__ import annotations

import json
import unittest
from smlibpy import Box

from backend.adapters.export.exporters import (
    ExportError,
    export_cfd_dict,
    export_dxf,
    export_step,
    export_stl,
)
from backend.core.patches import create_patch


class TestExporters(unittest.TestCase):
    def setUp(self) -> None:
        self.box = Box(60, 40, 20)

    def test_step_export_non_empty(self) -> None:
        data = export_step(self.box)
        self.assertGreater(len(data), 100)
        self.assertTrue(data.startswith(b"ISO-10303-21") or b"FILE_SCHEMA" in data)

    def test_stl_export_non_empty(self) -> None:
        data = export_stl(self.box)
        self.assertGreater(len(data), 80)

    def test_dxf_export_non_empty(self) -> None:
        data = export_dxf(self.box, plane_name="XY")
        self.assertGreater(len(data), 100)

    def test_cfd_dict_valid_json_and_utf8(self) -> None:
        p1 = create_patch("p1", "inlet_main", "inlet", "faces().facing(Z)", 2400.0)
        p2 = create_patch("p2", "wall_casing", "wall", "faces().facing(X)", 800.0)
        raw_bytes = export_cfd_dict([p1, p2])

        text = raw_bytes.decode("utf-8")
        parsed = json.loads(text)
        self.assertEqual(parsed["boundary_count"], 2)
        self.assertEqual(parsed["boundaries"][0]["name"], "inlet_main")

    def test_none_geometry_raises_export_error(self) -> None:
        with self.assertRaises(ExportError):
            export_step(None)
        with self.assertRaises(ExportError):
            export_stl(None)
        with self.assertRaises(ExportError):
            export_dxf(None)


if __name__ == "__main__":
    unittest.main()
