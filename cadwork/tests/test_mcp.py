"""End-to-end MCP test: a real HTTP server, the official client, ten tools."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import tempfile
import threading
import time
import unittest

import uvicorn

from cadwork.design.document import feature_to_json
from cadwork.design.features import FEATURES
from cadwork.samples.impeller import impeller_document
from cadwork.service import create_app


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
                self.assertEqual(
                    sorted(tool.name for tool in tools.tools),
                    sorted(["doc_create", "doc_list", "doc_read", "catalog", "feature_add",
                            "feature_update", "feature_remove", "preview", "checks", "export",
                            "render_png", "doc_summary", "doc_resolve"]),
                )

                catalog = _payload(await session.call_tool("catalog", {}))
                self.assertEqual({entry["type"] for entry in catalog}, set(FEATURES))

                missing = await session.call_tool("doc_read", {"document_id": "nope"})
                self.assertTrue(missing.is_error)
                self.assertIn("NOT_FOUND", missing.content[0].text)

                created = _payload(await session.call_tool("doc_create", {"name": "MCP"}))
                document_id = created["id"]
                version = created["version"]

                for feature in impeller_document().features:
                    result = await session.call_tool("feature_add", {
                        "document_id": document_id,
                        "base_version": version,
                        "feature": feature_to_json(feature),
                    })
                    self.assertFalse(result.is_error, result.content)
                    version = _payload(result)["document"]["version"]

                checks = _payload(await session.call_tool("checks", {"document_id": document_id}))
                self.assertTrue(all(
                    check["ok"] for feature in checks["features"] for check in feature["checks"]
                ))
                self.assertEqual(sorted(checks["tags"]), ["f6", "f7", "f8"])

                exported = await session.call_tool("export", {
                    "document_id": document_id, "format": "step",
                })
                self.assertFalse(exported.is_error, exported.content)
                path = exported.content[0].text
                self.assertTrue(os.path.exists(path))
                os.unlink(path)

                image = await session.call_tool("render_png", {"document_id": document_id})
                self.assertFalse(image.is_error, image.content)
                self.assertTrue(any(item.type == "image" for item in image.content))


if __name__ == "__main__":
    unittest.main()
