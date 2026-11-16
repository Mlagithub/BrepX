"""Assembly plans expand deterministically into assembly documents."""

from __future__ import annotations

import math
import unittest

from cadwork.design.assembly import AssemblyRef, PartRef, Transform
from cadwork.design.assembly_plan import (
    AssemblyPlan,
    Pattern,
    PlanInstance,
    compile_assembly_plan,
)
from cadwork.design.document import DocumentError


class AssemblyPlanTests(unittest.TestCase):
    def _part(self):
        return PartRef("part_blade", 3)

    def test_polar_pattern_expands_with_deterministic_ids(self) -> None:
        plan = AssemblyPlan(
            "engine",
            "engine",
            (
                PlanInstance(
                    "blade", self._part(), pattern=Pattern("polar", 4, radius=10.0)
                ),
            ),
        )
        assembly = compile_assembly_plan(plan)
        self.assertEqual(
            [item.id for item in assembly.instances],
            ["blade_0", "blade_1", "blade_2", "blade_3"],
        )
        first = assembly.instances[0]
        second = assembly.instances[1]
        self.assertAlmostEqual(first.placement.translation[0], 10.0)
        self.assertAlmostEqual(first.placement.translation[1], 0.0)
        self.assertAlmostEqual(second.placement.translation[0], 0.0)
        self.assertAlmostEqual(second.placement.translation[1], 10.0)
        self.assertAlmostEqual(second.placement.rotation[0][0], 0.0, places=9)
        self.assertAlmostEqual(second.placement.rotation[1][0], 1.0, places=9)

    def test_linear_pattern_and_base_transform_compose(self) -> None:
        plan = AssemblyPlan(
            "line",
            "line",
            (
                PlanInstance(
                    "bolt",
                    self._part(),
                    placement=Transform(translation=(1.0, 2.0, 3.0)),
                    pattern=Pattern("linear", 3, dx=5.0, dy=-1.0),
                ),
            ),
        )
        assembly = compile_assembly_plan(plan)
        translations = [item.placement.translation for item in assembly.instances]
        self.assertEqual(
            translations, [(1.0, 2.0, 3.0), (6.0, 1.0, 3.0), (11.0, 0.0, 3.0)]
        )

    def test_plan_compiles_to_requested_assembly_identity(self) -> None:
        plan = AssemblyPlan(
            "plan",
            "plan",
            (PlanInstance("sub", AssemblyRef("assembly_child", 2), Transform()),),
            version=4,
        )
        assembly = compile_assembly_plan(plan, assembly_id="assembly_target", version=7)
        self.assertEqual(assembly.id, "assembly_target")
        self.assertEqual(assembly.version, 7)
        self.assertEqual(assembly.instances[0].ref.document_id, "assembly_child")

    def test_expanded_id_collision_is_rejected(self) -> None:
        plan = AssemblyPlan(
            "plan",
            "plan",
            (
                PlanInstance("a", self._part(), pattern=Pattern("linear", 2, dx=1.0)),
                PlanInstance("a_0", self._part()),
            ),
        )
        with self.assertRaises(DocumentError) as caught:
            plan.expand()
        self.assertEqual(caught.exception.code, "DUPLICATE_ID")

    def test_invalid_pattern_is_rejected(self) -> None:
        with self.assertRaises(DocumentError):
            Pattern("polar", 0)

    def test_polar_rotation_matches_quarter_turn(self) -> None:
        pattern = Pattern("polar", 4, radius=0.0)
        placement = pattern.placement(1)
        self.assertAlmostEqual(placement.rotation[0][0], 0.0, places=9)
        self.assertAlmostEqual(placement.rotation[0][1], -1.0, places=9)
        self.assertAlmostEqual(placement.rotation[1][0], 1.0, places=9)
        self.assertAlmostEqual(placement.translation[0], 0.0)
        self.assertTrue(math.isclose(placement.rotation[2][2], 1.0))


if __name__ == "__main__":
    unittest.main()
