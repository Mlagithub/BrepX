"""Unit tests for incremental rebuild engine, dirty propagation and failure isolation."""

from __future__ import annotations

import unittest

import backend.kernel.ops_features
import backend.kernel.ops_primitives
from backend.core.command import Command
from backend.core.design import Design
from backend.core.pipeline import submit
from backend.core.rebuild import rebuild, verify_determinism
from backend.kernel.registry import default_registry


class TestRebuild(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = default_registry()
        d = Design.empty()
        c1 = Command.from_payload({
            "command_id": "c1",
            "op": "box",
            "params": {"length": 60.0, "width": 40.0, "height": 20.0},
            "idempotency_key": "k1",
        })
        c2 = Command.from_payload({
            "command_id": "c2",
            "op": "hole",
            "target": {"base": "prev", "expr": "faces().top()"},
            "params": {"radius": 6.0, "depth": 40.0},
            "idempotency_key": "k2",
        })
        c3 = Command.from_payload({
            "command_id": "c3",
            "op": "shell",
            "target": {"base": "prev", "expr": "faces().bottom()"},
            "params": {"thickness": 2.0},
            "idempotency_key": "k3",
        })
        self.design = submit(submit(submit(d, c1, self.registry), c2, self.registry), c3, self.registry)

    def test_rebuild_leaf_node_only_recomputes_leaf(self) -> None:
        res = rebuild(self.design, "c3", self.registry, new_params={"thickness": 1.0})
        self.assertTrue(res.ok)
        self.assertEqual(res.succeeded, ["c1", "c2", "c3"])
        self.assertIsNotNone(res.design)

    def test_rebuild_root_node_updates_entire_pipeline(self) -> None:
        res = rebuild(self.design, "c1", self.registry, new_params={"length": 80.0})
        self.assertTrue(res.ok)
        self.assertEqual(res.succeeded, ["c1", "c2", "c3"])
        self.assertGreater(res.design.geometry.volume, self.design.geometry.volume)

    def test_intermediate_failure_blocks_downstream_and_preserves_upstream(self) -> None:
        res = rebuild(self.design, "c2", self.registry, new_params={"radius": -10.0})
        self.assertFalse(res.ok)
        self.assertIsNotNone(res.failed)
        failed_id, diag = res.failed
        self.assertEqual(failed_id, "c2")
        self.assertEqual(diag["error"], "ParamRangeError")
        self.assertIn("c3", res.blocked)
        self.assertEqual(res.succeeded, ["c1"])

        diag_dict = res.to_diagnostic()
        self.assertFalse(diag_dict["ok"])
        self.assertEqual(diag_dict["failed_command"], "c2")
        self.assertIn("c3", diag_dict["blocked_downstream"])

    def test_verify_determinism_consistency(self) -> None:
        self.assertTrue(verify_determinism(self.design, self.registry))


if __name__ == "__main__":
    unittest.main()
