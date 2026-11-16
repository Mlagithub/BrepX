"""Tests for the smlibpy client, the deterministic emitter and the script backend.

The server-backed tests start ``python -m smlibpy.mcp`` on stdio; they skip
when the kernel is missing so the rest of the suite still runs.  Keep this
module fast: one server for the client test, one for the backend tests.
"""

from __future__ import annotations

import tempfile
import unittest
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from cadwork.design.backends.base import BackendError, BackendTimeout, NodeResult
from cadwork.design.script_emit import (
    METRICS_PREFIX,
    EmitError,
    emit_node,
    supported_actions,
)


def _server_available() -> bool:
    """The server tests need only the mcp SDK and smlibpy's MCP module."""
    try:
        import mcp  # noqa: F401
        import smlibpy.mcp  # noqa: F401
    except Exception:
        return False
    return True


HAS_SERVER = _server_available()
SKIP_REASON = "smlibpy MCP server unavailable (mcp SDK or smlibpy.mcp did not import)"

if HAS_SERVER:
    from cadwork.design.backends.script import ScriptBackend, parse_metrics
    from cadwork.service.smlibpy_client import (
        RunResult,
        SmlibpyClient,
        SyncSmlibpyClient,
    )
else:  # pragma: no cover - only on a machine without smlibpy
    ScriptBackend = None  # type: ignore[assignment]
    parse_metrics = None  # type: ignore[assignment]
    RunResult = None  # type: ignore[assignment]
    SmlibpyClient = None  # type: ignore[assignment]
    SyncSmlibpyClient = None  # type: ignore[assignment]


def _server(cls: type) -> type:
    return unittest.skipUnless(HAS_SERVER, SKIP_REASON)(cls)


@dataclass(frozen=True)
class Step:
    """Minimal plan-step stand-in so the emitter tests need no compiler."""

    node_id: str
    action: str
    variable: str
    inputs: Mapping[str, Any] = field(default_factory=dict)
    params: Mapping[str, Any] = field(default_factory=dict)


def box_step(node_id: str = "1") -> Step:
    return Step(
        node_id,
        "k_box",
        f"n{node_id}",
        {},
        {"length": 10.0, "width": 20.0, "height": 30.0},
    )


class EmitterTests(unittest.TestCase):
    def test_output_is_deterministic(self) -> None:
        first = emit_node(box_step())
        second = emit_node(box_step())
        self.assertEqual(first, second)

    def test_params_are_sorted_and_literal(self) -> None:
        script = emit_node(box_step())
        self.assertIn("n1 = Box(height=30.0, length=10.0, width=20.0)", script)
        self.assertIn("from smlibpy import *", script)
        self.assertIn("import json", script)
        self.assertIn("import math", script)

    def test_metrics_marker_and_no_time_or_random(self) -> None:
        script = emit_node(box_step())
        self.assertIn(f"print({METRICS_PREFIX!r} + json.dumps", script)
        self.assertIn("sort_keys=True", script)
        for forbidden in ("time.", "datetime", "random", "uuid"):
            self.assertNotIn(forbidden, script)

    def test_method_and_boolean_rendering(self) -> None:
        shell = Step(
            "2",
            "k_shell",
            "n2",
            {"target": "n1"},
            {"thickness": 2.0, "outward": True},
        )
        self.assertIn("n2 = n1.shell(outward=True, thickness=2.0)", emit_node(shell))
        cut = Step("3", "k_cut", "n3", {"target": "n1", "others": ("n2",)}, {})
        self.assertIn("n3 = n1.cut(n2)", emit_node(cut))

    def test_enum_params(self) -> None:
        spiral = Step(
            "4",
            "k_spiral",
            "n4",
            {},
            {"start_radius": 2.0, "end_radius": 8.0, "turns": 3.0, "plane": "XY"},
        )
        self.assertIn("plane=Plane.XY", emit_node(spiral))
        twist = Step(
            "5", "k_twist", "n5", {"target": "n1"}, {"angle": 30.0, "axis": "Z"}
        )
        self.assertIn("n5 = n1.twist(angle=30.0, axis=Z)", emit_node(twist))

    def test_export_step_is_opt_in(self) -> None:
        without = emit_node(box_step())
        self.assertNotIn("export_step", without)
        with tempfile.TemporaryDirectory() as folder:
            path = folder + r"\n1.step"
            script = emit_node(box_step(), step_path=path)
            self.assertIn("export_step(n1, ", script)
            self.assertIn("n1.step", script)

    def test_unknown_action_raises(self) -> None:
        step = Step("9", "k_nope", "n9")
        with self.assertRaises(EmitError) as caught:
            emit_node(step)
        self.assertIn("supported actions", str(caught.exception))
        self.assertEqual(caught.exception.code, "ACTION_UNKNOWN")

    def test_unknown_parameter_and_missing_input_raise(self) -> None:
        with self.assertRaises(EmitError) as caught:
            emit_node(Step("1", "k_box", "n1", {}, {"diameter": 3.0}))
        self.assertEqual(caught.exception.code, "PLAN_INVALID")
        with self.assertRaises(EmitError):
            emit_node(Step("2", "k_cut", "n2", {"target": "n1"}, {}))
        with self.assertRaises(EmitError):
            emit_node(
                Step(
                    "1",
                    "k_box",
                    "n1",
                    {},
                    {"length": object(), "width": 1.0, "height": 1.0},
                )
            )
        self.assertIn("k_box", supported_actions())


