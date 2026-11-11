"""Tests for geometry, reference, and spatial-pick probes."""

from __future__ import annotations

import unittest

from cadwork.design import build
from cadwork.design.document import Document, Feature, Filter, Ref
from cadwork.design.probe import pick_to_ref, probe_geometry, probe_ref


class ProbeGeometryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.doc = Document(
            id="d_probe",
            name="ProbeBox",
            version=1,
            features=(
                Feature("b1", "solid_box", params={"length": 40.0, "width": 20.0, "height": 10.0}),
            ),
        )
        self.result = build(self.doc)

    def test_bbox_and_mass_properties(self) -> None:
        info = probe_geometry(self.doc, self.result, "b1")
        self.assertFalse(info["empty"])
        self.assertEqual(info["feature_id"], "b1")
        self.assertAlmostEqual(info["mass"]["volume"], 8000.0, places=1)
        self.assertEqual(info["mass"]["faces"], 6)
        self.assertEqual(info["bbox"]["size"], [40.0, 20.0, 10.0])
        self.assertEqual(info["bbox"]["center"], [0.0, 0.0, 0.0])
        self.assertGreaterEqual(len(info["dominant_faces"]), 6)

    def test_probe_ref_hits_top_face(self) -> None:
        ref = Ref("b1", "faces", (Filter("top"),))
        res = probe_ref(self.result, ref)
        self.assertTrue(res["ok"])
        self.assertEqual(res["count"], 1)
        self.assertAlmostEqual(res["elements"][0]["area"], 800.0, places=1)
        self.assertAlmostEqual(res["elements"][0]["center"][2], 5.0, places=1)

    def test_probe_ref_invalid_source_reports_error(self) -> None:
        ref = Ref("missing", "faces", ())
        res = probe_ref(self.result, ref)
        self.assertFalse(res["ok"])
        self.assertEqual(res["code"], "REF_NOT_FOUND")

    def test_pick_to_ref_resolves_top_face(self) -> None:
        picked = pick_to_ref(
            self.doc,
            self.result,
            point=[1.0, -1.0, 5.0],
            normal=[0.0, 0.0, 1.0],
            area=800.0,
        )
        self.assertTrue(picked["ok"])
        self.assertEqual(picked["feature_id"], "b1")
        self.assertEqual(picked["orientation"], "top (+Z)")
        self.assertAlmostEqual(picked["area"], 800.0, places=1)
        ref_check = probe_ref(self.result, picked["suggested_ref"])
        self.assertTrue(ref_check["ok"])
        self.assertEqual(ref_check["count"], 1)


if __name__ == "__main__":
    unittest.main()
