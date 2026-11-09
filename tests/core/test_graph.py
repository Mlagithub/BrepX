"""Unit tests for DependencyGraph DAG operations, ordering, and cycle detection."""

from __future__ import annotations

import unittest

from backend.core.command import Command, CommandRecord, SelectorRef
from backend.core.errors import PreconditionError
from backend.core.graph import DependencyGraph, build_graph


def make_record(cmd_id: str, op: str = "box", target_base: str | None = None) -> CommandRecord:
    target = SelectorRef(base=target_base, expr="faces().top()") if target_base else None
    cmd = Command(
        command_id=cmd_id,
        op=op,
        target=target,
        tool=None,
        params={},
        expect=(),
        idempotency_key=f"k_{cmd_id}",
    )
    return CommandRecord(command=cmd, version=1, result_summary={"volume": 1.0, "face_count": 1, "is_valid": True})


class TestDependencyGraph(unittest.TestCase):
    def test_linear_chain_build_and_downstream(self) -> None:
        r1 = make_record("c1", "box")
        r2 = make_record("c2", "hole", target_base="prev")
        r3 = make_record("c3", "fillet", target_base="prev")

        g = build_graph([r1, r2, r3])
        self.assertEqual(g.topological_order(), ["c1", "c2", "c3"])
        self.assertEqual(g.downstream_of("c2"), {"c2", "c3"})
        self.assertEqual(g.downstream_of("c2", include_self=False), {"c3"})

    def test_diamond_and_multiple_upstream(self) -> None:
        g = DependencyGraph()
        g.add_edge("c1", "c2")
        g.add_edge("c1", "c3")
        g.add_edge("c2", "c4")
        g.add_edge("c3", "c4")

        order = g.topological_order()
        self.assertEqual(order[0], "c1")
        self.assertEqual(order[-1], "c4")
        self.assertEqual(g.downstream_of("c1"), {"c1", "c2", "c3", "c4"})

    def test_self_loop_forbidden(self) -> None:
        g = DependencyGraph()
        with self.assertRaises(ValueError):
            g.add_edge("c1", "c1")

    def test_phantom_upstream_raises_precondition_error(self) -> None:
        r1 = make_record("c2", "hole", target_base="c1")
        with self.assertRaises(PreconditionError):
            build_graph([r1])

    def test_cycle_detection(self) -> None:
        g = DependencyGraph()
        g.add_edge("c1", "c2")
        g.add_edge("c2", "c3")
        g.add_edge("c3", "c1")
        with self.assertRaises(PreconditionError):
            g.topological_order()

    def test_deterministic_order(self) -> None:
        g = DependencyGraph()
        g.add_node("c2")
        g.add_node("c1")
        g.add_node("c3")
        order1 = g.topological_order()
        order2 = g.topological_order()
        self.assertEqual(order1, ["c1", "c2", "c3"])
        self.assertEqual(order1, order2)


if __name__ == "__main__":
    unittest.main()
