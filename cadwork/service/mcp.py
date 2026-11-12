"""Agent surface: perceive, plan, execute and verify a parametric CAD document.

The tool names are short because dsh already namespaces them as ``mcp__cad__*``.
"""

from __future__ import annotations

import io
from typing import Any

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .service import CADService, ServiceError


def _fail(exc: ServiceError) -> ToolError:
    message = f"{exc.code}: {exc.message}"
    if exc.hint:
        message = f"{message} (hint: {exc.hint})"
    return ToolError(message)


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
            "A parametric CAD document. Read with state, measure with probe, and resolve "
            "spoken references with resolve. For a modelling request, maintain the plan "
            "(plan, plan_edit, plan_compile) and execute one ready node at a time with "
            "plan_run; never invent kernel code. Use preview when a direct edit is simpler, "
            "render for visual checks, and import to freeze a STEP/IGES base body. Every "
            "write needs the current base_version; a node must pass its own checks."
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
            return service.probe(
                document_id,
                feature_id=feature_id,
                ref=ref,
                picked_point=picked_point,
                picked_normal=picked_normal,
                picked_area=picked_area,
            )
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def resolve(document_id: str, phrase: str) -> dict[str, Any]:
        """Map a spoken reference such as "左边的沉头" to feature ids with a clarifying question."""
        try:
            return service.resolve_reference(document_id, phrase)
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
        """Add, update or remove plan nodes. Ops: add_node, update_node, remove_node, set_goal."""
        try:
            return service.plan_edit(document_id, ops, base_revision=base_revision, goal=goal)
        except ServiceError as exc:
            raise _fail(exc) from exc

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
