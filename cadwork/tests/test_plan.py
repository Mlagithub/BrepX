"""Tests for the modeling-plan data model and structural validation."""

from __future__ import annotations

import json
import unittest

from cadwork.design.document import Filter, Ref
from cadwork.design.document import ref_to_json as document_ref_to_json
from cadwork.design.plan import (
    Expect,
    ModelingPlan,
    PlanError,
    PlanNode,
    new_plan,
    next_node_id,
    plan_from_json,
    plan_to_json,
    ref_to_json,
    validate_expect,
    validate_plan,
    with_node,
    with_revision,
)


def _base_plan() -> ModelingPlan:
    nodes = (
        PlanNode("g", "goal", "Build a small block"),
        PlanNode("f1", "feature", "block", action="solid_box",
                 params={"length": 10.0, "width": 20.0, "height": 30.0}),
        PlanNode(
            "f2", "feature", "cut it", action="boolean",
            params={"kind": "cut"},
            refs={
                "target": Ref("f1", "self"),
                "tool": Ref("f1", "faces", (Filter("largest"),)),
            },
            deps=("f1",),
        ),
        PlanNode(
            "c1", "check", "still has volume", deps=("f2",),
            expect=(
                Expect("volume", "ge", 1.0),
                Expect("faces", "between", (1, 100)),
            ),
        ),
    )
    return new_plan("d_test", "Build a small block", 0, nodes=nodes)


class PlanModelTests(unittest.TestCase):
    def test_new_plan_defaults(self) -> None:
        plan = new_plan("d1", "goal", 3)
        self.assertTrue(plan.id.startswith("p_"))
        self.assertEqual(plan.document_id, "d1")
        self.assertEqual(plan.goal, "goal")
        self.assertEqual(plan.base_version, 3)
        self.assertEqual(plan.revision, 1)
        self.assertEqual(plan.nodes, ())
        self.assertEqual(plan.status, "draft")
        self.assertGreater(plan.created, 0.0)

    def test_with_node_appends_then_replaces_in_place(self) -> None:
        plan = new_plan("d1", "goal", 0, nodes=(
            PlanNode("f1", "feature", "one", action="solid_box"),
            PlanNode("f2", "feature", "two", action="solid_box"),
        ))
        updated = with_node(plan, PlanNode("f3", "feature", "three", action="solid_box"))
        self.assertEqual([node.id for node in updated.nodes], ["f1", "f2", "f3"])
        self.assertEqual(updated.revision, plan.revision)
        self.assertEqual(updated.created, plan.created)

        replaced = with_node(updated, PlanNode("f2", "feature", "TWO", action="solid_box"))
        self.assertEqual([node.id for node in replaced.nodes], ["f1", "f2", "f3"])
        self.assertEqual([node.title for node in replaced.nodes], ["one", "TWO", "three"])
        # Pure helper: the input is untouched.
        self.assertEqual([node.title for node in updated.nodes], ["one", "two", "three"])

    def test_with_revision_increments_or_sets(self) -> None:
        plan = new_plan("d1", "goal", 0)
        self.assertEqual(with_revision(plan).revision, 2)
        self.assertEqual(with_revision(plan, 7).revision, 7)
        self.assertEqual(plan.revision, 1)

    def test_next_node_id(self) -> None:
        self.assertEqual(next_node_id(new_plan("d1", "goal", 0)), "n1")
        self.assertEqual(next_node_id(), "n1")
        plan = new_plan("d1", "goal", 0, nodes=(
            PlanNode("n1", "goal", "g"),
            PlanNode("n3", "goal", "g"),
        ))
        self.assertEqual(next_node_id(plan), "n2")

    def test_round_trip_carries_since_and_extra(self) -> None:
        ref = Ref("f1", "faces", (Filter("largest"),),
                  since=("f0",), extra=("f2",))
        plan = new_plan("d1", "goal", 0, nodes=(
            PlanNode("c1", "check", "c", deps=("f1",),
                     expect=(Expect("distance", "le", 1.0, ref=ref),)),
        ))
        decoded = ModelingPlan.from_json(json.dumps(plan.to_json()))
        self.assertEqual(decoded.nodes[0].expect[0].ref, ref)
        self.assertEqual(decoded.nodes[0].expect[0].ref.since, ("f0",))
        self.assertEqual(decoded.nodes[0].expect[0].ref.extra, ("f2",))

    def test_json_round_trip(self) -> None:
        plan = _base_plan()
        payload = plan.to_json()
        decoded = ModelingPlan.from_json(json.dumps(payload))
        self.assertEqual(decoded, plan)
        self.assertEqual(decoded.nodes[1].params["length"], 10.0)
        self.assertEqual(decoded.nodes[2].refs["target"], Ref("f1", "self"))
        self.assertEqual(decoded.nodes[2].refs["tool"].filters, (Filter("largest"),))
        self.assertEqual(decoded.nodes[3].expect[1].value, (1, 100))

    def test_round_trip_preserves_tuple_refs(self) -> None:
        node = PlanNode(
            "f1", "feature", "thicken",
            action="thicken_faces",
            refs={"faces": (Ref("n0", "faces"), Ref("n0", "faces"))},
        )
        plan = new_plan("d1", "goal", 0, nodes=(node,))
        decoded = plan_from_json(plan_to_json(plan))
        self.assertIsInstance(decoded.nodes[0].refs["faces"], tuple)
        self.assertEqual(decoded.nodes[0].refs, node.refs)

    def test_ref_json_matches_the_canonical_document_shape(self) -> None:
        ref = Ref("f1", "faces", (Filter("largest"),))
        self.assertEqual(ref_to_json(ref), document_ref_to_json(ref))

    def test_from_json_accepts_a_string(self) -> None:
        plan = _base_plan()
        decoded = ModelingPlan.from_json(json.dumps(plan.to_json()))
        self.assertEqual(decoded.id, plan.id)

    def test_from_json_can_validate(self) -> None:
        plan = _base_plan()
        self.assertEqual(ModelingPlan.from_json(plan.to_json(), validate=True), plan)


