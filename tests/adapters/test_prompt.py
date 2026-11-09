"""Unit tests for prompt construction and KV-cache static prefix invariants."""

from __future__ import annotations

import hashlib
import unittest

from backend.adapters.agent.prompt import STATIC_PREFIX, build_messages


class TestPrompt(unittest.TestCase):
    def test_static_prefix_byte_stability_and_length(self) -> None:
        self.assertGreater(len(STATIC_PREFIX), 3000)
        self.assertLess(len(STATIC_PREFIX), 8000)

        h1 = hashlib.sha256(STATIC_PREFIX.encode("utf-8")).hexdigest()
        h2 = hashlib.sha256(STATIC_PREFIX.encode("utf-8")).hexdigest()
        self.assertEqual(h1, h2)

    def test_build_messages_structure_and_dynamic_separation(self) -> None:
        view1 = {"version": 1, "summary": {"volume": 1000}}
        msgs1 = build_messages(view1, "拉伸顶面 10mm")

        self.assertEqual(len(msgs1), 2)
        self.assertEqual(msgs1[0]["role"], "system")
        self.assertEqual(msgs1[0]["content"], STATIC_PREFIX)
        self.assertEqual(msgs1[1]["role"], "user")
        self.assertIn("拉伸顶面 10mm", msgs1[1]["content"])

        view2 = {"version": 2, "summary": {"volume": 2000}}
        msgs2 = build_messages(view2, "打一个沉孔", diagnostics=["前置检查未通过"])
        self.assertEqual(msgs2[0]["content"], STATIC_PREFIX)
        self.assertIn("前置检查未通过", msgs2[1]["content"])

        hash_sys1 = hashlib.sha256(msgs1[0]["content"].encode("utf-8")).hexdigest()
        hash_sys2 = hashlib.sha256(msgs2[0]["content"].encode("utf-8")).hexdigest()
        self.assertEqual(hash_sys1, hash_sys2)


if __name__ == "__main__":
    unittest.main()
