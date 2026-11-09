"""Plan-as-Data structured workflow representation and replanning logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

MAX_CRITICAL_PATH = 4


class PlanStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    OBSOLETE = "obsolete"


class AgentPlanError(Exception):
    def __init__(self, message: str, critical_path_length: int = 0) -> None:
        super().__init__(message)
        self.message = message
        self.critical_path_length = critical_path_length

    def to_diagnostic(self) -> dict[str, Any]:
        return {
            "error": "AgentPlanError",
            "message": self.message,
            "critical_path_length": self.critical_path_length,
        }


@dataclass
class PlanStep:
    step_id: str
    title: str
    op: str
    target_expr: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    replaces: str | None = None


class PlanDAG:
    def __init__(self, steps: list[PlanStep] | None = None) -> None:
        self.steps: dict[str, PlanStep] = {}
        if steps:
            for step in steps:
                self.steps[step.step_id] = step
            c_len = self.critical_path_length()
            if c_len > MAX_CRITICAL_PATH:
                raise AgentPlanError(
                    f"Plan critical path length {c_len} exceeds maximum limit ({MAX_CRITICAL_PATH}).",
                    critical_path_length=c_len,
                )

    def critical_path_length(self) -> int:
        active_steps = {
            sid: s for sid, s in self.steps.items()
            if s.status != PlanStatus.OBSOLETE
        }
        if not active_steps:
            return 0

        memo: dict[str, int] = {}

        def get_depth(sid: str, visited: set[str]) -> int:
            if sid in visited:
                raise AgentPlanError("Cycle detected in PlanDAG dependencies.")
            if sid in memo:
                return memo[sid]

            step = active_steps.get(sid)
            if step is None:
                return 0

            max_dep_depth = 0
            for dep in step.depends_on:
                if dep in active_steps:
                    dep_depth = get_depth(dep, visited | {sid})
                    if dep_depth > max_dep_depth:
                        max_dep_depth = dep_depth

            length = 1 + max_dep_depth
            memo[sid] = length
            return length

        return max(get_depth(sid, set()) for sid in active_steps)

    def next_runnable(self) -> PlanStep | None:
        for step in self.steps.values():
            if step.status != PlanStatus.PENDING:
                continue
            deps_satisfied = True
            for dep_id in step.depends_on:
                dep_step = self.steps.get(dep_id)
                if dep_step is None or dep_step.status != PlanStatus.COMPLETED:
                    deps_satisfied = False
                    break
            if deps_satisfied:
                return step
        return None

    def mark_downstream_obsolete(self, failed_step_id: str) -> list[str]:
        if failed_step_id in self.steps:
            self.steps[failed_step_id].status = PlanStatus.FAILED

        obsoleted: list[str] = []
        changed = True

        while changed:
            changed = False
            for sid, step in self.steps.items():
                if step.status == PlanStatus.COMPLETED or step.status == PlanStatus.OBSOLETE or sid == failed_step_id:
                    continue
                for dep_id in step.depends_on:
                    dep_step = self.steps.get(dep_id)
                    if dep_step and dep_step.status in (PlanStatus.FAILED, PlanStatus.OBSOLETE):
                        step.status = PlanStatus.OBSOLETE
                        obsoleted.append(sid)
                        changed = True
                        break

        return obsoleted

    def merge_replacement(self, old_id: str, new_step: PlanStep) -> None:
        new_step.replaces = old_id
        self.steps[new_step.step_id] = new_step

        for step in self.steps.values():
            if old_id in step.depends_on:
                step.depends_on = [
                    new_step.step_id if dep == old_id else dep
                    for dep in step.depends_on
                ]

        c_len = self.critical_path_length()
        if c_len > MAX_CRITICAL_PATH:
            raise AgentPlanError(
                f"Replanned critical path length {c_len} exceeds limit ({MAX_CRITICAL_PATH}).",
                critical_path_length=c_len,
            )
