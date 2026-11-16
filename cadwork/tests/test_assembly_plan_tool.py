"""The assembly plan tool: declarative JSON becomes a version-1 assembly, no B-rep."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from dataclasses import replace

from mcp.server.mcpserver.exceptions import ToolError

from cadwork.design.assembly import (
    Instance,
    PartRef,
    Transform,
    new_assembly_document,
)
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


def _assert_plain(test: unittest.TestCase, value) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            test.assertIsInstance(key, str)
            _assert_plain(test, item)
        return
    if isinstance(value, list):
        for item in value:
            _assert_plain(test, item)
        return
    test.assertTrue(
        value is None or isinstance(value, (str, int, float, bool)), repr(value)
    )


class AssemblyPlanToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)
        self.service = CADService(self.store)
        self.server = build_mcp_server(self.service)

        part = self.store.create("blade")
        part = apply_ops(
            part,
            [
                {
                    "op": "add",
                    "feature": {
                        "id": "base",
                        "type": "k_box",
                        "params": {"length": 10.0, "width": 20.0, "height": 30.0},
                    },
                }
            ],
        )
        self.store.save(part)
        part = replace(
            part,
            version=2,
            configurations={"long": {"base": {"length": 20.0}}},
        )
        self.part = self.store.save(part)

        child = new_assembly_document("group", document_id="a_group", seq=2)
        child = replace(
            child,
            instances=(
                Instance(
                    "blade_c",
                    PartRef(self.part.id, 2),
                    Transform(translation=(0.0, 100.0, 0.0)),
                ),
            ),
        )
        self.child = self.store.save_assembly(child)

    def _run(self, coroutine):
        return asyncio.run(coroutine)

    async def _call(self, name: str, arguments: dict):
        result = await self.server.call_tool(name, arguments)
        self.assertFalse(result.is_error, result.content)
        return _payload(result)

    async def _tool_error(self, name: str, arguments: dict) -> str:
        with self.assertRaises(ToolError) as caught:
            await self.server.call_tool(name, arguments)
        return str(caught.exception)

    def _plan(self) -> dict:
        return {
            "name": "Drive",
            "instances": [
                {
                    "id": "blade_a",
                    "ref": {
                        "kind": "part",
                        "document_id": self.part.id,
                        "version": 2,
                    },
                    "placement": {"translation": [100.0, 0.0, 0.0]},
                },
                {
                    "id": "blade",
                    "ref": {
                        "kind": "part",
                        "document_id": self.part.id,
                        "version": 2,
                        "configuration": "long",
                    },
                    "pattern": {"kind": "linear", "count": 2, "dx": 50.0},
                },
                {
                    "id": "group_1",
                    "ref": {
                        "kind": "assembly",
                        "document_id": self.child.id,
                        "version": 1,
                    },
                    "placement": {"translation": [0.0, 0.0, 200.0]},
                },
            ],
        }

    def test_plan_creates_version_one_assembly_with_patterns(self) -> None:
        async def scenario():
            state = await self._call("assembly_plan", {"plan": self._plan()})
            assembly = state["assembly"]
            self.assertEqual(assembly["version"], 1)
            self.assertEqual(assembly["name"], "Drive")
            self.assertEqual(
                [item["id"] for item in assembly["instances"]],
                ["blade_a", "blade_0", "blade_1", "group_1"],
            )

            build = state["build"]
            self.assertTrue(build["ok"])
            self.assertEqual(
                [item["path"] for item in build["instances"]],
                ["blade_a", "blade_0", "blade_1", "group_1", "group_1/blade_c"],
            )
            by_path = {item["path"]: item for item in build["instances"]}
            self.assertEqual(
                by_path["blade_0"]["placement"]["translation"], [0.0, 0.0, 0.0]
            )
            self.assertEqual(
                by_path["blade_1"]["placement"]["translation"], [50.0, 0.0, 0.0]
            )
            self.assertEqual(
                by_path["group_1/blade_c"]["placement"]["translation"],
                [0.0, 100.0, 200.0],
            )
            self.assertEqual(by_path["group_1"]["definition_kind"], "assembly")
            self.assertEqual(by_path["blade_0"]["configuration"], "long")

        self._run(scenario())

    def test_bom_counts_are_recursive_and_quantity_correct(self) -> None:
        async def scenario():
            state = await self._call("assembly_plan", {"plan": self._plan()})
            bom = {
                (entry["document_id"], entry["version"], entry["configuration"]): entry
                for entry in state["build"]["bom"]
            }
            default = bom[(self.part.id, 2, "default")]
            long = bom[(self.part.id, 2, "long")]
            self.assertEqual(default["quantity"], 2)
            self.assertEqual(set(default["paths"]), {"blade_a", "group_1/blade_c"})
            self.assertEqual(long["quantity"], 2)
            self.assertEqual(set(long["paths"]), {"blade_0", "blade_1"})

        self._run(scenario())

    def test_plan_name_argument_overrides_the_payload(self) -> None:
        async def scenario():
            state = await self._call(
                "assembly_plan",
                {
                    "plan": self._plan(),
                    "name": "Custom",
                },
            )
            self.assertEqual(state["assembly"]["name"], "Custom")

        self._run(scenario())

    def test_explicit_plan_id_is_used_and_cannot_be_reused(self) -> None:
        plan = self._plan()
        plan["id"] = "a_plan_demo"

        async def scenario():
            state = await self._call("assembly_plan", {"plan": plan})
            self.assertEqual(state["assembly"]["id"], "a_plan_demo")
            message = await self._tool_error("assembly_plan", {"plan": plan})
            self.assertIn("DUPLICATE_ID", message)

        self._run(scenario())

    def test_duplicate_instance_id_is_a_tool_error(self) -> None:
        plan = {
            "instances": [
                {
                    "id": "same",
                    "ref": {
                        "kind": "part",
                        "document_id": self.part.id,
                        "version": 2,
                    },
                },
                {
                    "id": "same",
                    "ref": {
                        "kind": "part",
                        "document_id": self.part.id,
                        "version": 2,
                    },
                },
            ],
        }

        async def scenario():
            message = await self._tool_error("assembly_plan", {"plan": plan})
            self.assertIn("DUPLICATE_ID", message)

        self._run(scenario())

    def test_missing_reference_and_configuration_are_tool_errors(self) -> None:
        async def scenario():
            missing = {
                "instances": [
                    {
                        "id": "missing",
                        "ref": {
                            "kind": "part",
                            "document_id": "d_missing",
                            "version": 1,
                        },
                    }
                ],
            }
            message = await self._tool_error("assembly_plan", {"plan": missing})
            self.assertIn("REF_NOT_FOUND", message)

            bad_config = {
                "instances": [
                    {
                        "id": "bad",
                        "ref": {
                            "kind": "part",
                            "document_id": self.part.id,
                            "version": 2,
                            "configuration": "missing",
                        },
                    }
                ],
            }
            message = await self._tool_error("assembly_plan", {"plan": bad_config})
            self.assertIn("REF_CONFIG_NOT_FOUND", message)

        self._run(scenario())

    def test_malformed_plan_shapes_are_tool_errors(self) -> None:
        async def scenario():
            message = await self._tool_error("assembly_plan", {"plan": {}})
            self.assertIn("MISSING_FIELD", message)

            unknown = {"instances": [], "unexpected": 1}
            message = await self._tool_error("assembly_plan", {"plan": unknown})
            self.assertIn("UNKNOWN_FIELD", message)

            bad_kind = {
                "instances": [
                    {
                        "id": "x",
                        "ref": {
                            "kind": "sheet",
                            "document_id": "d_x",
                            "version": 1,
                        },
                    }
                ]
            }
            message = await self._tool_error("assembly_plan", {"plan": bad_kind})
            self.assertIn("INVALID_REF", message)

        self._run(scenario())

    def test_state_payload_has_no_brep(self) -> None:
        async def scenario():
            state = await self._call("assembly_plan", {"plan": self._plan()})
            self.assertEqual(set(state), {"assembly", "build", "references"})
            _assert_plain(self, state)
            encoded = json.dumps(state)
            self.assertEqual(json.loads(encoded), state)
            for item in state["build"]["instances"]:
                self.assertIsInstance(item["has_geometry"], bool)

        self._run(scenario())

    def test_schema_tool_describes_plan_shapes(self) -> None:
        async def scenario():
            schema = await self._call("assembly_plan_schema", {})
            self.assertIn("plan", schema)
            self.assertIn("instance", schema)
            self.assertIn("pattern", schema)
            self.assertIn("assembly_ref", schema)
            self.assertTrue(schema["notes"])
            _assert_plain(self, schema)

        self._run(scenario())


if __name__ == "__main__":
    unittest.main()
