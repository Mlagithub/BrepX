"""Agent surface: perceive, plan, execute and verify a parametric CAD document.

The tool names are short because dsh already namespaces them as ``mcp__cad__*``.
"""

from __future__ import annotations

import io
import math
import numbers
from typing import Any

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .service import CADService, ServiceError


def _fail(exc: ServiceError) -> ToolError:
    message = f"{exc.code}: {exc.message}"
    if exc.hint:
        message = f"{message} (hint: {exc.hint})"
    return ToolError(message)


def _json_safe(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        number = float(value)
        if not math.isfinite(number):
            return None
        # -0.0 and 0.0 are equal in Python but JSON.stringify(0.0) and
        # JSON.stringify(-0.0) are observably different; the host checks that
        # the value survives that round trip, so normalize the sign.
        return 0.0 if number == 0.0 else number
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _compose(views: list[tuple[str, bytes]]) -> bytes:
    from PIL import Image as PILImage

    images = []
    for _label, data in views:
        try:
            images.append(PILImage.open(io.BytesIO(data)).convert("RGB"))
        except Exception:
            continue
    if not images:
        raise ValueError("no rendered view could be decoded")
    if len(images) == 1:
        buffer = io.BytesIO()
        images[0].save(buffer, format="PNG")
        return buffer.getvalue()
    width = max(image.width for image in images)
    height = sum(image.height for image in images)
    sheet = PILImage.new("RGB", (width, height), (255, 255, 255))
    top = 0
    for image in images:
        sheet.paste(image, (0, top))
        top += image.height
    buffer = io.BytesIO()
    sheet.save(buffer, format="PNG")
    return buffer.getvalue()


def build_mcp_server(service: CADService) -> MCPServer:
    server = MCPServer(
        "cadwork",
        instructions=(
            "A parametric CAD document. A user message that starts with [当前文档 <id> ...] "
            "already names the active document for that turn: call state with that id and edit "
            "that document; do not create a new document or ask which document. For a request "
            "without that tag, start with new_document; use documents to list existing work, "
            "then state with that document id to continue. "
            "Read with state, measure with probe, and resolve spoken references with resolve. "
            "Before any change that refers to existing geometry by a demonstrative or position "
            "(这个/那个/左边/右边/上面/下面/刚才/最后/它/该) without a feature id, call resolve with "
            "the exact phrase and any picked anchor. If can_write is false, do not call plan, "
            "plan_edit, plan_run or any write: ask its question with 2-4 concrete id/name/basis "
            "options and the anchor. Reuse the id the user picks; do not resolve the same phrase "
            "twice. A skipped or unanswered clarifying question is not permission to write; if "
            "the request has no concrete value, ask for it or stop. "
            "For a modelling request, maintain the plan (plan, plan_edit, plan_compile) and "
            "execute one ready node at a time with plan_run; never invent kernel code. Use "
            "preview when a direct edit is simpler, render for visual checks, and import to "
            "freeze a STEP/IGES base body. Every write needs the current base_version; a node "
            "must pass its own checks."
        ),
    )

    def _active_document(document_id: str | None) -> str:
        if document_id:
            return document_id
        documents = service.list_documents()
        if documents:
            return documents[0]["id"]
        return service.store.create("Workbench").id

    @server.tool()
    def documents() -> list[dict[str, Any]]:
        """List CAD documents with id, name, version and feature count."""
        return service.list_documents()

    @server.tool()
    def new_document(name: str = "Workbench") -> dict[str, Any]:
        """Create a blank CAD document and return its id for all following calls."""
        try:
            document = service.store.create(name)
            return service.document_json(document.id)
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def state(document_id: str | None = None) -> dict[str, Any]:
        """Read the document projection: version, features, checks, metrics and the plan summary."""
        try:
            return service.state(_active_document(document_id))
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def probe(
        document_id: str,
        ref: dict[str, Any] | None = None,
        feature_id: str | None = None,
        picked_point: list[float] | None = None,
        picked_normal: list[float] | None = None,
        picked_area: float | None = None,
    ) -> dict[str, Any]:
        """Measure the real bounding box, dry-run a semantic selector, or resolve a picked point."""
        try:
            return _json_safe(service.probe(
                document_id,
                feature_id=feature_id,
                ref=ref,
                picked_point=picked_point,
                picked_normal=picked_normal,
                picked_area=picked_area,
            ))
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def resolve(document_id: str, phrase: str, anchor: str | None = None) -> dict[str, Any]:
        """Map a spoken reference to feature ids and decide if a write is allowed.

        `can_write` is false unless the phrase is confident or a picked feature
        anchor is supplied; in that case ask the returned question with its
        concrete candidates and do not plan or edit yet.
        """
        try:
            return service.resolve_reference(document_id, phrase, anchor)
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def catalog(category: str | None = None) -> list[dict[str, Any]]:
        """List the generated actions and adapters with their parameter schemas and input roles."""
        try:
            entries = service.catalog()
        except ServiceError as exc:
            raise _fail(exc) from exc
        if not category:
            return entries
        needle = category.lower()
        return [
            entry for entry in entries
            if needle in entry["type"].lower() or needle in entry.get("summary", "").lower()
        ]

    @server.tool()
    def plan_schema() -> dict[str, Any]:
        """Return the exact node, ref, filter, expect and plan-edit op shapes."""
        return {
            "node": {
                "id": "plate",
                "kind": "feature",
                "title": "80x80x20 plate",
                "action": "k_box",
                "params": {"length": 80.0, "width": 80.0, "height": 20.0},
                "refs": {},
                "deps": [],
                "expect": [],
            },
            "cut_node": {
                "id": "hole",
                "kind": "feature",
                "title": "cut the bore",
                "action": "k_cut",
                "params": {},
                "refs": {
                    "target": {"source": "plate", "select": "self"},
                    "others": [{"source": "tool", "select": "self"}],
                },
                "deps": ["plate", "tool"],
                "expect": [],
            },
            "ref": {
                "source": "hole",
                "select": "faces",
                "filters": [{"method": "nearest", "args": [[0.0, 0.0, 10.0]]}],
            },
            "expect_item": {"metric": "solids", "op": "eq", "value": 1},
            "blend_group": {
                "id": "blend", "kind": "feature", "action": "blend_group",
                "params": {"kind": "fillet", "size": 2.0, "propagate": True,
                           "on_failure": "fail"},
                "refs": {"target": {"source": "body", "select": "self"},
                         "edges": {"source": "body", "select": "edges",
                                   "filters": [{"method": "concave"}]}},
                "deps": ["body"],
            },
            "thread": {
                "id": "thread", "kind": "feature", "action": "thread",
                "params": {"diameter": 12.0, "pitch": 1.75, "length": 30.0,
                           "depth": 1.2, "center": [0.0, 0.0, 0.0],
                           "left_handed": False},
                "refs": {"target": {"source": "body", "select": "self"}},
                "deps": ["body"],
            },
            "stepped_bore": {
                "id": "bearing", "kind": "feature", "action": "stepped_bore",
                "params": {"diameter_1": 40.0, "depth_1": 8.0, "diameter_2": 30.0,
                           "through": True, "center": [0.0, 0.0, 0.0], "axis": "X"},
                "refs": {"target": {"source": "body", "select": "self"}},
                "deps": ["body"],
            },
            "ops": {
                "add_node": {"op": "add_node", "node": "<node shape above>"},
                "update_node": {"op": "update_node",
                                "node": {"id": "plate", "params": {"length": 100.0}}},
                "remove_node": {"op": "remove_node", "id": "plate"},
                "set_goal": {"op": "set_goal", "goal": "plate with a bore"},
            },
            "notes": [
                "update_node replaces the whole params object; include every required parameter.",
                "deps must name earlier nodes; refs.source must name an earlier feature.",
                "kind is required: goal, feature or check.",
            ],
        }

    @server.tool()
    def preview(document_id: str, ops: list[dict[str, Any]],
                base_version: int | None = None) -> dict[str, Any]:
        """Compile a candidate edit without writing it; returns checks, metrics and changed faces."""
        try:
            return service.preview(document_id, ops, base_version)
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def variants(
        document_id: str,
        variants: list[dict[str, Any]] | None = None,
        feature: str | None = None,
        params: dict[str, list[Any]] | None = None,
    ) -> dict[str, Any]:
        """Build two to four candidate deltas side by side and report every surviving option."""
        try:
            return service.create_variants(
                document_id,
                variants=variants,
                feature=feature,
                params=params,
                include_base=False,
                thumbs=False,
            )
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def commit(
        document_id: str,
        base_version: int,
        ops: list[dict[str, Any]],
        title: str,
        focus_params: list[dict[str, Any]] | None = None,
        intent_id: str | None = None,
        step_index: int | None = None,
    ) -> dict[str, Any]:
        """Atomically write a milestone: version lock, compile, all checks, then broadcast."""
        try:
            return service.commit(
                document_id,
                base_version,
                ops,
                title=title,
                focus_params=focus_params,
                actor="agent",
                intent_id=intent_id,
                step_index=step_index,
            )
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def revert(document_id: str, target_version: int,
               title: str | None = None) -> dict[str, Any]:
        """Republish an earlier version's features as a new milestone instead of rewriting history."""
        try:
            return service.revert(document_id, target_version, title)
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def render(document_id: str, views: list[str] | None = None,
               feature: str | None = None) -> Image:
        """Compose a qualitative multi-view picture for shape and orientation self-checking."""
        wanted = views or ["iso", "front", "top"]
        frames: list[tuple[str, bytes]] = []
        try:
            for view in wanted:
                frames.append((view, service.render(document_id, feature=feature, view=view)))
        except ServiceError as exc:
            raise _fail(exc) from exc
        try:
            data = _compose(frames)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        return Image(data=data, format="png")

    @server.tool()
    def plan(document_id: str) -> dict[str, Any]:
        """Read the current plan: goal, revision, node status, parameters, refs and observations."""
        try:
            return service.plan(document_id)
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def plan_edit(
        document_id: str,
        ops: list[dict[str, Any]],
        base_revision: int | None = None,
        goal: str | None = None,
    ) -> dict[str, Any]:
        """Edit the plan. Each op has op=add_node|update_node|remove_node|set_goal.
        Call plan_schema for the exact shapes; add_node needs a full node with kind."""
        try:
            return service.plan_edit(document_id, ops, base_revision=base_revision, goal=goal)
        except ServiceError as exc:
            raise _fail(exc) from exc
        except Exception as exc:
            raise ToolError(
                f"PLAN_INVALID: {type(exc).__name__}: {exc} "
                "(hint: call plan_schema; each op needs op and a valid node shape)"
            ) from exc

    @server.tool()
    def plan_add_node(
        document_id: str,
        node: dict[str, Any],
        base_revision: int | None = None,
        goal: str | None = None,
    ) -> dict[str, Any]:
        """Add exactly one plan node. Use this for large plans so each tool call
        carries one small JSON object instead of a multi-node ops array."""
        try:
            return service.plan_edit(
                document_id, [{"op": "add_node", "node": node}],
                base_revision=base_revision, goal=goal,
            )
        except ServiceError as exc:
            raise _fail(exc) from exc
        except Exception as exc:
            raise ToolError(
                f"PLAN_INVALID: {type(exc).__name__}: {exc} "
                "(hint: call plan_schema; the node needs id, kind and action)"
            ) from exc

    @server.tool()
    def plan_compile(document_id: str) -> dict[str, Any]:
        """Dry-run the whole plan: validate it, lower every node, and report issues and coverage."""
        try:
            return service.plan_compile(document_id)
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def plan_run(document_id: str, node_id: str,
                 base_version: int | None = None,
                 executor: str | None = None) -> dict[str, Any]:
        """Execute one ready node, commit its milestone, evaluate its checks and return the plan."""
        try:
            return service.plan_run(document_id, node_id, base_version=base_version,
                                    executor=executor)
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def intents(document_id: str, action: str = "list") -> dict[str, Any]:
        """List or clear the human's pending intent notes for this document."""
        try:
            if action == "clear":
                return {"cleared": service.store.clear_intents(document_id)}
            if action != "list":
                raise ServiceError("INVALID_ACTION", "action must be list or clear", status=400)
            return {"intents": service.store.list_intents(document_id)}
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool(name="import")
    def import_file(document_id: str, path: str, format: str = "step") -> dict[str, Any]:
        """Freeze a local STEP/IGES/B-Rep file into the document as a base body."""
        try:
            return service.import_file(document_id, path, format=format)
        except ServiceError as exc:
            raise _fail(exc) from exc

    return server
