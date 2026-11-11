"""End-to-end agent surface: a real HTTP server, the official client, ten tools."""

from __future__ import annotations

import asyncio
import json
import socket
import tempfile
import threading
import time
import unittest

import uvicorn

from cadwork.design.document import feature_to_json
from cadwork.samples.impeller import impeller_document
from cadwork.service import create_app

EXPECTED_TOOLS = sorted([
    "cad_state", "cad_probe", "cad_resolve", "cad_catalog", "cad_begin_intent",
    "cad_preview", "cad_variants", "cad_commit", "cad_revert", "cad_render",
])


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _payload(result):
    structured = getattr(result, "structured_content", None)
    if structured is None:
        structured = getattr(result, "structuredContent", None)
    if structured is None:
        structured = json.loads(result.content[0].text)
    if isinstance(structured, dict) and set(structured) == {"result"}:
        return structured["result"]
    return structured


class MCPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.folder = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        cls.app = create_app(cls.folder.name)
        config = uvicorn.Config(cls.app, host="127.0.0.1", port=cls.port, log_level="error")
        cls.server = uvicorn.Server(config)
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        for _ in range(200):
            if cls.server.started:
                break
            time.sleep(0.05)
        cls.url = f"http://127.0.0.1:{cls.port}/mcp/"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.should_exit = True
        cls.thread.join(timeout=10)
        cls.folder.cleanup()

    def test_agent_builds_impeller_over_mcp(self) -> None:
        asyncio.run(self._scenario())

    async def _scenario(self) -> None:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async with streamable_http_client(self.url) as streams:
            read, write = streams[0], streams[1]
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                self.assertEqual(sorted(tool.name for tool in tools.tools), EXPECTED_TOOLS)

                catalog = _payload(await session.call_tool("cad_catalog", {}))
                self.assertEqual(len(catalog), 30)

                state = _payload(await session.call_tool("cad_state", {}))
                self.assertTrue(state["vacant"])
                document_id = state["document"]["id"]
                self.assertEqual(state["document"]["version"], 0)

                intent = _payload(await session.call_tool("cad_begin_intent", {
                    "document_id": document_id,
                    "prompt": "建一个九叶片叶轮",
                    "steps": [f"放置 {feature.id}" for feature in impeller_document().features],
                }))
                intent_id = intent["intent_id"]
                self.assertEqual(len(intent["steps"]), 9)

                version = 0
                for index, feature in enumerate(impeller_document().features, start=1):
                    committed = _payload(await session.call_tool("cad_commit", {
                        "document_id": document_id,
                        "base_version": version,
                        "ops": [{"op": "add", "feature": feature_to_json(feature)}],
                        "title": f"放置 {feature.id}",
                        "intent_id": intent_id,
                        "step_index": index,
                    }))
                    version = committed["document"]["version"]
                self.assertEqual(version, 9)

                state = _payload(await session.call_tool("cad_state", {"document_id": document_id}))
                self.assertFalse(state["vacant"])
                self.assertTrue(state["checks"]["ok"])
                self.assertEqual(state["active_intent"]["status"], "completed")
                self.assertGreater(len(state["focus_params"]), 0)
                self.assertGreater(state["metrics"]["faces"], 0)

                probe = _payload(await session.call_tool("cad_probe", {
                    "document_id": document_id,
                    "ref": {"source": "f5", "select": "faces",
                            "filters": [{"method": "largest"}]},
                }))
                self.assertTrue(probe["ref_probe"]["ok"])
                self.assertEqual(probe["ref_probe"]["count"], 1)

                resolved = _payload(await session.call_tool("cad_resolve", {
                    "document_id": document_id, "phrase": "最后那个",
                }))
                self.assertIn("matches", resolved)

                preview = _payload(await session.call_tool("cad_preview", {
                    "document_id": document_id,
                    "ops": [{"op": "update", "id": "f3", "params": {"count": 11}}],
                    "base_version": version,
                }))
                self.assertIn("f3", preview["diff"]["changed"])
                self.assertGreaterEqual(preview["metrics"]["faces"], 1)
                still = _payload(await session.call_tool("cad_state", {"document_id": document_id}))
                self.assertEqual(still["document"]["version"], version)

                reverted = _payload(await session.call_tool("cad_revert", {
                    "document_id": document_id, "target_version": 4, "title": "回到四步",
                }))
                self.assertEqual(len(reverted["document"]["features"]), 4)
                version = reverted["document"]["version"]

                image = await session.call_tool("cad_render", {"document_id": document_id})
                self.assertFalse(image.is_error, image.content)
                self.assertTrue(any(item.type == "image" for item in image.content))


if __name__ == "__main__":
    unittest.main()