class ParseMetricsTests(unittest.TestCase):
    def test_parse_metrics_after_output(self) -> None:
        text = (
            "Output:\n6000.0\n\n"
            '__BREPX_METRICS__{"bbox": {"max": [5.0], "min": [-5.0]}, "volume": 6000.0}\n\n'
            "Shown: nothing yet."
        )
        if parse_metrics is None:  # pragma: no cover
            self.skipTest(SKIP_REASON)
        metrics = parse_metrics(text)
        self.assertEqual(metrics["volume"], 6000.0)
        self.assertEqual(metrics["bbox"]["min"], [-5.0])

    def test_missing_marker_is_none(self) -> None:
        if parse_metrics is None:  # pragma: no cover
            self.skipTest(SKIP_REASON)
        self.assertIsNone(parse_metrics("just some text"))
        self.assertIsNone(parse_metrics(METRICS_PREFIX + "not json"))


@_server
class SmlibpyClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_tools_and_run_box(self) -> None:
        client = SmlibpyClient()
        await client.start()
        try:
            self.assertIsNotNone(client.server_info)
            tools = await client.list_tools()
            self.assertEqual(len(tools), 15)
            self.assertIn("run_script", {tool.name for tool in tools})

            result = await client.run("new", "box = Box(10, 20, 30)\nprint(box.volume)")
            self.assertTrue(result.ok, result.text)
            self.assertIsNotNone(result.session_id)
            self.assertRegex(result.session_id or "", r"^s-[a-z0-9]+$")
            self.assertIn("6000", result.text)

            failed = await client.run(
                result.session_id or "", "raise RuntimeError('nope')"
            )
            self.assertFalse(failed.ok)
            self.assertIn("Script failed", failed.text)
        finally:
            await client.close()


@_server
class SyncFacadeTests(unittest.TestCase):
    def test_sync_facade_opens_session(self) -> None:
        client = SyncSmlibpyClient()
        try:
            self.assertEqual(len(client.list_tools()), 15)
            session = client.new_session()
            self.assertRegex(session, r"^s-[a-z0-9]+$")
            self.assertIn("The session is empty", client.clear(session))
        finally:
            client.close()


