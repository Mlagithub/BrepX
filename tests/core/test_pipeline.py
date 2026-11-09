"""Unit tests for Command pipeline execution, verification, idempotency and undo/redo."""

from __future__ import annotations

import unittest

import backend.kernel.ops_features
import backend.kernel.ops_primitives
from backend.core.command import Command
from backend.core.design import Design
from backend.core.errors import (
    OperatorNotFoundError,
    ParamRangeError,
    ParamTypeError,
    PostconditionError,
    PreconditionError,
)
from backend.core.pipeline import redo, submit, undo
from backend.kernel.registry import default_registry
from backend.selector.errors import SelectorResolutionError


class TestPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = default_registry()
        self.design = Design.empty()

    def test_box_and_hole_success_flow(self) -> None:
        cmd_box = Command.from_payload({
            "command_id": "c1",
            "op": "box",
            "params": {"length": 60.0, "width": 40.0, "height": 20.0},
            "idempotency_key": "k_box_1",
        })
        d1 = submit(self.design, cmd_box, self.registry)
        self.assertEqual(d1.version, 2)
        self.assertEqual(len(d1.journal), 1)
        self.assertIsNotNone(d1.geometry)

        cmd_hole = Command.from_payload({
            "command_id": "c2",
            "op": "hole",
            "target": {"base": "prev", "expr": "faces().top()"},
            "params": {"radius": 6.0, "depth": 40.0},
            "idempotency_key": "k_hole_1",
        })
        d2 = submit(d1, cmd_hole, self.registry)
        self.assertEqual(d2.version, 3)
        self.assertEqual(len(d2.journal), 2)
        self.assertLess(d2.geometry.volume, d1.geometry.volume)

    def test_failure_leaves_design_completely_unmodified(self) -> None:
        cmd_box = Command.from_payload({
            "command_id": "c1",
            "op": "box",
            "params": {"length": 60.0, "width": 40.0, "height": 20.0},
            "idempotency_key": "k_box_base",
        })
        d_base = submit(self.design, cmd_box, self.registry)

        cmd_unknown_op = Command.from_payload({
            "command_id": "c_err_1",
            "op": "non_existent_op",
            "params": {},
            "idempotency_key": "k_err_1",
        })
        with self.assertRaises(OperatorNotFoundError):
            submit(d_base, cmd_unknown_op, self.registry)
        self.assertEqual(d_base.version, 2)
        self.assertEqual(len(d_base.journal), 1)

        cmd_bad_param = Command.from_payload({
            "command_id": "c_err_2",
            "op": "hole",
            "target": {"base": "prev", "expr": "faces().top()"},
            "params": {"radius": -5.0, "depth": 40.0},
            "idempotency_key": "k_err_2",
        })
        with self.assertRaises(ParamRangeError):
            submit(d_base, cmd_bad_param, self.registry)
        self.assertEqual(d_base.version, 2)

        cmd_bad_selector = Command.from_payload({
            "command_id": "c_err_3",
            "op": "hole",
            "target": {"base": "prev", "expr": "faces().cylinders()"},
            "params": {"radius": 6.0, "depth": 40.0},
            "idempotency_key": "k_err_3",
        })
        with self.assertRaises(SelectorResolutionError):
            submit(d_base, cmd_bad_selector, self.registry)
        self.assertEqual(d_base.version, 2)

        cmd_failed_assertion = Command.from_payload({
            "command_id": "c_err_4",
            "op": "hole",
            "target": {"base": "prev", "expr": "faces().top()"},
            "params": {"radius": 6.0, "depth": 40.0},
            "expect": [{"name": "volume_delta_sign", "args": [1]}],
            "idempotency_key": "k_err_4",
        })
        with self.assertRaises(PostconditionError):
            submit(d_base, cmd_failed_assertion, self.registry)
        self.assertEqual(d_base.version, 2)

    def test_idempotency_deduplication(self) -> None:
        cmd_box = Command.from_payload({
            "command_id": "c1",
            "op": "box",
            "params": {"length": 60.0, "width": 40.0, "height": 20.0},
            "idempotency_key": "k_idem_1",
        })
        d1 = submit(self.design, cmd_box, self.registry)
        self.assertEqual(d1.version, 2)

        d1_dup = submit(d1, cmd_box, self.registry)
        self.assertEqual(d1_dup.version, 2)
        self.assertEqual(len(d1_dup.journal), 1)

    def test_undo_and_redo_cycle(self) -> None:
        cmd_box = Command.from_payload({
            "command_id": "c1",
            "op": "box",
            "params": {"length": 60.0, "width": 40.0, "height": 20.0},
            "idempotency_key": "k_undo_1",
        })
        d1 = submit(self.design, cmd_box, self.registry)

        cmd_hole = Command.from_payload({
            "command_id": "c2",
            "op": "hole",
            "target": {"base": "prev", "expr": "faces().top()"},
            "params": {"radius": 6.0, "depth": 40.0},
            "idempotency_key": "k_undo_2",
        })
        d2 = submit(d1, cmd_hole, self.registry)

        d_undo = undo(d2, self.registry)
        self.assertEqual(d_undo.version, 4)
        self.assertEqual(len(d_undo.journal), 1)
        self.assertAlmostEqual(d_undo.geometry.volume, d1.geometry.volume, delta=1e-3)

        d_redo = redo(d_undo, self.registry)
        self.assertEqual(d_redo.version, 5)
        self.assertEqual(len(d_redo.journal), 2)
        self.assertAlmostEqual(d_redo.geometry.volume, d2.geometry.volume, delta=1e-3)

    def test_target_command_on_empty_design_raises_precondition_error(self) -> None:
        cmd_hole = Command.from_payload({
            "command_id": "c1",
            "op": "hole",
            "target": {"base": "prev", "expr": "faces().top()"},
            "params": {"radius": 6.0, "depth": 40.0},
            "idempotency_key": "k_empty_1",
        })
        with self.assertRaises(PreconditionError):
            submit(self.design, cmd_hole, self.registry)


if __name__ == "__main__":
    unittest.main()
