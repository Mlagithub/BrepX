"""Unit tests for operator registry and specification contracts."""

from __future__ import annotations

import unittest

from backend.core.command import is_solid
from backend.core.errors import OperatorNotFoundError
from backend.core.params import ParamKind, ParamSpec
from backend.kernel.registry import OperatorRegistry, OperatorSpec, default_registry


def dummy_box_builder(length: float = 1.0) -> object:
    return object()


SAMPLE_DOC = """
用途: 创建规则长方体实体
场景: 初始化基准几何工件
区别: 与拉伸不同，不依赖前序二维截面
参数: length(长度), width(宽度), height(高度)
约束: 各尺寸参数必须严格大于零
示例: box(length=10, width=10, height=10)
"""


class TestOperatorRegistry(unittest.TestCase):
    def test_operator_spec_validation(self) -> None:
        with self.assertRaises(ValueError):
            OperatorSpec(
                op="bad_box",
                category="invalid_category",
                produces="solid",
                params={},
                needs_target=False,
                needs_tool=False,
                default_assertions=(is_solid(),),
                doc=SAMPLE_DOC,
                call=dummy_box_builder,
            )

        with self.assertRaises(ValueError):
            OperatorSpec(
                op="bad_doc_box",
                category="primitive",
                produces="solid",
                params={},
                needs_target=False,
                needs_tool=False,
                default_assertions=(is_solid(),),
                doc="Missing required keys",
                call=dummy_box_builder,
            )

        spec = OperatorSpec(
            op="box",
            category="primitive",
            produces="solid",
            params={"length": ParamSpec(ParamKind.FLOAT, default=1.0, min=0.0)},
            needs_target=False,
            needs_tool=False,
            default_assertions=(is_solid(),),
            doc=SAMPLE_DOC,
            call=dummy_box_builder,
        )
        self.assertEqual(spec.op, "box")

    def test_registry_registration_and_lookup(self) -> None:
        reg = OperatorRegistry()
        spec = OperatorSpec(
            op="box",
            category="primitive",
            produces="solid",
            params={},
            needs_target=False,
            needs_tool=False,
            default_assertions=(),
            doc=SAMPLE_DOC,
            call=dummy_box_builder,
        )
        reg.register(spec)
        self.assertIn("box", reg.all_ops())
        self.assertEqual(reg.get("box").op, "box")

        with self.assertRaises(ValueError):
            reg.register(spec)

        with self.assertRaises(OperatorNotFoundError) as ctx:
            reg.get("boc")
        self.assertIn("box", ctx.exception.closest)

        primitive_specs = reg.specs_by_category("primitive")
        self.assertEqual(len(primitive_specs), 1)

    def test_default_registry_singleton(self) -> None:
        r1 = default_registry()
        r2 = default_registry()
        self.assertIs(r1, r2)


if __name__ == "__main__":
    unittest.main()
