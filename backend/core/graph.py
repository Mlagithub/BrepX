"""Dependency DAG modeling for commands and incremental reconstruction."""

from __future__ import annotations

from collections import deque
from typing import Sequence

from backend.core.command import CommandRecord
from backend.core.errors import PreconditionError


class DependencyGraph:
    def __init__(self) -> None:
        self._nodes: set[str] = set()
        self._edges: dict[str, set[str]] = {}
        self._reverse: dict[str, set[str]] = {}

    def add_node(self, node_id: str) -> None:
        self._nodes.add(node_id)
        if node_id not in self._edges:
            self._edges[node_id] = set()
        if node_id not in self._reverse:
            self._reverse[node_id] = set()

    def add_edge(self, from_id: str, to_id: str) -> None:
        if from_id == to_id:
            raise ValueError(f"Self-loop forbidden in DependencyGraph on node '{from_id}'")
        self.add_node(from_id)
        self.add_node(to_id)
        self._edges[from_id].add(to_id)
        self._reverse[to_id].add(from_id)

    def topological_order(self) -> list[str]:
        in_degree = {n: len(self._reverse[n]) for n in self._nodes}
        zero_in = [n for n, deg in in_degree.items() if deg == 0]
        zero_in.sort()

        order: list[str] = []
        while zero_in:
            curr = zero_in.pop(0)
            order.append(curr)

            for downstream in sorted(self._edges[curr]):
                in_degree[downstream] -= 1
                if in_degree[downstream] == 0:
                    zero_in.append(downstream)
                    zero_in.sort()

        if len(order) != len(self._nodes):
            raise PreconditionError("Cycle detected in DependencyGraph: topological sort failed.")

        return order

    def downstream_of(self, node_id: str, include_self: bool = True) -> set[str]:
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found in DependencyGraph")

        visited: set[str] = set([node_id]) if include_self else set()
        queue = deque([node_id])

        while queue:
            curr = queue.popleft()
            for nxt in self._edges.get(curr, set()):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)

        return visited


def build_graph(journal: Sequence[CommandRecord]) -> DependencyGraph:
    graph = DependencyGraph()
    known_commands: list[str] = []

    for record in journal:
        cmd = record.command
        graph.add_node(cmd.command_id)

        bases_to_check: list[str] = []
        if cmd.target is not None:
            bases_to_check.append(cmd.target.base)
        if cmd.tool is not None:
            bases_to_check.append(cmd.tool.base)

        for base in bases_to_check:
            if base == "prev":
                if known_commands:
                    prev_id = known_commands[-1]
                    graph.add_edge(prev_id, cmd.command_id)
            elif base.startswith("c"):
                if base not in known_commands:
                    raise PreconditionError(
                        f"Command '{cmd.command_id}' references non-existent base '{base}' in journal."
                    )
                graph.add_edge(base, cmd.command_id)

        known_commands.append(cmd.command_id)

    return graph
