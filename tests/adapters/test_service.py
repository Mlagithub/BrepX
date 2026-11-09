"""Unit tests for agent output schema, turn execution service, and self-healing loop."""

from __future__ import annotations

import json
import unittest

from backend.adapters.agent.healing import (
    AgentBudgetError,
    HealingCoordinator,
    build_diagnostic_hint,
)
from backend.adapters.agent.llm_client import LLMConfig
from backend.adapters.agent.schema import (
    AgentOutputError,
    parse_reply,
    validate_command_payload,
)
from backend.adapters.agent.service import handle_turn


class TestAgentServiceAndHealing(unittest.TestCase):
    def test_schema_parse_codeblock_and_raw_json(self) -> None:
        block_text = '前言\n```json\n{"explanation": "ok", "commands": [{"op": "box", "params": {}}]}\n```\n结语'
        exp1, cmds1 = parse_reply(block_text)
        self.assertEqual(exp1, "ok")
        self.assertEqual(len(cmds1), 1)

        raw_text = '{"explanation": "direct", "commands": [{"op": "cylinder", "params": {}}]}'
        exp2, cmds2 = parse_reply(raw_text)
        self.assertEqual(exp2, "direct")
        self.assertEqual(len(cmds2), 1)

        with self.assertRaises(AgentOutputError):
            parse_reply("not a valid json")

    def test_command_payload_validation_forbidden_index(self) -> None:
        valid_cmd = {"op": "hole", "target": {"base": "prev", "expr": "faces().top()"}}
        self.assertEqual(validate_command_payload(valid_cmd)["op"], "hole")

        invalid_cmd = {"op": "hole", "target": {"base": "prev", "expr": "faces()[0]"}}
        with self.assertRaises(AgentOutputError):
            validate_command_payload(invalid_cmd)

    def test_healing_loop_detection(self) -> None:
        coordinator = HealingCoordinator()
        cmds = [{"op": "box", "params": {"length": 10}}]
        coordinator.record_action_fingerprint(cmds)

        with self.assertRaises(AgentBudgetError) as ctx:
            coordinator.record_action_fingerprint(cmds)
        self.assertEqual(ctx.exception.reason, "LOOP_DETECTED")

    def test_healing_and_retry_turn_execution(self) -> None:
        mock_replies = [
            '{"explanation": "attempt 1", "commands": [{"op": "hole", "target": {"base": "prev", "expr": "faces().bad()"}}]}',
            '{"explanation": "attempt 2", "commands": [{"op": "box", "params": {"length": 60.0}}]}',
        ]
        reply_iter = iter(mock_replies)

        def mock_chat(msgs, cfg):
            return next(reply_iter)

        executed_cmds = []

        def mock_exec(url, cmd):
            if cmd.get("op") == "hole":
                return {"ok": False, "error": {"error": "SelectorResolutionError", "message": "no_match"}}
            executed_cmds.append(cmd["op"])
            return {"ok": True, "command_id": cmd.get("command_id", "c1")}

        cfg = LLMConfig(base_url="https://mock", model="m", api_key="sk-test")
        res = handle_turn(
            prompt="建一个模型",
            view={"version": 1},
            config=cfg,
            chat_fn=mock_chat,
            command_executor=mock_exec,
        )

        self.assertTrue(res["ok"])
        self.assertEqual(res["turns_used"], 2)
        self.assertIn("box", executed_cmds)


if __name__ == "__main__":
    unittest.main()
