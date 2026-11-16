"""Run plan nodes through the script backend, then commit the document."""

from __future__ import annotations

import tempfile
import unittest

from cadwork.design.document import Ref
from cadwork.design.plan import PlanNode
from cadwork.service.service import CADService
from cadwork.service.store import Store


class PlanScriptBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)
        self.service = CADService(self.store)
        self.document = self.store.create("script executor")
        self.addCleanup(self._close_backend)

    def _close_backend(self) -> None:
        if self.service._script_backend is not None:
            self.service._script_backend.close()

    def test_box_and_cut_run_on_the_script_backend(self) -> None:
        from cadwork.design.plan import plan_node_to_json

        nodes = [
            PlanNode(
                "plate",
                "feature",
                "plate",
                "k_box",
                params={"length": 20.0, "width": 20.0, "height": 20.0},
            ),
            PlanNode(
                "bore",
                "feature",
                "bore",
                "k_cylinder",
                params={"radius": 4.0, "height": 40.0},
            ),
            PlanNode(
                "cut",
                "feature",
                "cut the bore",
                "k_cut",
                refs={"target": Ref("plate", "self"), "others": (Ref("bore", "self"),)},
                deps=("plate", "bore"),
            ),
        ]
        self.service.plan_edit(
            self.document.id,
            [{"op": "add_node", "node": plan_node_to_json(node)} for node in nodes],
            goal="plate with a bore",
        )
        for node in nodes:
            self.service.plan_run(self.document.id, node.id, executor="script")
        current = self.store.get(self.document.id)
        self.assertEqual(current.version, 3)
        self.assertEqual(len(current.features), 3)
        state = self.service.state(self.document.id)
        self.assertAlmostEqual(state["metrics"]["volume"], 6994.69, delta=0.1)
        plan = state["plan"]
        self.assertEqual(plan["status"], "done")
