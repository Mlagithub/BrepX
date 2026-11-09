"""Unit tests for LLM client configuration, error translation, and mocking."""

from __future__ import annotations

import io
import json
import unittest
from unittest.mock import MagicMock, patch

from backend.adapters.agent.llm_client import (
    AgentConfigError,
    AgentTransportError,
    LLMConfig,
    chat,
    ping_llm,
)


class TestLLMClient(unittest.TestCase):
    def test_missing_api_key_raises_config_error(self) -> None:
        with self.assertRaises(AgentConfigError) as ctx:
            LLMConfig(base_url="https://api.example.com", model="gpt-4o", api_key="")
        self.assertEqual(ctx.exception.code, "MISSING_API_KEY")

    @patch("urllib.request.urlopen")
    def test_chat_success_mock(self, mock_urlopen: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": '{"op": "box", "params": {}}'}}]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        cfg = LLMConfig(base_url="https://api.example.com/v1", model="test-model", api_key="sk-test")
        content = chat([{"role": "user", "content": "ping"}], cfg)
        self.assertEqual(content, '{"op": "box", "params": {}}')

    @patch("urllib.request.urlopen")
    def test_ping_llm_timing(self, mock_urlopen: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "pong"}}]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        cfg = LLMConfig(base_url="https://api.example.com/v1", model="test-model", api_key="sk-test")
        res = ping_llm(cfg)
        self.assertTrue(res["ok"])
        self.assertEqual(res["model"], "test-model")
        self.assertIn("latency_ms", res)


if __name__ == "__main__":
    unittest.main()