@_server
class ScriptBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.backend = ScriptBackend(timeout_s=120.0)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.backend.close()

    def test_single_box_node(self) -> None:
        result = self.backend.build_node("doc-box", box_step())
        self.assertIsInstance(result, NodeResult)
        self.assertAlmostEqual(result.metrics["volume"], 6000.0, places=6)
        self.assertEqual(result.metrics["faces"], 6)
        self.assertEqual(result.metrics["edges"], 12)
        self.assertEqual(result.metrics["solids"], 1)
        self.assertIs(result.metrics["watertight"], True)
        self.assertEqual(result.metrics["bbox"]["min"], [-5.0, -10.0, -15.0])
        self.assertEqual(result.metrics["bbox"]["max"], [5.0, 10.0, 15.0])
        self.assertIsNotNone(self.backend.session_id("doc-box"))
        self.assertIn("1", self.backend.committed_nodes("doc-box"))

    def test_export_step_node(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = folder + r"\doc-export.step"
            result = self.backend.build_node(
                "doc-export", box_step("7"), step_path=path
            )
            self.assertEqual(result.step_path, path)
            with open(path, "rb") as handle:
                self.assertGreater(len(handle.read()), 0)

    def test_bad_script_raises_backend_error(self) -> None:
        step = Step(
            "9",
            "k_box",
            "n9",
            {},
            {"length": "ten", "width": 20.0, "height": 30.0},
        )
        with self.assertRaises(BackendError) as caught:
            self.backend.build_node("doc-fail", step)
        self.assertEqual(caught.exception.code, "SCRIPT_FAILED")
        self.assertTrue(caught.exception.raw)
        self.assertNotIn("9", self.backend.committed_nodes("doc-fail"))

    def test_unknown_action_raises_emit_error(self) -> None:
        with self.assertRaises(EmitError):
            self.backend.build_node("doc-unknown", Step("u", "k_nope", "nu"))

    def test_replay_two_steps(self) -> None:
        box = box_step("1")
        shell = Step("2", "k_shell", "n2", {"target": "n1"}, {"thickness": 2.0})
        first = self.backend.build_node("doc-replay", box)
        second = self.backend.build_node("doc-replay", shell)
        self.assertLess(second.metrics["volume"], first.metrics["volume"])

        replay = self.backend.replay("doc-replay", [box, shell])
        self.assertIsNotNone(replay)
        self.assertAlmostEqual(replay["volume"], second.metrics["volume"], places=6)
        self.assertEqual(
            self.backend.committed_nodes("doc-replay"), frozenset({"1", "2"})
        )

    def test_reset_forgets_session_and_commits(self) -> None:
        first = box_step("3")
        self.backend.build_node("doc-reset", first)
        old_session = self.backend.session_id("doc-reset")
        self.backend.reset("doc-reset")
        self.assertIsNone(self.backend.session_id("doc-reset"))
        self.assertEqual(self.backend.committed_nodes("doc-reset"), frozenset())
        self.backend.build_node("doc-reset", first)
        self.assertNotEqual(self.backend.session_id("doc-reset"), old_session)


class _StubClient:
    """Client double for failure paths that must not start a server."""

    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.cleared: list[str] = []

    def start(self) -> _StubClient:
        return self

    def new_session(self) -> str:
        return "s-stub"

    def run(
        self,
        session: str,
        script: str,
        label: str | None = None,
        timeout_s: float = 120.0,
    ) -> Any:
        if self.error is not None:
            raise self.error
        return self.result

    def clear(self, session: str) -> str:
        self.cleared.append(session)
        return "The session is empty."

    def close(self) -> None:
        pass


class BackendFailureTests(unittest.TestCase):
    def test_server_side_timeout_maps_to_backend_timeout(self) -> None:
        if ScriptBackend is None:  # pragma: no cover
            self.skipTest(SKIP_REASON)
        result = RunResult(
            ok=False,
            text="Script failed:\nThe script was stopped: it did not finish within 1 s.",
        )
        backend = ScriptBackend(client=_StubClient(result=result))
        with self.assertRaises(BackendTimeout) as caught:
            backend.build_node("doc-timeout", box_step())
        self.assertEqual(caught.exception.code, "SCRIPT_TIMEOUT")
        self.assertEqual(backend.committed_nodes("doc-timeout"), frozenset())

    def test_client_timeout_invalidates_session(self) -> None:
        if ScriptBackend is None:  # pragma: no cover
            self.skipTest(SKIP_REASON)
        backend = ScriptBackend(client=_StubClient(error=BackendTimeout("slow")))
        with self.assertRaises(BackendTimeout):
            backend.build_node("doc-timeout-2", box_step())
        self.assertIsNone(backend.session_id("doc-timeout-2"))

    def test_missing_metrics_raises_backend_error(self) -> None:
        if ScriptBackend is None:  # pragma: no cover
            self.skipTest(SKIP_REASON)
        backend = ScriptBackend(
            client=_StubClient(result=RunResult(ok=True, text="Output:\nnothing"))
        )
        with self.assertRaises(BackendError) as caught:
            backend.build_node("doc-nometrics", box_step())
        self.assertIn("no __BREPX_METRICS__", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
