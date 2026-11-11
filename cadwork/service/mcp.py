"""Agent surface: ten tools covering perceive, probe, preview, commit and self-check."""

from __future__ import annotations

import io
import os
import tempfile
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
    for label, data in views:
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
            "A parametric CAD document whose geometry is a compiled product. "
            "Perceive with cad_state, measure with cad_probe, plan with cad_begin_intent, "
            "try changes with cad_preview or cad_variants, then commit with cad_commit. "
            "Every write needs the current base_version, and a commit must pass all checks."
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
    def cad_state(document_id: str | None = None) -> dict[str, Any]:
        """Read the document's projection: version, features, milestone chain, checks, metrics and active intent."""
        try:
            return service.state(_active_document(document_id))
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def cad_probe(
        document_id: str,
        ref: dict[str, Any] | None = None,
        feature_id: str | None = None,
        picked_point: list[float] | None = None,
        picked_normal: list[float] | None = None,
        picked_area: float | None = None,
    ) -> dict[str, Any]:
        """Measure the real bounding box, dry-run a semantic selector, or resolve a picked point to a reference."""
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
    def cad_resolve(document_id: str, phrase: str) -> dict[str, Any]:
        """Map a spoken reference such as "左边的沉头" to feature ids with confidence and a clarifying question."""
        try:
            return service.resolve_reference(document_id, phrase)
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def cad_catalog(category: str | None = None) -> list[dict[str, Any]]:
        """List the declarative geometry steps with their parameter schemas and input roles."""
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
    def cad_begin_intent(document_id: str, prompt: str, steps: list[str],
                         base_version: int | None = None) -> dict[str, Any]:
        """Register this turn's intent and its milestone titles so the canvas can light up the stepper."""
        try:
            return service.begin_intent(document_id, prompt, steps, base_version)
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def cad_preview(document_id: str, ops: list[dict[str, Any]],
                    base_version: int | None = None) -> dict[str, Any]:
        """Compile a candidate edit without writing it; returns checks, metrics and changed faces."""
        try:
            return service.preview(document_id, ops, base_version)
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def cad_variants(
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
    def cad_commit(
        document_id: str,
        base_version: int,
        ops: list[dict[str, Any]],
        title: str,
        focus_params: list[dict[str, Any]] | None = None,
        intent_id: str | None = None,
        step_index: int | None = None,
    ) -> dict[str, Any]:
        """Atomically write a milestone: check the version lock, compile, pass every check, then broadcast."""
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
    def cad_revert(document_id: str, target_version: int,
                   title: str | None = None) -> dict[str, Any]:
        """Republish an earlier version's features as a new milestone instead of rewriting history."""
        try:
            return service.revert(document_id, target_version, title)
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def cad_render(document_id: str, views: list[str] | None = None,
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

    return server
