"""Tests for lowering plans to document ops and the backend BuildProgram IR."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from cadwork.design.document import Ref
from cadwork.design.plan import Expect, PlanNode, new_plan
from cadwork.design.plan_compile import (
    BuildProgram,
    CompileError,
    compile_node,
    compile_plan,
    compile_program,
)


def _plan(*nodes: PlanNode):
    return new_plan("d1", "test plan", 0, nodes=nodes)


def _box_params(length: float = 10.0) -> dict:
    return {"length": length, "width": 20.0, "height": 30.0}


def _feature(node_id: str, action: str = "k_box", **kwargs) -> PlanNode:
    return PlanNode(node_id, "feature", node_id, action=action, **kwargs)


class CompileNodeTests(unittest.TestCase):
    def test_add_op(self) -> None:
        plan = _plan(_feature("f1", params=_box_params()))
        ops = compile_node(plan, plan.nodes[0], None)
        self.assertEqual(len(ops), 1)
        op = ops[0]
        self.assertEqual(op["op"], "add")
        feature = op["feature"]
        self.assertEqual(feature["id"], "f1")
        self.assertEqual(feature["type"], "k_box")
        self.assertEqual(feature["params"]["length"], 10.0)
        self.assertEqual(feature["params"]["width"], 20.0)
        self.assertEqual(feature["refs"], {})
        self.assertEqual(feature["actor"], "agent")

    def test_feature_id_overrides_the_node_id(self) -> None:
        plan = _plan(_feature("n1", feature_id="part_1", params=_box_params()))
        op = compile_node(plan, plan.nodes[0], None)[0]
        self.assertEqual(op["feature"]["id"], "part_1")

    def test_update_op_when_the_feature_already_exists(self) -> None:
        document = SimpleNamespace(
            id="d1",
            features=(SimpleNamespace(id="part_1", type="k_box"),),
        )
        plan = _plan(_feature("n1", feature_id="part_1", params=_box_params(12.0)))
        op = compile_node(plan, plan.nodes[0], document)[0]
        self.assertEqual(op["op"], "update")
        self.assertEqual(op["id"], "part_1")
        self.assertEqual(op["params"]["length"], 12.0)
        self.assertEqual(op["refs"], {})

    def test_update_rejects_an_immutable_type_change(self) -> None:
        document = SimpleNamespace(
            id="d1",
            features=(SimpleNamespace(id="part_1", type="k_cylinder"),),
        )
        plan = _plan(_feature("n1", action="k_box", feature_id="part_1",
                              params=_box_params()))
        with self.assertRaises(CompileError) as caught:
            compile_node(plan, plan.nodes[0], document)
        self.assertEqual(caught.exception.code, "PLAN_INVALID")

    def test_refs_are_translated_from_node_ids_to_feature_ids(self) -> None:
        plan = _plan(
            _feature("n1", feature_id="base", params=_box_params()),
            PlanNode(
                "n2", "feature", "cut", action="k_cut",
                refs={"target": Ref("n1", "self"), "others": Ref("n1", "self")},
                deps=("n1",),
            ),
        )
        op = compile_node(plan, plan.nodes[1], None)[0]
        refs = op["feature"]["refs"]
        self.assertEqual(refs["target"]["source"], "base")
        self.assertEqual(refs["others"]["source"], "base")
        self.assertEqual(refs["target"]["select"], "self")

    def test_tuple_refs_stay_tuples_and_serialize_as_lists(self) -> None:
        plan = _plan(
            _feature("n1", params=_box_params()),
            _feature("n2", params=_box_params()),
            PlanNode(
                "n3", "feature", "cut", action="k_cut",
                refs={
                    "target": Ref("n1", "self"),
                    "others": (Ref("n2", "self"), Ref("n2", "self")),
                },
                deps=("n1", "n2"),
            ),
        )
        op = compile_node(plan, plan.nodes[2], None)[0]
        others = op["feature"]["refs"]["others"]
        self.assertIsInstance(others, list)
        self.assertEqual([item["source"] for item in others], ["n2", "n2"])

    def test_optional_none_params_are_not_written_to_the_document(self) -> None:
        plan = _plan(
            _feature("n1", params=_box_params()),
            PlanNode(
                "n2", "feature", "place", action="place_on",
                refs={"shape": Ref("n1", "self")},
                deps=("n1",),
            ),
        )
        op = compile_node(plan, plan.nodes[1], None)[0]
        self.assertNotIn("plane", op["feature"]["params"])
        self.assertEqual(op["feature"]["params"]["offset"], 0.0)

    def test_since_and_extra_are_translated_to_feature_ids(self) -> None:
        plan = _plan(
            _feature("n1", feature_id="base1", params=_box_params()),
            _feature("n2", feature_id="base2", params=_box_params()),
            PlanNode(
                "n3", "feature", "cut", action="k_cut",
                refs={
                    "target": Ref("n1", "self", since=("n1",), extra=("n2",)),
                    "others": Ref("n2", "self"),
                },
                deps=("n1", "n2"),
            ),
        )
        op = compile_node(plan, plan.nodes[2], None)[0]
        target = op["feature"]["refs"]["target"]
        self.assertEqual(target["source"], "base1")
        self.assertEqual(target["since"], ["base1"])
        self.assertEqual(target["extra"], ["base2"])

    def test_goal_and_check_nodes_produce_no_ops(self) -> None:
        plan = _plan(
            PlanNode("g", "goal", "goal"),
            _feature("f1", params=_box_params()),
            PlanNode("c1", "check", "check", deps=("f1",),
                     expect=(Expect("volume", "ge", 1.0),)),
        )
        self.assertEqual(compile_node(plan, plan.nodes[0], None), [])
        self.assertEqual(compile_node(plan, plan.nodes[2], None), [])

    def test_unknown_action(self) -> None:
        plan = _plan(_feature("f1", action="not_a_real_action"))
        with self.assertRaises(CompileError) as caught:
            compile_node(plan, plan.nodes[0], None)
        self.assertEqual(caught.exception.code, "ACTION_UNKNOWN")
        self.assertEqual(caught.exception.node_id, "f1")

    def test_invalid_params(self) -> None:
        params = dict(_box_params())
        params["nope"] = 1.0
        plan = _plan(_feature("f1", params=params))
        with self.assertRaises(CompileError) as caught:
            compile_node(plan, plan.nodes[0], None)
        self.assertEqual(caught.exception.code, "PLAN_INVALID")

    def test_missing_ref_role(self) -> None:
        plan = _plan(_feature("f1", action="k_cut"))
        with self.assertRaises(CompileError) as caught:
            compile_node(plan, plan.nodes[0], None)
        self.assertEqual(caught.exception.code, "PLAN_INVALID")

    def test_feature_without_action(self) -> None:
        plan = _plan(PlanNode("f1", "feature", "no action"))
        with self.assertRaises(CompileError) as caught:
            compile_node(plan, plan.nodes[0], None)
        self.assertEqual(caught.exception.code, "PLAN_INVALID")


class CompileProgramTests(unittest.TestCase):
    def _plan(self):
        return _plan(
            PlanNode("n1", "feature", "box", action="k_box",
                     params=_box_params(),
                     expect=(Expect("volume", "ge", 0.0),)),
            PlanNode(
                "n2", "feature", "move", action="k_translate",
                refs={"target": Ref("n1", "self")},
                deps=("n1",),
            ),
            PlanNode("c1", "check", "volume", deps=("n2",),
                     expect=(Expect("volume", "ge", 1.0),)),
        )

    def test_steps_variables_inputs_and_final(self) -> None:
        plan = self._plan()
        program = compile_program(plan, None)
        self.assertIsInstance(program, BuildProgram)
        self.assertEqual(len(program.steps), 2)
        first, second = program.steps
        self.assertEqual(first.node_id, "n1")
        self.assertEqual(first.variable, "nn1")
        self.assertEqual(first.action, "k_box")
        self.assertEqual(first.inputs, {})
        self.assertEqual(second.variable, "nn2")
        self.assertEqual(second.inputs["target"], "nn1")
        self.assertEqual(program.final, "nn2")

    def test_steps_carry_their_own_expectations(self) -> None:
        program = compile_program(self._plan(), None)
        self.assertEqual(program.steps[0].expect, (Expect("volume", "ge", 0.0),))
        # Check nodes are evaluated by verify against the dependency output;
        # they do not create or decorate a backend step.
        self.assertEqual(program.steps[1].expect, ())

    def test_tuple_inputs_become_variable_tuples(self) -> None:
        plan = _plan(
            _feature("n1", params=_box_params()),
            _feature("n2", params=_box_params()),
            PlanNode(
                "n3", "feature", "cut", action="k_cut",
                refs={
                    "target": Ref("n1", "self"),
                    "others": (Ref("n2", "self"),),
                },
                deps=("n1", "n2"),
            ),
        )
        step = compile_program(plan, None).steps[2]
        self.assertEqual(step.inputs["others"], ("nn2",))

    def test_no_features_means_an_empty_program(self) -> None:
        program = compile_program(_plan(PlanNode("g", "goal", "goal")), None)
        self.assertEqual(program.steps, ())
        self.assertIsNone(program.final)

    def test_invalid_plan_is_reported_as_a_compile_error(self) -> None:
        plan = _plan(
            _feature("f1"),
            PlanNode("c1", "check", "c", expect=(Expect("volume", "ge", 1.0),)),
        )
        with self.assertRaises(CompileError) as caught:
            compile_program(plan, None)
        self.assertEqual(caught.exception.code, "PLAN_INVALID")

    def test_unknown_action_is_reported_as_a_compile_error(self) -> None:
        plan = _plan(_feature("f1", action="not_a_real_action"))
        with self.assertRaises(CompileError) as caught:
            compile_program(plan, None)
        self.assertEqual(caught.exception.code, "ACTION_UNKNOWN")


class CompilePlanTests(unittest.TestCase):
    def _valid_plan(self):
        return _plan(
            PlanNode("g", "goal", "goal"),
            _feature("n1", feature_id="base", params=_box_params()),
            PlanNode(
                "n2", "feature", "cut", action="k_cut",
                refs={"target": Ref("n1", "self"), "others": Ref("n1", "self")},
                deps=("n1",),
            ),
            PlanNode("c1", "check", "volume", deps=("n2",),
                     expect=(Expect("volume", "ge", 1.0),)),
        )

    def test_report_ops_coverage_and_program(self) -> None:
        report = compile_plan(self._valid_plan(), None)
        self.assertTrue(report.ok)
        self.assertEqual(report.ops_count, 2)
        self.assertEqual([op["op"] for op in report.ops], ["add", "add"])
        self.assertEqual(report.coverage["unknown"], [])
        self.assertIn("k_box", report.coverage["found"])
        self.assertIn("k_cut", report.coverage["found"])
        self.assertEqual(report.coverage.found, ["k_box", "k_cut"])
        self.assertEqual(report.coverage.unknown, [])
        self.assertIsNotNone(report.program)
        self.assertEqual(len(report.steps), 2)
        self.assertEqual(report.final, "nn2")

    def test_unknown_action_is_reported_without_stopping(self) -> None:
        plan = _plan(
            _feature("n1", params=_box_params()),
            _feature("n2", action="not_a_real_action"),
        )
        report = compile_plan(plan, None)
        self.assertFalse(report.ok)
        self.assertEqual([issue.code for issue in report.issues], ["ACTION_UNKNOWN"])
        self.assertEqual(report.coverage["unknown"], ["not_a_real_action"])
        self.assertIn("k_box", report.coverage["found"])
        self.assertIsNone(report.program)

    def test_structural_issue_is_reported(self) -> None:
        plan = _plan(
            _feature("f1", params=_box_params()),
            PlanNode("c1", "check", "c", expect=(Expect("volume", "ge", 1.0),)),
        )
        report = compile_plan(plan, None)
        self.assertFalse(report.ok)
        self.assertEqual(report.issues[0].code, "PLAN_INVALID")
        self.assertEqual(report.ops, [])
        self.assertIsNone(report.program)

    def test_duplicate_document_feature_ids_are_reported(self) -> None:
        plan = _plan(
            _feature("n1", feature_id="shared", params=_box_params()),
            _feature("n2", feature_id="shared", params=_box_params()),
        )
        report = compile_plan(plan, None)
        self.assertFalse(report.ok)
        self.assertEqual(report.issues[0].code, "NODE_ID_CONFLICT")

    def test_report_uses_update_ops_for_existing_features(self) -> None:
        document = SimpleNamespace(
            id="d1",
            features=(SimpleNamespace(id="base", type="k_box"),),
        )
        report = compile_plan(self._valid_plan(), document)
        self.assertTrue(report.ok)
        self.assertEqual(report.ops[0]["op"], "update")
        self.assertEqual(report.ops[0]["id"], "base")

    def test_report_serializes(self) -> None:
        report = compile_plan(self._valid_plan(), None)
        payload = report.to_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["ops_count"], 2)
        self.assertEqual(payload["program"]["final"], "nn2")


if __name__ == "__main__":
    unittest.main()
