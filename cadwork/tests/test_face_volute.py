"""A spiral body placed on a picked planar face, then fused and checked."""

from __future__ import annotations

import tempfile
import unittest

from cadwork.design.document import Filter, Ref
from cadwork.design.plan import Expect, PlanNode, plan_node_to_json
from cadwork.service.service import CADService, ServiceError
from cadwork.service.store import Store

FACE_POINT = [0.0, 0.0, 10.0]


def _placed(planar: bool = True) -> PlanNode:
    filters = [Filter("nearest", args=(FACE_POINT,))]
    if planar:
        filters.insert(0, Filter("planar"))
    return PlanNode(
        "placed", "feature", "spiral on the top face", "place_on",
        refs={
            "shape": Ref("spiral", "self"),
            "face": Ref("base", "faces", tuple(filters)),
        },
        deps=("spiral", "base"),
    )


def _nodes(planar: bool = True) -> list[PlanNode]:
    return [
        PlanNode("base", "feature", "plate", "k_box",
                 params={"length": 80.0, "width": 80.0, "height": 20.0}),
        PlanNode("spiral", "feature", "spiral path", "k_spiral",
                 params={"start_radius": 8.0, "end_radius": 24.0, "turns": 2.0,
                         "plane": "XY", "clockwise": False}),
        _placed(planar),
        PlanNode("section", "feature", "round section", "k_circle",
                 params={"radius": 2.0}),
        PlanNode("swept", "feature", "growing sweep", "k_sweep",
                 params={"orient": True, "translational": False, "twist": 0.0,
                         "scale_start": 0.5, "scale_end": 1.2},
                 refs={"profile": Ref("section", "self"),
                       "path": Ref("placed", "self")},
                 deps=("section", "placed")),
        PlanNode("joined", "feature", "fuse the volute", "k_fuse",
                 refs={"target": Ref("base", "self"),
                       "others": (Ref("swept", "self"),)},
                 deps=("base", "swept")),
        PlanNode("check", "check", "one watertight body", deps=("joined",),
                 expect=(Expect("solids", "eq", 1),
                         Expect("watertight", "true"))),
    ]


class FaceAnchoredVoluteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)
        self.service = CADService(self.store)
        self.document = self.store.create("face-anchored volute")

    def _add(self, nodes: list[PlanNode]) -> None:
        self.service.plan_edit(
            self.document.id,
            [{"op": "add_node", "node": plan_node_to_json(node)} for node in nodes],
            goal="a spiral body on a picked face",
        )

    def test_place_on_face_then_boolean(self) -> None:
        nodes = _nodes()
        self._add(nodes)
        for node in nodes:
            self.service.plan_run(self.document.id, node.id)
        current = self.store.get(self.document.id)
        self.assertEqual([feature.id for feature in current.features],
                         ["base", "spiral", "placed", "section", "swept", "joined"])
        report = self.service.checks(self.document.id)
        self.assertTrue(all(check["ok"] for item in report["features"]
                            for check in item["checks"]))
        plan = self.service.plan(self.document.id)["plan"]
        self.assertEqual(plan["status"], "done")
        self.assertEqual(len(plan["nodes"]), 7)

    def test_non_planar_face_is_rejected_without_a_write(self) -> None:
        nodes = [
            PlanNode("base", "feature", "cylinder", "k_cylinder",
                     params={"radius": 40.0, "height": 20.0}),
            PlanNode("spiral", "feature", "spiral path", "k_spiral",
                     params={"start_radius": 8.0, "end_radius": 24.0, "turns": 2.0,
                             "plane": "XY", "clockwise": False}),
            PlanNode("placed", "feature", "spiral on the side", "place_on",
                     refs={"shape": Ref("spiral", "self"),
                           "face": Ref("base", "faces", (
                               Filter("nearest", args=([40.0, 0.0, 0.0],)),
                           ))},
                     deps=("spiral", "base")),
        ]
        self._add(nodes)
        self.service.plan_run(self.document.id, "base")
        self.service.plan_run(self.document.id, "spiral")
        version = self.store.get(self.document.id).version
        with self.assertRaises(ServiceError):
            self.service.plan_run(self.document.id, "placed")
        self.assertEqual(self.store.get(self.document.id).version, version)
