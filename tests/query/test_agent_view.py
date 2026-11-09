"""Unit tests for agent observation view generation, truncation, and token budgeting."""

from __future__ import annotations

import unittest
from smlibpy import Box

from backend.core.design import Design
from backend.kernel import ops_features, ops_primitives
from backend.kernel.registry import OperatorRegistry, OperatorSpec, default_registry
from backend.query.agent_view import (
    MAX_FACES_IN_VIEW,
    build_agent_view,
    estimate_tokens,
)


class TestAgentView(unittest.TestCase):
    def setUp(self) -> None:
        self.box = Box(60, 40, 20)
        self.design = Design.with_geometry(self.box)

    def test_agent_view_structure_and_facts(self) -> None:
        view = build_agent_view(self.design, selections=["faces().facing(Z)"])
        self.assertEqual(view["version"], 1)
        self.assertEqual(view["summary"]["face_count"], 6)
        self.assertAlmostEqual(view["summary"]["volume"], 48000.0, delta=1e-3)

        self.assertEqual(len(view["selections"]), 1)
        sel_fact = view["selections"][0]
        self.assertEqual(sel_fact["selector"], "faces().facing(Z)")
        self.assertEqual(sel_fact["entity_type"], "face")
        self.assertTrue(sel_fact["is_planar"])
        self.assertEqual(sel_fact["normal"], [0.0, 0.0, 1.0])

        tok_count = estimate_tokens(view)
        self.assertLess(tok_count, 2000)

    def test_truncation_limits(self) -> None:
        view = build_agent_view(self.design)
        self.assertFalse(view["truncated"])
        self.assertEqual(view["omitted_faces_count"], 0)

    def test_hierarchical_operator_retrieval(self) -> None:
        reg = OperatorRegistry()
        self.assertEqual(reg.find(""), [])

        sample_doc = (
            "用途: 测试自定义放样\n场景: 管道过渡\n区别: 多截面平滑连接\n"
            "参数: profiles\n约束: 至少两个有效闭合截面\n示例: loft(profiles=[p1, p2])"
        )
        custom_spec = OperatorSpec(
            op="custom_loft",
            category="surface",
            produces="solid",
            params={},
            needs_target=False,
            needs_tool=False,
            default_assertions=(),
            doc=sample_doc,
            call=lambda *a: None,
        )
        reg.register(custom_spec)

        found = reg.find("平滑连接")
        self.assertIn("custom_loft", [s.op for s in found])

        found_empty = reg.find("未知算子关键词")
        self.assertEqual(found_empty, [])


if __name__ == "__main__":
    unittest.main()
