"""The agent surface: short document, plan and geometry tools over the MCP server."""

from __future__ import annotations

import asyncio
import math
import tempfile
import unittest

from cadwork.design.features import FEATURES
from cadwork.service.mcp import build_mcp_server
from cadwork.service.service import CADService
from cadwork.service.store import Store

EXPECTED_TOOLS = sorted([
    "documents", "new_document", "state", "probe", "resolve", "catalog",
    "plan_schema", "plan_add_node", "preview", "variants", "commit", "revert",
    "render", "plan", "plan_edit", "plan_compile", "plan_run", "intents", "import",
])

PLAN_OPS = [
    {"op": "add_node", "node": {"id": "g", "kind": "goal", "title": "make a box"}},
    {"op": "add_node", "node": {
        "id": "n1", "kind": "feature", "title": "box", "action": "k_box",
        "params": {"length": 20.0, "width": 20.0, "height": 20.0},
    }},
    {"op": "add_node", "node": {
        "id": "c1", "kind": "check", "title": "has volume", "deps": ["n1"],
        "expect": [{"metric": "volume", "op": "ge", "value": 1.0}],
    }},
]


def _payload(result):
    structured = getattr(result, "structured_content", None)
    if structured is None:
        structured = getattr(result, "structuredContent", None)
    if structured is None:
        import json

        structured = json.loads(result.content[0].text)
    if isinstance(structured, dict) and set(structured) == {"result"}:
        return structured["result"]
    return structured


class MCPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.service = CADService(Store(self.folder.name))
        self.server = build_mcp_server(self.service)

    def _run(self, coroutine):
        return asyncio.run(coroutine)

    async def _call(self, name: str, arguments: dict):
        result = await self.server.call_tool(name, arguments)
        self.assertFalse(result.is_error, result.content)
        return _payload(result)

    def test_exactly_the_short_tool_names(self) -> None:
        async def scenario():
            tools = await self.server.list_tools()
            self.assertEqual(sorted(tool.name for tool in tools), EXPECTED_TOOLS)
            self.assertEqual(len(tools), 19)
            for tool in tools:
                self.assertFalse(tool.name.startswith("cad_"), tool.name)

        self._run(scenario())

    def test_agent_plans_runs_and_reads_state(self) -> None:
        async def scenario():
            state = await self._call("state", {})
            self.assertTrue(state["vacant"])
            document_id = state["document"]["id"]
            self.assertEqual(state["document"]["version"], 0)
            self.assertIsNone(state["plan"])

            catalog = await self._call("catalog", {})
            self.assertEqual({entry["type"] for entry in catalog}, set(FEATURES))
            self.assertIn("k_box", {entry["type"] for entry in catalog})
            self.assertIn("pattern", {entry["type"] for entry in catalog})
            self.assertIn("cavity", {entry["type"] for entry in catalog})

            edited = await self._call("plan_edit", {
                "document_id": document_id,
                "ops": PLAN_OPS,
                "goal": "make a box",
            })
            plan = edited["plan"]
            self.assertEqual(plan["goal"], "make a box")
            self.assertEqual([node["id"] for node in plan["nodes"]], ["g", "n1", "c1"])

            compiled = await self._call("plan_compile", {"document_id": document_id})
            self.assertTrue(compiled["ok"], compiled)
            self.assertEqual(compiled["ops_count"], 1)

            ran = await self._call("plan_run", {
                "document_id": document_id, "node_id": "n1",
            })
            self.assertEqual(ran["document_version"], 1)
            nodes = {node["id"]: node for node in ran["plan"]["nodes"]}
            self.assertEqual(nodes["n1"]["status"], "done")

            state = await self._call("state", {"document_id": document_id})
            self.assertFalse(state["vacant"])
            self.assertTrue(state["checks"]["ok"])
            self.assertEqual(state["metrics"]["faces"], 6)
            self.assertAlmostEqual(state["metrics"]["volume"], 8000.0, places=1)
            self.assertIsNotNone(state["plan"])
            self.assertEqual(state["plan"]["nodes"], 3)
            self.assertGreater(len(state["focus_params"]), 0)

            checked = await self._call("plan_run", {
                "document_id": document_id, "node_id": "c1", "base_version": 1,
            })
            nodes = {node["id"]: node for node in checked["plan"]["nodes"]}
            self.assertEqual(nodes["c1"]["status"], "done")
            self.assertIn("volume", nodes["c1"]["observed"])

            preview = await self._call("preview", {
                "document_id": document_id,
                "ops": [{"op": "update", "id": "n1", "params": {"length": 40.0}}],
                "base_version": 1,
            })
            self.assertIn("n1", preview["diff"]["changed"])
            self.assertAlmostEqual(preview["metrics"]["volume"], 16000.0, places=1)
            still = await self._call("state", {"document_id": document_id})
            self.assertEqual(still["document"]["version"], 1)

            probe = await self._call("probe", {
                "document_id": document_id,
                "ref": {"source": "n1", "select": "faces",
                        "filters": [{"method": "top"}]},
            })
            self.assertTrue(probe["ref_probe"]["ok"])
            self.assertEqual(probe["ref_probe"]["count"], 1)

            resolved = await self._call("resolve", {
                "document_id": document_id, "phrase": "最后那个",
            })
            self.assertIn("matches", resolved)

            image = await self.server.call_tool("render", {"document_id": document_id})
            self.assertFalse(image.is_error, image.content)
            self.assertTrue(any(item.type == "image" for item in image.content))

            reverted = await self._call("revert", {
                "document_id": document_id, "target_version": 0,
                "title": "回到空白",
            })
            self.assertEqual(reverted["document"]["version"], 2)
            self.assertEqual(reverted["document"]["features"], [])

        self._run(scenario())

    def test_document_tools_and_schema(self) -> None:
        async def scenario():
            created = await self._call("new_document", {"name": "fresh"})
            document_id = created["id"]
            state = await self._call("state", {"document_id": document_id})
            self.assertTrue(state["vacant"])
            listed = await self._call("documents", {})
            self.assertIn(document_id, {item["id"] for item in listed})
            schema = await self._call("plan_schema", {})
            self.assertIn("add_node", schema["ops"])
            self.assertIn("kind", schema["node"])

        self._run(scenario())

    def test_non_finite_probe_values_are_not_json(self) -> None:
        from cadwork.service.mcp import _json_safe

        self.assertEqual(_json_safe(float("nan")), None)
        self.assertEqual(_json_safe(float("inf")), None)
        self.assertEqual(_json_safe({"x": [1.0, float("-inf")]}), {"x": [1.0, None]})
        negative_zero = _json_safe({"x": -0.0})["x"]
        self.assertEqual(negative_zero, 0.0)
        self.assertEqual(math.copysign(1.0, negative_zero), 1.0)

    def test_commit_revert_and_intent_notes(self) -> None:
        async def scenario():
            state = await self._call("state", {})
            document_id = state["document"]["id"]

            committed = await self._call("commit", {
                "document_id": document_id,
                "base_version": 0,
                "ops": [{"op": "add", "feature": {
                    "id": "b1", "type": "k_box",
                    "params": {"length": 20.0, "width": 20.0, "height": 20.0},
                }}],
                "title": "box",
            })
            self.assertEqual(committed["document"]["version"], 1)
            self.assertEqual(len(committed["document"]["features"]), 1)
            self.assertEqual(committed["build"]["features"][0]["id"], "b1")

            self.service.add_intent_note(document_id, "把方块加长到 40")
            listed = await self._call("intents", {"document_id": document_id})
            self.assertEqual(len(listed["intents"]), 1)
            cleared = await self._call("intents", {
                "document_id": document_id, "action": "clear",
            })
            self.assertEqual(cleared["cleared"], 1)

            reverted = await self._call("revert", {
                "document_id": document_id, "target_version": 0,
            })
            self.assertEqual(reverted["document"]["version"], 2)
            self.assertEqual(reverted["document"]["features"], [])

        self._run(scenario())


if __name__ == "__main__":
    unittest.main()
