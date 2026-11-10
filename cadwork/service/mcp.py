"""MCP surface: ten tools over the same CADService the HTTP API uses."""

from __future__ import annotations

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


def build_mcp_server(service: CADService) -> MCPServer:
    server = MCPServer(
        "cadwork",
        instructions=(
            "A parametric CAD document. Read the catalog, add features, preview, "
            "then apply. Every write needs the current base_version. "
            "Geometry is never sent to you: use doc_read, checks and render_png."
        ),
    )

    @server.tool()
    def doc_summary(document_id: str) -> dict[str, Any]:
        """Read the document the way a person would: every feature named in plain
        words ("沉头孔 Ø10"), its editable parameters, whether it is on, and what
        the build produced. Start here before changing anything."""
        try:
            return service.summary(document_id)
        except ServiceError as exc:
            raise _fail(exc)

    @server.tool()
    def doc_resolve(document_id: str, phrase: str) -> dict[str, Any]:
        """Turn what the user said ("左边的沉头", "右边那个孔", "最后那个") into
        feature ids, with the reasons for each match. When `confident` is false,
        ask the user the returned `question` instead of guessing."""
        try:
            return service.resolve_reference(document_id, phrase)
        except ServiceError as exc:
            raise _fail(exc)

    @server.tool()
    def doc_create(name: str = "Untitled") -> dict[str, Any]:
        """Create an empty document and return it."""
        document = service.store.create(name)
        return service.document_json(document.id)

    @server.tool()
    def doc_list() -> list[dict[str, Any]]:
        """List documents with id, name, version and feature count."""
        return service.list_documents()

    @server.tool()
    def doc_read(document_id: str) -> dict[str, Any]:
        """Read one document: features, version and build metrics."""
        try:
            return service.document_json(document_id)
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def catalog() -> list[dict[str, Any]]:
        """Feature types with their parameter schemas and input roles."""
        return service.catalog()

    @server.tool()
    def feature_add(document_id: str, base_version: int, feature: dict[str, Any]) -> dict[str, Any]:
        """Append one feature. Feature shape: {id, type, params, refs}."""
        try:
            return service.apply(document_id, base_version, [{"op": "add", "feature": feature}])
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def feature_update(
        document_id: str,
        base_version: int,
        feature_id: str,
        params: dict[str, Any] | None = None,
        refs: dict[str, Any] | None = None,
        enabled: bool | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Patch one feature's params, refs, enabled flag or note."""
        op: dict[str, Any] = {"op": "update", "id": feature_id}
        if params is not None:
            op["params"] = params
        if refs is not None:
            op["refs"] = refs
        if enabled is not None:
            op["enabled"] = enabled
        if note is not None:
            op["note"] = note
        try:
            return service.apply(document_id, base_version, [op])
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def feature_remove(document_id: str, base_version: int, feature_id: str) -> dict[str, Any]:
        """Remove one feature if nothing references it."""
        try:
            return service.apply(document_id, base_version,
                                 [{"op": "remove", "id": feature_id}])
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def preview(document_id: str, ops: list[dict[str, Any]]) -> dict[str, Any]:
        """Dry-run a batch of ops. Returns metrics and a diff; never persists."""
        try:
            return service.preview(document_id, ops)
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def checks(document_id: str) -> dict[str, Any]:
        """Run every feature check and return the results."""
        try:
            return service.checks(document_id)
        except ServiceError as exc:
            raise _fail(exc) from exc

    @server.tool()
    def export(document_id: str, format: str = "step", feature: str | None = None) -> str:
        """Export step, stl, glb, dxf or cfd; returns the file path."""
        try:
            payload, _media_type = service.export(document_id, format, feature)
        except ServiceError as exc:
            raise _fail(exc) from exc
        suffix = "json" if format == "cfd" else format
        descriptor, path = tempfile.mkstemp(prefix=f"{document_id}-", suffix=f".{suffix}")
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
        return path

    @server.tool()
    def render_png(document_id: str, feature: str | None = None,
                   view: str = "iso") -> Image:
        """Render a PNG of the document's display body."""
        try:
            data = service.render(document_id, feature=feature, view=view)
        except ServiceError as exc:
            raise _fail(exc) from exc
        return Image(data=data, format="png")

    return server
