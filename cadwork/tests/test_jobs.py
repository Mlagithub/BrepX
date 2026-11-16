"""Async plan jobs and failed-node state for the browser workbench."""

from __future__ import annotations

import tempfile
import time
import unittest

from cadwork.design.document import Filter, Ref
from cadwork.design.plan import Expect, PlanNode, plan_node_to_json
from cadwork.service.jobs import PlanJobRegistry
from cadwork.service.service import CADService, ServiceError
from cadwork.service.store import Store


class _SlowService:
    def plan_run(
        self, document_id, node_id, base_version=None, executor=None, cancel_event=None
    ):
        time.sleep(0.15)
        if cancel_event is not None and cancel_event.is_set():
            raise ServiceError("CANCELLED", "cancelled", status=409)
        return {"document_id": document_id, "node": node_id}


class JobTests(unittest.TestCase):
    def test_job_completes(self) -> None:
        registry = PlanJobRegistry(_SlowService())  # type: ignore[arg-type]
        job = registry.start("doc", "node")
        for _ in range(40):
            current = registry.get(job.job_id)
            if current and current.status == "done":
                break
            time.sleep(0.02)
        self.assertEqual(registry.get(job.job_id).status, "done")

    def test_job_can_be_cancelled_before_commit(self) -> None:
        registry = PlanJobRegistry(_SlowService())  # type: ignore[arg-type]
        job = registry.start("doc", "node")
        time.sleep(0.03)
        registry.cancel(job.job_id)
        for _ in range(50):
            current = registry.get(job.job_id)
            if current and current.status == "cancelled":
                break
            time.sleep(0.02)
        self.assertEqual(registry.get(job.job_id).status, "cancelled")


class FailedNodeTests(unittest.TestCase):
    def test_build_failure_marks_the_node_failed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            service = CADService(Store(folder))
            document = service.store.create("failed node")
            nodes = [
                PlanNode(
                    "box",
                    "feature",
                    "box",
                    "k_box",
                    {"length": 40.0, "width": 40.0, "height": 20.0},
                ),
                PlanNode(
                    "fillet",
                    "feature",
                    "bad fillet",
                    "k_fillet",
                    {"radius": 100.0},
                    {
                        "target": Ref("box", "self"),
                        "edges": Ref(
                            "box",
                            "edges",
                            (Filter("nearest", args=([0.0, 0.0, 10.0],)),),
                        ),
                    },
                    ("box",),
                ),
                PlanNode(
                    "check",
                    "check",
                    "final",
                    "",
                    deps=("fillet",),
                    expect=(Expect("solids", "eq", 1),),
                ),
            ]
            service.plan_edit(
                document.id,
                [{"op": "add_node", "node": plan_node_to_json(node)} for node in nodes],
                goal="failure",
            )
            service.plan_run(document.id, "box")
            with self.assertRaises(ServiceError):
                service.plan_run(document.id, "fillet")
            plan = service.plan(document.id)["plan"]
            failed = next(node for node in plan["nodes"] if node["id"] == "fillet")
            self.assertEqual(failed["status"], "failed")
            self.assertIn("BUILD_FAILED", failed["error"])
            self.assertEqual(service.read(document.id).version, 1)
