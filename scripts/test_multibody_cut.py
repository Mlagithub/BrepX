"""Test resolving multi-body selector expressions."""

from __future__ import annotations

import backend.kernel.ops_patterns
import backend.kernel.ops_primitives
from backend.core.command import Command
from backend.core.design import Design
from backend.core.pipeline import resolve_command_targets, submit
from backend.kernel import smlib_bridge
from backend.kernel.registry import default_registry


def test() -> None:
    reg = default_registry()
    d = Design.empty()
    d = submit(
        d,
        Command.from_payload({
            "command_id": "c1",
            "op": "box",
            "params": {"length": 60.0, "width": 40.0, "height": 20.0},
            "idempotency_key": "k1",
        }),
        reg,
    )
    d = submit(
        d,
        Command.from_payload({
            "command_id": "c2",
            "op": "cylinder",
            "params": {"radius": 15.0, "height": 50.0},
            "idempotency_key": "k2",
        }),
        reg,
    )
    print("Design bodies:", list(d.bodies.keys()))

    cmd_cut = Command.from_payload({
        "command_id": "c3",
        "op": "boolean_cut",
        "target": {"base": "prev", "expr": "bodies['body_1']"},
        "tool": {"base": "prev", "expr": "bodies['body_2']"},
        "params": {},
        "idempotency_key": "k3",
    })
    th, toh, tbid, tobid = resolve_command_targets(d, cmd_cut)
    print("Resolved:", tbid, tobid)
    d = submit(d, cmd_cut, reg)
    print("After cut bodies:", list(d.bodies.keys()), "volume:", d.geometry.volume)


if __name__ == "__main__":
    test()