class PlanValidationTests(unittest.TestCase):
    def assertPlanError(self, plan: ModelingPlan, code: str) -> None:
        with self.assertRaises(PlanError) as caught:
            validate_plan(plan)
        self.assertEqual(caught.exception.code, code, str(caught.exception))

    def test_valid_plan_passes_with_or_without_a_document(self) -> None:
        plan = _base_plan()
        validate_plan(plan)
        validate_plan(plan, object())

    def test_duplicate_node_ids(self) -> None:
        plan = new_plan("d1", "goal", 0, nodes=(
            PlanNode("g", "goal", "one"),
            PlanNode("g", "goal", "two"),
        ))
        self.assertPlanError(plan, "NODE_ID_CONFLICT")

    def test_invalid_node_id(self) -> None:
        plan = new_plan("d1", "goal", 0, nodes=(PlanNode("1bad", "goal", "g"),))
        self.assertPlanError(plan, "PLAN_INVALID")

    def test_unknown_dependency(self) -> None:
        plan = new_plan("d1", "goal", 0, nodes=(
            PlanNode("g", "goal", "g"),
            PlanNode("f1", "feature", "f", action="solid_box", deps=("missing",)),
        ))
        self.assertPlanError(plan, "PLAN_INVALID")

    def test_forward_dependency_is_rejected(self) -> None:
        plan = new_plan("d1", "goal", 0, nodes=(
            PlanNode("f1", "feature", "f", action="solid_box", deps=("f2",)),
            PlanNode("f2", "feature", "f", action="solid_box"),
        ))
        self.assertPlanError(plan, "PLAN_INVALID")

    def test_ref_must_point_at_an_earlier_feature(self) -> None:
        plan = new_plan("d1", "goal", 0, nodes=(
            PlanNode("g", "goal", "g"),
            PlanNode("f1", "feature", "one", action="solid_box"),
            PlanNode("f2", "feature", "two", action="transform",
                     refs={"target": Ref("f1", "self")}),
            PlanNode("f3", "feature", "three", action="transform",
                     refs={"target": Ref("g", "self")}),
        ))
        self.assertPlanError(plan, "PLAN_INVALID")

        later = new_plan("d1", "goal", 0, nodes=(
            PlanNode("f1", "feature", "one", action="transform",
                     refs={"target": Ref("f2", "self")}),
            PlanNode("f2", "feature", "two", action="solid_box"),
        ))
        self.assertPlanError(later, "PLAN_INVALID")

    def test_feature_requires_action(self) -> None:
        plan = new_plan("d1", "goal", 0, nodes=(
            PlanNode("f1", "feature", "no action"),
        ))
        self.assertPlanError(plan, "PLAN_INVALID")

    def test_goal_cannot_have_an_action(self) -> None:
        plan = new_plan("d1", "goal", 0, nodes=(
            PlanNode("g", "goal", "g", action="solid_box"),
        ))
        self.assertPlanError(plan, "PLAN_INVALID")

    def test_goal_cannot_have_expectations(self) -> None:
        plan = new_plan("d1", "goal", 0, nodes=(
            PlanNode("g", "goal", "g", expect=(Expect("volume", "ge", 1.0),)),
        ))
        self.assertPlanError(plan, "PLAN_INVALID")

    def test_check_requires_one_dependency(self) -> None:
        none = new_plan("d1", "goal", 0, nodes=(
            PlanNode("c1", "check", "c", expect=(Expect("volume", "ge", 1.0),)),
        ))
        self.assertPlanError(none, "PLAN_INVALID")

        two = new_plan("d1", "goal", 0, nodes=(
            PlanNode("f1", "feature", "f", action="solid_box"),
            PlanNode("f2", "feature", "f", action="solid_box"),
            PlanNode("c1", "check", "c", deps=("f1", "f2"),
                     expect=(Expect("volume", "ge", 1.0),)),
        ))
        self.assertPlanError(two, "PLAN_INVALID")

    def test_check_cannot_have_an_action(self) -> None:
        plan = new_plan("d1", "goal", 0, nodes=(
            PlanNode("f1", "feature", "f", action="solid_box"),
            PlanNode("c1", "check", "c", action="solid_box", deps=("f1",),
                     expect=(Expect("volume", "ge", 1.0),)),
        ))
        self.assertPlanError(plan, "PLAN_INVALID")

    def test_check_requires_an_expectation(self) -> None:
        plan = new_plan("d1", "goal", 0, nodes=(
            PlanNode("f1", "feature", "f", action="solid_box"),
            PlanNode("c1", "check", "c", deps=("f1",)),
        ))
        self.assertPlanError(plan, "PLAN_INVALID")

    def test_unknown_kind(self) -> None:
        plan = new_plan("d1", "goal", 0, nodes=(PlanNode("x", "mystery", "x"),))
        self.assertPlanError(plan, "PLAN_INVALID")

    def test_invalid_feature_id(self) -> None:
        plan = new_plan("d1", "goal", 0, nodes=(
            PlanNode("f1", "feature", "f", action="solid_box", feature_id="has-dash"),
        ))
        self.assertPlanError(plan, "PLAN_INVALID")

    def test_unknown_metric_and_op_fail_at_validation_time(self) -> None:
        bad_metric = new_plan("d1", "goal", 0, nodes=(
            PlanNode("f1", "feature", "f", action="solid_box"),
            PlanNode("c1", "check", "c", deps=("f1",),
                     expect=(Expect("weight", "ge", 1.0),)),
        ))
        self.assertPlanError(bad_metric, "PLAN_INVALID")

        bad_op = new_plan("d1", "goal", 0, nodes=(
            PlanNode("f1", "feature", "f", action="solid_box"),
            PlanNode("c1", "check", "c", deps=("f1",),
                     expect=(Expect("volume", "roughly", 1.0),)),
        ))
        self.assertPlanError(bad_op, "PLAN_INVALID")

        with self.assertRaises(PlanError) as caught:
            validate_expect(Expect("volume", "nope", 1.0))
        self.assertEqual(caught.exception.code, "PLAN_INVALID")

    def test_between_requires_a_pair(self) -> None:
        with self.assertRaises(PlanError) as caught:
            validate_expect(Expect("volume", "between", (1.0,)))
        self.assertEqual(caught.exception.code, "PLAN_INVALID")

    def test_comparison_requires_a_value(self) -> None:
        with self.assertRaises(PlanError) as caught:
            validate_expect(Expect("volume", "ge"))
        self.assertEqual(caught.exception.code, "PLAN_INVALID")

    def test_distance_requires_a_ref(self) -> None:
        with self.assertRaises(PlanError) as caught:
            validate_expect(Expect("distance", "le", 1.0))
        self.assertEqual(caught.exception.code, "PLAN_INVALID")

    def test_negative_tolerance_is_rejected(self) -> None:
        with self.assertRaises(PlanError) as caught:
            validate_expect(Expect("volume", "ge", 1.0, tolerance=-1.0))
        self.assertEqual(caught.exception.code, "PLAN_INVALID")


if __name__ == "__main__":
    unittest.main()
