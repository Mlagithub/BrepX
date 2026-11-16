"""Assembly tools on the agent surface."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from dataclasses import replace

from cadwork.design.assembly import Instance, PartRef, Transform, instance_to_json
from cadwork.design.document import apply_ops
from cadwork.service.mcp import build_mcp_server
from cadwork.service.service import CADService
from cadwork.service.store import Store


def _payload(result):
    structured = getattr(result, "structured_content", None)
    if structured is None:
        structured = getattr(result, "structuredContent", None)
    if structured is None:
        structured = json.loads(result.content[0].text)
    if isinstance(structured, dict) and set(structured) == {"result"}:
        return structured["result"]
    return structured


class AssemblyMCPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.service = CADService(Store(self.folder.name))
        part = self.service.store.create("blade")
        part = apply_ops(
            part,
            [
                {
                    "op": "add",
                    "feature": {
                        "id": "base",
                        "type": "k_box",
                        "params": {"length": 10.0, "width": 6.0, "height": 4.0},
                    },
                }
            ],
        )
        self.part = self.service.store.save(part)
        self.server = build_mcp_server(self.service)

    async def _call(self, name: str, arguments: dict):
        result = await self.server.call_tool(name, arguments)
        self.assertFalse(result.is_error, result.content)
        return _payload(result)

    def _run(self, coroutine):
        return asyncio.run(coroutine)

    def test_assembly_tool_roundtrip(self) -> None:
        async def scenario():
            created = await self._call("new_assembly", {"name": "assembly"})
            assembly_id = created["assembly"]["id"]
            payload = instance_to_json(
                Instance("blade_a", PartRef(self.part.id, 1), Transform())
            )
            state = await self._call(
                "assembly_edit",
                {
                    "assembly_id": assembly_id,
                    "base_version": 1,
                    "ops": [{"op": "add", "instance": payload}],
                },
            )
            self.assertEqual(state["assembly"]["version"], 2)
            self.assertEqual(len(state["assembly"]["instances"]), 1)

            scene = await self._call("assembly_scene", {"assembly_id": assembly_id})
            self.assertEqual(len(scene["instances"]), 1)
            self.assertEqual(len(scene["definitions"]), 1)

            bom = await self._call("assembly_bom", {"assembly_id": assembly_id})
            self.assertEqual(sum(row["quantity"] for row in bom["summary"]), 1)

            updated_part = replace(self.part, version=2)
            self.service.store.save(updated_part)
            references = await self._call(
                "assembly_references", {"assembly_id": assembly_id}
            )
            self.assertTrue(references["outdated"])
            updated = await self._call(
                "update_assembly_references",
                {
                    "assembly_id": assembly_id,
                    "base_version": 2,
                },
            )
            self.assertEqual(updated["assembly"]["version"], 3)
            self.assertEqual(updated["references"][0]["pinned_version"], 2)

        self._run(scenario())


if __name__ == "__main__":
    unittest.main()
