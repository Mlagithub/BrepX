"""Generic adapter features: batch blends, threads and stepped bores."""

from __future__ import annotations

import unittest

from cadwork import smlib as S
from cadwork.design.features import FEATURES


class BlendGroupTests(unittest.TestCase):
    def test_batch_chamfer_of_a_box(self) -> None:
        box = S.Box(40.0, 30.0, 20.0)
        edges = box.edges().parallel_to(S.Z)
        output = FEATURES["blend_group"].build(
            {"target": box, "edges": edges},
            {"kind": "chamfer", "size": 2.0, "propagate": True, "on_failure": "fail"},
        )
        self.assertEqual(output.meta["blend"]["applied"], 4)
        self.assertEqual(output.meta["blend"]["skipped"], 0)
        self.assertTrue(output.value.is_valid())
        self.assertEqual(len(output.value.solids()), 1)

    def test_batch_fillet_of_a_box(self) -> None:
        box = S.Box(40.0, 30.0, 20.0)
        edges = box.edges().parallel_to(S.Z)
        output = FEATURES["blend_group"].build(
            {"target": box, "edges": edges},
            {"kind": "fillet", "size": 3.0, "propagate": True, "on_failure": "fail"},
        )
        self.assertEqual(output.meta["blend"]["applied"], 4)
        self.assertTrue(output.value.is_valid())


class ThreadTests(unittest.TestCase):
    def test_thread_tool_and_cut(self) -> None:
        params = {"diameter": 12.0, "pitch": 1.75, "length": 20.0,
                  "depth": 1.0, "center": [0.0, 0.0, 0.0], "left_handed": False}
        tool = FEATURES["thread"].build({}, params)
        self.assertTrue(tool.value.is_valid())
        self.assertGreater(tool.value.volume, 0.0)
        rod = S.Cylinder(6.0, 60.0)
        cut = FEATURES["thread"].build({"target": rod}, params)
        self.assertTrue(cut.value.is_valid())
        self.assertEqual(len(cut.value.solids()), 1)
        self.assertLess(cut.value.volume, rod.volume)


class SteppedBoreTests(unittest.TestCase):
    def test_three_axis_stepped_bores(self) -> None:
        for axis, center in (("Z", [0.0, 0.0, 10.0]),
                             ("X", [0.0, 0.0, 0.0]),
                             ("Y", [0.0, 0.0, 0.0])):
            block = S.Box(60.0, 50.0, 30.0)
            output = FEATURES["stepped_bore"].build(
                {"target": block},
                {"diameter_1": 18.0, "depth_1": 6.0,
                 "diameter_2": 10.0, "through": True,
                 "center": center, "axis": axis},
            )
            with self.subTest(axis=axis):
                self.assertTrue(output.value.is_valid())
                self.assertEqual(len(output.value.solids()), 1)
                self.assertLess(output.value.volume, block.volume)
