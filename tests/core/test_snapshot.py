"""Unit tests for geometry snapshot store, eviction, and integration."""

from __future__ import annotations

import unittest

import backend.kernel.ops_primitives
from backend.core.command import Command
from backend.core.design import Design
from backend.core.pipeline import submit, undo
from backend.core.snapshot import (
    MAX_SNAPSHOTS,
    SNAPSHOT_EVERY,
    SnapshotStore,
    should_snapshot,
)
from backend.kernel.registry import default_registry


class TestSnapshot(unittest.TestCase):
    def test_trigger_policy(self) -> None:
        self.assertTrue(should_snapshot(1))
        self.assertFalse(should_snapshot(2))
        self.assertFalse(should_snapshot(3))
        self.assertFalse(should_snapshot(4))
        self.assertTrue(should_snapshot(5))
        self.assertTrue(should_snapshot(10))
        self.assertEqual(SNAPSHOT_EVERY, 5)

    def test_store_and_get_below(self) -> None:
        store = SnapshotStore(capacity=5)
        self.assertIsNone(store.get_below(10))

        store.put(1, "geom_1")
        store.put(5, "geom_5")
        store.put(10, "geom_10")

        self.assertEqual(store.get_below(4), (1, "geom_1"))
        self.assertEqual(store.get_below(5), (5, "geom_5"))
        self.assertEqual(store.get_below(9), (5, "geom_5"))
        self.assertEqual(store.get_below(10), (10, "geom_10"))
        self.assertEqual(store.get_below(100), (10, "geom_10"))

    def test_lru_eviction(self) -> None:
        store = SnapshotStore(capacity=3)
        store.put(1, "g1")
        store.put(2, "g2")
        store.put(3, "g3")
        self.assertEqual(store.versions(), [1, 2, 3])

        store.get_below(1)

        store.put(4, "g4")
        self.assertEqual(store.versions(), [1, 3, 4])

    def test_pipeline_integration_and_undo_retention(self) -> None:
        reg = default_registry()
        d = Design.empty()
        self.assertEqual(len(d.snapshots), 0)

        for i in range(1, 6):
            cmd = Command.from_payload({
                "command_id": f"c_{i}",
                "op": "box",
                "params": {"length": 10.0 + i, "width": 10.0, "height": 10.0},
                "idempotency_key": f"k_snap_{i}",
            })
            d = submit(d, cmd, reg)

        self.assertIn(5, d.snapshots.versions())

        d_undo = undo(d, reg)
        self.assertIn(5, d_undo.snapshots.versions())


if __name__ == "__main__":
    unittest.main()
