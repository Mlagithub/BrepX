"""Unit tests for Command, SelectorRef, Assertions and CommandRecord contracts."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from backend.core.command import (
    Assertion,
    Command,
    CommandRecord,
    SelectorRef,
    bbox_within,
    face_count_delta,
    is_solid,
    is_valid,
    no_degenerate_faces,
    volume_delta_sign,
    volume_gt,
)


class TestCommandContracts(unittest.TestCase):
    def test_selector_ref_valid_and_frozen(self) -> None:
        ref = SelectorRef(base="prev", expr="faces().facing(Z)")
        self.assertEqual(ref.base, "prev")
        self.assertEqual(ref.expr, "faces().facing(Z)")

        with self.assertRaises(FrozenInstanceError):
            ref.base = "c1"

        with self.assertRaises(ValueError):
            SelectorRef(base="invalid_base", expr="faces().top()")

        with self.assertRaises(ValueError):
            SelectorRef(base="prev", expr="faces()[0]")

    def test_assertion_factories(self) -> None:
        self.assertEqual(is_valid().name, "is_valid")
        self.assertEqual(is_solid().name, "is_solid")
        self.assertEqual(volume_gt(10.5).args, (10.5,))
        self.assertEqual(volume_delta_sign(-1).args, (-1,))
        with self.assertRaises(ValueError):
            volume_delta_sign(2)
        self.assertEqual(face_count_delta(2).args, (2,))
        self.assertEqual(no_degenerate_faces(1e-4).args, (1e-4,))
        self.assertEqual(bbox_within((0, 0, 0, 10, 10, 10)).args, (0.0, 0.0, 0.0, 10.0, 10.0, 10.0))

    def test_command_creation_and_payload_roundtrip(self) -> None:
        cmd = Command(
            command_id="c1",
            op="box",
            target=None,
            tool=None,
            params={"length": 10.0, "name": "cube"},
            expect=(is_solid(),),
            idempotency_key="cube_gen_1",
        )
        self.assertEqual(cmd.op, "box")
        self.assertEqual(cmd.params["length"], 10.0)

        with self.assertRaises(ValueError):
            Command(
                command_id="c2",
                op="box",
                target=None,
                tool=None,
                params={"invalid_obj": [1, 2, 3]},
                expect=(),
                idempotency_key="k2",
            )

        payload = {
            "command_id": "c3",
            "op": "extrude",
            "target": {"base": "prev", "expr": "faces().top()"},
            "params": {"height": 5.0},
            "expect": [{"name": "volume_delta_sign", "args": [1]}],
            "idempotency_key": "extrude_1",
        }
        deserialized = Command.from_payload(payload)
        self.assertIsNotNone(deserialized.target)
        self.assertEqual(deserialized.target.expr, "faces().top()")
        self.assertEqual(len(deserialized.expect), 1)

    def test_command_record_validation(self) -> None:
        cmd = Command(
            command_id="c1",
            op="box",
            target=None,
            tool=None,
            params={},
            expect=(),
            idempotency_key="k1",
        )
        with self.assertRaises(ValueError):
            CommandRecord(cmd, 1, {"volume": 10.0})

        record = CommandRecord(cmd, 1, {"volume": 10.0, "face_count": 6, "is_valid": True})
        self.assertEqual(record.version, 1)


if __name__ == "__main__":
    unittest.main()
