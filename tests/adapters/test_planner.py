"""Unit tests for Plan-as-Data DAG representation, critical path, and replanning."""

from __future__ import annotations

import unittest

from backend.adapters.agent.planner import (
    MAX_CRITICAL_PATH,
    AgentPlanError,
    PlanDAG,
    PlanStatus,
    PlanStep,
)


class TestPlanner(unittest.TestCase):
    def test_plan_dag_creation_and_next_runnable(self) -> None:
        s1 = PlanStep(step_id="s1", title="创建长方体", op="box")
        s2 = PlanStep(step_id="s2", title="打孔", op="hole", depends_on=["s1"])
        dag = PlanDAG([s1, s2])

        self.assertEqual(dag.critical_path_length(), 2)
        next_step = dag.next_runnable()
        self.assertIsNotNone(next_step)
        self.assertEqual(next_step.step_id, "s1")

        s1.status = PlanStatus.COMPLETED
        next_step2 = dag.next_runnable()
        self.assertIsNotNone(next_step2)
        self.assertEqual(next_step2.step_id, "s2")

    def test_critical_path_limit_enforced(self) -> None:
        steps = [
            PlanStep(step_id="s1", title="s1", op="box"),
            PlanStep(step_id="s2", title="s2", op="hole", depends_on=["s1"]),
            PlanStep(step_id="s3", title="s3", op="fillet", depends_on=["s2"]),
            PlanStep(step_id="s4", title="s4", op="chamfer", depends_on=["s3"]),
            PlanStep(step_id="s5", title="s5", op="shell", depends_on=["s4"]),
        ]
        with self.assertRaises(AgentPlanError) as ctx:
            PlanDAG(steps)
        self.assertEqual(ctx.exception.critical_path_length, 5)

    def test_mark_downstream_obsolete_and_replan_replacement(self) -> None:
        s1 = PlanStep(step_id="s1", title="s1", op="box", status=PlanStatus.COMPLETED)
        s2 = PlanStep(step_id="s2", title="s2", op="hole", depends_on=["s1"])
        s3 = PlanStep(step_id="s3", title="s3", op="fillet", depends_on=["s2"])
        dag = PlanDAG([s1, s2, s3])

        obsoleted = dag.mark_downstream_obsolete("s2")
        self.assertIn("s3", obsoleted)
        self.assertEqual(dag.steps["s1"].status, PlanStatus.COMPLETED)
        self.assertEqual(dag.steps["s2"].status, PlanStatus.FAILED)
        self.assertEqual(dag.steps["s3"].status, PlanStatus.OBSOLETE)

        s2_replacement = PlanStep(step_id="s2_fix", title="s2 fix", op="extrude", depends_on=["s1"])
        dag.merge_replacement("s2", s2_replacement)
        self.assertIn("s2_fix", dag.steps)
        self.assertEqual(dag.steps["s2_fix"].replaces, "s2")


if __name__ == "__main__":
    unittest.main()
