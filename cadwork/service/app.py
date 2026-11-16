"""HTTP and MCP surface over one process: browser canvas, agent tools."""

from __future__ import annotations

import asyncio
import base64
import binascii
import gzip
import hashlib
import json
import mimetypes
import os
import queue
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

mimetypes.add_type("text/javascript", ".mjs")

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cadwork import __version__
from cadwork.design.build import BuildError
from cadwork.design.document import DocumentError, feature_to_json
from cadwork.domains import DomainError, default_registry
from cadwork.samples.impeller import impeller_document
from cadwork.samples.registry import SAMPLES
from cadwork.samples.registry import build as build_sample
from cadwork.samples.registry import catalog as sample_catalog

SAMPLE_TITLES = {name: spec.title for name, spec in SAMPLES.items()}

from .gen_tests import CASES, GEN_KEYS, run_case
from .jobs import PlanJobRegistry
from .mcp import build_mcp_server
from .preview import PREVIEW_MEDIA_TYPE, is_preview_key
from .service import CADService, ServiceError
from .store import Store, StoreError


class CreateDocument(BaseModel):
    name: str = "Untitled"


class CreateAssembly(BaseModel):
    name: str = "Untitled"


class AssemblyEditRequest(BaseModel):
    base_version: int
    ops: list[dict[str, Any]]


class AssemblyReferencesRequest(BaseModel):
    base_version: int
    instance_ids: list[str] | None = None


class EditRequest(BaseModel):
    base_version: int
    ops: list[dict[str, Any]]
    title: str | None = None


class PreviewRequest(BaseModel):
    ops: list[dict[str, Any]]
    base_version: int | None = None


class SampleRequest(BaseModel):
    params: dict[str, Any] = {}
    replace: bool = True


class VariantSpec(BaseModel):
    label: str | None = None
    ops: list[dict[str, Any]] = []


class VariantRequest(BaseModel):
    feature: str | None = None
    params: dict[str, list[Any]] | None = None
    variants: list[VariantSpec] | None = None
    include_base: bool = False
    base_version: int | None = None
    thumbs: bool = True


class ChangeSpec(BaseModel):
    feature_id: str
    params: dict[str, Any]


class TweakRequest(BaseModel):
    base_version: int | None = None
    changes: list[ChangeSpec]
    title: str | None = None


class RevertRequest(BaseModel):
    target_version: int
    title: str | None = None


class IntentRequest(BaseModel):
    text: str
    base_version: int | None = None


class PlanEditRequest(BaseModel):
    ops: list[dict[str, Any]]
    base_revision: int | None = None
    goal: str | None = None


class PlanRunRequest(BaseModel):
    node_id: str
    base_version: int | None = None
    executor: str | None = None


class ImportRequest(BaseModel):
    path: str
    format: str = "step"


class ImportUpload(BaseModel):
    filename: str
    data: str
    format: str | None = None


class HandleRequest(BaseModel):
    feature_id: str
    point: list[float]
    normal: list[float] = [0.0, 0.0, 1.0]
    scope: str = "face"


class GenRunRequest(BaseModel):
    key: str
    run_id: str | None = None


class PickRequest(BaseModel):
    version: int | None = None
    point: list[float]
    normal: list[float] | None = None
    area: float | None = None
    face_index: int | None = None
    feature_id: str | None = None


def _error(exc: Exception) -> JSONResponse:
    if isinstance(exc, ServiceError):
        return JSONResponse({"error": exc.to_json()}, status_code=exc.status)
    if isinstance(exc, DomainError):
        return JSONResponse({"error": exc.to_json()}, status_code=exc.status)
    if isinstance(exc, StoreError):
        return JSONResponse(
            {"error": {"code": exc.code, "message": exc.message}},
            status_code=exc.status,
        )
    if isinstance(exc, DocumentError):
        status = 409 if exc.code == "STALE_VERSION" else 400
        return JSONResponse(
            {"error": {"code": exc.code, "message": exc.message, "hint": exc.hint}},
            status_code=status,
        )
    if isinstance(exc, BuildError):
        return JSONResponse({"error": exc.to_json()}, status_code=422)
    return JSONResponse(
        {"error": {"code": "INTERNAL", "message": str(exc)}}, status_code=500
    )


def _sse(event: str, payload: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


_COMPRESSIBLE_MEDIA_TYPES = frozenset(
    {
        "application/json",
        "application/javascript",
        "application/manifest+json",
        "application/xml",
        "image/svg+xml",
    }
)
_COMPRESSION_FLOOR_BYTES = 1024


class TextCompressionMiddleware:
    """gzip text, JSON and JavaScript responses; binary payloads pass through untouched.

    A binary body (wasm, png, STEP) is already compact and some clients read it by byte
    range; event streams never complete, so they cannot be buffered. This is raw ASGI
    because the body is not observable through BaseHTTPMiddleware.
    """

    def __init__(self, inner_app: Any) -> None:
        self.app = inner_app

    def _media_allows_encoding(self, headers: dict[bytes, bytes]) -> bool:
        media_type = headers.get(b"content-type", b"").split(b";")[0].strip().lower()
        return media_type != b"text/event-stream" and (
            media_type.startswith(b"text/")
            or media_type.decode("latin-1") in _COMPRESSIBLE_MEDIA_TYPES
        )

    def _compressible(
        self, message: dict[str, Any], headers: dict[bytes, bytes]
    ) -> bool:
        status = int(message.get("status", 200))
        return (
            self._media_allows_encoding(headers)
            and status not in (204, 206, 304)
            and b"content-encoding" not in headers
            and b"content-range" not in headers
            # Accept-Ranges promises byte offsets into the body; a gzipped body would
            # shift them, so static file responses keep their own byte ranges.
            and b"accept-ranges" not in headers
        )

    @staticmethod
    def _ensure_vary(
        message: dict[str, Any], headers: dict[bytes, bytes]
    ) -> dict[str, Any]:
        """Mark a type that may be served compressed, even when this body was not.

        Caches key on Vary, so a small or already-encoded response must advertise the
        negotiation too; otherwise a cached identity body can answer a gzip request.
        """
        vary = headers.get(b"vary", b"")
        if b"accept-encoding" in vary.lower():
            return message
        rebuilt = [
            (key, value)
            for key, value in message.get("headers", [])
            if key.lower() != b"vary"
        ]
        rebuilt.append(
            (b"vary", b"Accept-Encoding" if not vary else vary + b", Accept-Encoding")
        )
        updated = dict(message)
        updated["headers"] = rebuilt
        return updated

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http" or scope.get("method") == "HEAD":
            await self.app(scope, receive, send)
            return
        request_headers = dict(scope.get("headers") or [])
        if b"gzip" not in request_headers.get(b"accept-encoding", b"").lower():
            await self.app(scope, receive, send)
            return
        start_message: dict[str, Any] | None = None
        start_headers: dict[bytes, bytes] = {}
        compressible = False
        parts: list[bytes] = []

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal start_message, start_headers, compressible
            if message["type"] == "http.response.start":
                start_headers = {
                    key.lower(): value for key, value in message.get("headers", [])
                }
                if self._media_allows_encoding(start_headers):
                    message = self._ensure_vary(message, start_headers)
                    start_headers = {
                        key.lower(): value for key, value in message.get("headers", [])
                    }
                start_message = message
                compressible = self._compressible(message, start_headers)
                if not compressible:
                    await send(message)
                return
            if message["type"] == "http.response.body":
                body = message.get("body", b"")
                if not compressible:
                    await send(message)
                    return
                parts.append(body)
                if message.get("more_body", False):
                    return
                payload = b"".join(parts)
                if len(payload) >= _COMPRESSION_FLOOR_BYTES:
                    # Level 4 keeps most of the ratio at a fraction of the latency of the
                    # default level, which matters while the user waits for geometry bytes.
                    encoded = gzip.compress(payload, compresslevel=4)
                    if len(encoded) < len(payload):
                        headers = [
                            (key, value)
                            for key, value in start_headers.items()
                            if key not in (b"content-length", b"content-encoding")
                        ]
                        headers.append((b"content-encoding", b"gzip"))
                        headers.append(
                            (b"content-length", str(len(encoded)).encode("ascii"))
                        )
                        # The ETag stays representation-based: it names the same decoded
                        # bytes for both encodings, so a validator carried across a
                        # negotiated encoding change still matches. Caches separate the
                        # two bodies by Vary.
                        start_message = dict(start_message or {})
                        start_message["headers"] = headers
                        await send(start_message)
                        await send({"type": "http.response.body", "body": encoded})
                        return
                await send(start_message)  # type: ignore[arg-type]
                await send({"type": "http.response.body", "body": payload})
                return
            await send(message)

        await self.app(scope, receive, send_wrapper)


def register_routes(app: FastAPI, service: CADService) -> None:
    jobs = PlanJobRegistry(service)

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        from cadwork import smlib as S

        return {"status": "ok", "version": __version__, "smlibpy": S.VERSION}

    @app.get("/api/domains")
    def domains() -> dict[str, Any]:
        return {"domains": default_registry.list()}

    @app.get("/api/domains/{domain_id}/brief")
    def domain_brief(domain_id: str, version: str | None = None) -> dict[str, Any]:
        pack = default_registry.get(domain_id, version)
        return {
            "id": pack.id,
            "version": pack.version,
            "brief": pack.brief_schema().to_json(),
        }

    @app.get("/gen-tests", response_class=HTMLResponse)
    def gen_tests_page() -> HTMLResponse:
        return HTMLResponse(
            (Path(__file__).with_name("gen_tests.html")).read_text(encoding="utf-8")
        )

    @app.get("/documents", response_class=HTMLResponse)
    def documents_page() -> HTMLResponse:
        return HTMLResponse(
            (Path(__file__).with_name("documents.html")).read_text(encoding="utf-8")
        )

    @app.get("/workbench", response_class=HTMLResponse)
    def workbench_page() -> HTMLResponse:
        return HTMLResponse(
            (Path(__file__).with_name("workbench.html")).read_text(encoding="utf-8")
        )

    @app.get("/gen-tests/gallery", response_class=HTMLResponse)
    def gen_gallery_page() -> HTMLResponse:
        return HTMLResponse(
            (Path(__file__).with_name("gen_gallery.html")).read_text(encoding="utf-8")
        )

    @app.get("/api/gen-tests/renders")
    def gen_renders(run_id: str = "browser-mwdawbfs") -> dict[str, Any]:
        if not run_id.replace("-", "").replace("_", "").isalnum():
            return JSONResponse({"error": "invalid run id"}, status_code=400)
        folder = Path(service.store.root) / "gen-evidence" / run_id
        entries = []
        for key in GEN_KEYS:
            stem = key.replace(".", "_")
            payload_path = folder / f"{stem}.render.json"
            png = folder / "render" / f"{stem}.png"
            payload = {}
            if payload_path.is_file():
                try:
                    payload = json.loads(payload_path.read_text(encoding="utf-8"))
                except Exception:
                    payload = {}
            entries.append(
                {
                    "key": key,
                    "status": payload.get("status", "missing"),
                    "view": payload.get("view"),
                    "ratio": payload.get("ratio"),
                    "seconds": payload.get("seconds"),
                    "png_url": f"/gen-evidence/{run_id}/render/{stem}.png"
                    if png.is_file()
                    else None,
                }
            )
        summary = {}
        summary_path = folder / "renders.json"
        if summary_path.is_file():
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except Exception:
                summary = {}
        return {
            "run_id": run_id,
            "total": len(entries),
            "passed": sum(1 for item in entries if item["status"] == "passed"),
            "render_seconds": summary.get("seconds"),
            "items": entries,
        }

    @app.get("/api/gen-tests/cases")
    def gen_test_cases() -> dict[str, Any]:
        return {"keys": list(GEN_KEYS), "total": len(GEN_KEYS)}

    @app.post("/api/gen-tests/run")
    def gen_test_run(body: GenRunRequest) -> dict[str, Any]:
        if body.key not in CASES:
            return JSONResponse({"error": "unknown GEN case"}, status_code=404)
        run_id = body.run_id or "browser"
        if not run_id.replace("-", "").replace("_", "").isalnum():
            return JSONResponse({"error": "invalid run id"}, status_code=400)
        result = run_case(body.key, Path(service.store.root) / "gen-evidence", run_id)
        artifact = result.get("artifact")
        if artifact:
            result["artifact_url"] = f"/gen-evidence/{run_id}/{Path(artifact).name}"
        return result

    @app.get("/gen-evidence/{run_id}/{filename}")
    def gen_evidence(run_id: str, filename: str) -> Response:
        safe_root = Path(service.store.root) / "gen-evidence" / run_id
        safe_name = Path(filename).name
        path = safe_root / safe_name
        if safe_name != filename or not path.is_file():
            return JSONResponse({"error": "evidence not found"}, status_code=404)
        media = "application/json" if path.suffix == ".json" else "application/step"
        return FileResponse(path, media_type=media, filename=safe_name)

    @app.get("/gen-evidence/{run_id}/render/{filename}")
    def gen_render_evidence(run_id: str, filename: str) -> Response:
        safe_root = Path(service.store.root) / "gen-evidence" / run_id / "render"
        safe_name = Path(filename).name
        path = safe_root / safe_name
        if safe_name != filename or not path.is_file():
            return JSONResponse({"error": "render not found"}, status_code=404)
        return FileResponse(path, media_type="image/png", filename=safe_name)

    @app.get("/api/catalog")
    def catalog() -> list[dict[str, Any]]:
        return service.catalog()

    @app.get("/api/docs")
    def list_documents() -> list[dict[str, Any]]:
        return service.list_documents()

    @app.post("/api/docs")
    def create_document(body: CreateDocument) -> dict[str, Any]:
        document = service.store.create(body.name)
        return service.document_json(document.id)

    @app.get("/api/docs/{document_id}")
    def read_document(document_id: str) -> dict[str, Any]:
        return service.document_json(document_id)

    @app.get("/api/docs/{document_id}/meta")
    def read_document_meta(document_id: str) -> dict[str, Any]:
        return service.document_meta(document_id)

    @app.put("/api/docs/{document_id}")
    def edit_document(document_id: str, body: EditRequest) -> dict[str, Any]:
        return service.commit(
            document_id,
            body.base_version,
            body.ops,
            title=body.title or "编辑特征",
            actor="human",
        )

    @app.delete("/api/docs/{document_id}")
    def delete_document(document_id: str) -> dict[str, Any]:
        service.delete_document(document_id)
        return {"deleted": document_id}

    @app.get("/api/assemblies")
    def list_assemblies() -> list[dict[str, Any]]:
        return [
            entry
            for entry in service.list_documents()
            if entry.get("kind") == "assembly"
        ]

    @app.post("/api/assemblies")
    def create_assembly(body: CreateAssembly) -> dict[str, Any]:
        assembly = service.create_assembly(body.name)
        return service.assembly_state(assembly.id)

    @app.get("/api/assemblies/{assembly_id}")
    def read_assembly(assembly_id: str, version: int | None = None) -> dict[str, Any]:
        return service.assembly_state(assembly_id, version)

    @app.put("/api/assemblies/{assembly_id}")
    def edit_assembly(assembly_id: str, body: AssemblyEditRequest) -> dict[str, Any]:
        return service.edit_assembly(assembly_id, body.base_version, body.ops)

    @app.delete("/api/assemblies/{assembly_id}")
    def delete_assembly(assembly_id: str) -> dict[str, Any]:
        service.delete_document(assembly_id)
        return {"deleted": assembly_id}

    @app.get("/api/assemblies/{assembly_id}/scene")
    def assembly_scene(assembly_id: str, version: int | None = None) -> dict[str, Any]:
        return service.assembly_scene(assembly_id, version)

    @app.get("/api/assemblies/{assembly_id}/bom")
    def assembly_bom(assembly_id: str, version: int | None = None) -> dict[str, Any]:
        return service.assembly_bom(assembly_id, version)

    @app.get("/api/assemblies/{assembly_id}/export")
    def export_assembly(assembly_id: str, format: str = "step") -> Response:
        raw, media, _ = service.assembly_export(assembly_id, format)
        return Response(
            content=raw,
            media_type=media,
            headers={
                "Content-Disposition": f'attachment; filename="{assembly_id}.step"'
            },
        )

    @app.get("/api/assemblies/{assembly_id}/preview")
    def assembly_preview(
        assembly_id: str, version: int | None = None
    ) -> Response:
        result = service.assembly_preview(assembly_id, version)
        headers = {"Cache-Control": "no-cache"}
        if result["state"] == "ready":
            headers.update(
                {
                    "X-Preview-Key": result["previewKey"],
                    "X-Bundle-Key": result["bundleKey"],
                }
            )
            return Response(
                content=result["bundle"],
                media_type=PREVIEW_MEDIA_TYPE,
                headers=headers,
            )
        return JSONResponse(
            {
                "state": "building",
                "previewKey": result["previewKey"],
                "buildId": result["buildId"],
                "progress": result["progress"],
            },
            status_code=202,
            headers=headers,
        )

    @app.get("/api/preview/{bundle_key}.bpx")
    def preview_bundle(bundle_key: str) -> Response:
        if not service.assembly_preview_enabled():
            raise ServiceError(
                "PREVIEW_DISABLED",
                "assembly preview is disabled for this deployment",
                status=503,
            )
        if not is_preview_key(bundle_key):
            return JSONResponse(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "no preview asset",
                    }
                },
                status_code=404,
            )
        bundle = service.preview_asset(bundle_key)
        if bundle is None:
            return JSONResponse(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "no preview asset",
                    }
                },
                status_code=404,
            )
        return Response(
            content=bundle,
            media_type=PREVIEW_MEDIA_TYPE,
            headers={
                "ETag": f'"{bundle_key}"',
                "Cache-Control": "public, max-age=31536000, immutable",
            },
        )

    @app.post("/api/preview/builds/{build_id}/cancel")
    def cancel_preview_build(build_id: str) -> dict[str, Any]:
        return service.cancel_preview_build(build_id)

    @app.get("/api/assemblies/{assembly_id}/references")
    def assembly_references(assembly_id: str) -> dict[str, Any]:
        return service.assembly_references(assembly_id)

    @app.post("/api/assemblies/{assembly_id}/update-references")
    def update_assembly_references(
        assembly_id: str, body: AssemblyReferencesRequest
    ) -> dict[str, Any]:
        return service.update_assembly_references(
            assembly_id, body.base_version, body.instance_ids
        )

    @app.post("/api/docs/{document_id}/preview")
    def preview(document_id: str, body: PreviewRequest) -> dict[str, Any]:
        return service.preview(document_id, body.ops, body.base_version)

    @app.post("/api/docs/{document_id}/undo")
    def undo(document_id: str) -> dict[str, Any]:
        return service.undo(document_id)

    @app.post("/api/docs/{document_id}/sample/impeller")
    def sample_impeller(document_id: str, count: int = 9) -> dict[str, Any]:
        document = service.read(document_id)
        sample = impeller_document(count=count)
        ops = [
            {"op": "remove", "id": feature.id}
            for feature in reversed(document.features)
        ]
        ops += [
            {"op": "add", "feature": feature_to_json(feature)}
            for feature in sample.features
        ]
        return service.commit(
            document_id, document.version, ops, title="载入叶轮", actor="human"
        )

    @app.get("/api/samples")
    def samples() -> list[dict[str, Any]]:
        return sample_catalog()

    @app.post("/api/docs/{document_id}/sample/{name}")
    def load_sample(
        document_id: str, name: str, body: SampleRequest | None = None
    ) -> dict[str, Any]:
        document = service.read(document_id)
        request = body or SampleRequest()
        try:
            sample = build_sample(name, request.params)
        except KeyError as exc:
            raise ServiceError(
                "NOT_FOUND",
                f"no sample {name!r}",
                status=404,
                hint="read /api/samples for the available ones",
            ) from exc
        except ValueError as exc:
            raise ServiceError("INVALID_PARAM", str(exc), status=400) from exc
        ops: list[dict[str, Any]] = []
        if request.replace:
            ops.extend(
                {"op": "remove", "id": feature.id}
                for feature in reversed(document.features)
            )
        ops.extend(
            {"op": "add", "feature": feature_to_json(feature)}
            for feature in sample.features
        )
        return service.commit(
            document_id,
            document.version,
            ops,
            title=SAMPLE_TITLES.get(name, sample.name),
            actor="human",
            name=SAMPLE_TITLES.get(name, sample.name),
        )

    @app.get("/api/docs/{document_id}/state")
    def state(document_id: str) -> dict[str, Any]:
        return service.state(document_id)

    @app.get("/api/docs/{document_id}/events")
    async def events(document_id: str, request: Request) -> Response:
        service.read(document_id)
        channel = service.bus.subscribe(document_id)

        async def stream():
            try:
                yield _sse("state", service.state(document_id))
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event, payload = await asyncio.to_thread(
                            channel.get, True, 20.0
                        )
                    except queue.Empty:
                        yield ": heartbeat\n\n"
                        continue
                    yield _sse(event, payload)
            finally:
                service.bus.unsubscribe(document_id, channel)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/docs/{document_id}/step")
    def step(
        document_id: str, request: Request, version: int | None = None
    ) -> Response:
        document, digest = service.step_identity(document_id, version=version)
        etag = f'"{digest}"'
        headers = {"ETag": etag, "Cache-Control": "no-cache"}
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=headers)
        payload = service.step_bytes(
            document_id, version=version, document=document, digest=digest
        )
        return Response(
            content=payload, media_type="application/octet-stream", headers=headers
        )

    @app.get("/api/docs/{document_id}/diff")
    def diff(document_id: str, base: int, target: int | None = None) -> dict[str, Any]:
        return service.compare_versions(document_id, base, target)

    @app.post("/api/docs/{document_id}/pick")
    def pick(document_id: str, body: PickRequest) -> dict[str, Any]:
        return service.pick(document_id, body.model_dump())

    @app.get("/api/docs/{document_id}/dimensions")
    def dimensions(document_id: str, feature_id: str) -> dict[str, Any]:
        return service.dimensions(document_id, feature_id)

    @app.post("/api/docs/{document_id}/handles")
    def handles(document_id: str, body: HandleRequest) -> dict[str, Any]:
        return service.handles(
            document_id, body.feature_id, body.point, body.normal, scope=body.scope
        )

    @app.post("/api/docs/{document_id}/tweak")
    def tweak(document_id: str, body: TweakRequest) -> dict[str, Any]:
        changes = [item.model_dump() for item in body.changes]
        return service.tweak(document_id, changes, body.base_version, body.title)

    @app.post("/api/docs/{document_id}/toggle/{feature_id}")
    def toggle(document_id: str, feature_id: str) -> dict[str, Any]:
        return service.toggle(document_id, feature_id)

    @app.post("/api/docs/{document_id}/revert")
    def revert(document_id: str, body: RevertRequest) -> dict[str, Any]:
        return service.revert(document_id, body.target_version, body.title)

    @app.post("/api/docs/{document_id}/intents")
    def add_intent(document_id: str, body: IntentRequest) -> dict[str, Any]:
        return service.add_intent_note(
            document_id, body.text, base_version=body.base_version
        )

    @app.get("/api/docs/{document_id}/intents")
    def list_intents(document_id: str) -> dict[str, Any]:
        return service.list_intents(document_id)

    @app.delete("/api/docs/{document_id}/intents")
    def clear_intents(document_id: str) -> dict[str, Any]:
        return service.clear_intents(document_id)

    @app.post("/api/docs/{document_id}/intents/{intent_id}/cancel")
    def cancel_intent(document_id: str, intent_id: str) -> dict[str, Any]:
        return service.cancel_intent(document_id, intent_id)

    @app.get("/api/docs/{document_id}/plan")
    def get_plan(document_id: str) -> dict[str, Any]:
        return service.plan(document_id)

    @app.post("/api/docs/{document_id}/plan/edit")
    def edit_plan(document_id: str, body: PlanEditRequest) -> dict[str, Any]:
        return service.plan_edit(
            document_id, body.ops, base_revision=body.base_revision, goal=body.goal
        )

    @app.post("/api/docs/{document_id}/plan/compile")
    def compile_plan(document_id: str) -> dict[str, Any]:
        return service.plan_compile(document_id)

    @app.post("/api/docs/{document_id}/plan/run")
    def run_plan(document_id: str, body: PlanRunRequest) -> dict[str, Any]:
        return service.plan_run(
            document_id,
            body.node_id,
            base_version=body.base_version,
            executor=body.executor,
        )

    @app.post("/api/docs/{document_id}/plan/run_async")
    def run_plan_async(document_id: str, body: PlanRunRequest) -> dict[str, Any]:
        job = jobs.start(
            document_id,
            body.node_id,
            base_version=body.base_version,
            executor=body.executor,
        )
        return job.to_json()

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, Any]:
        job = jobs.get(job_id)
        if job is None:
            return JSONResponse({"error": "job not found"}, status_code=404)
        return job.to_json()

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str) -> dict[str, Any]:
        job = jobs.cancel(job_id)
        if job is None:
            return JSONResponse({"error": "job not found"}, status_code=404)
        return job.to_json()

    @app.get("/api/docs/{document_id}/timeline")
    def timeline(document_id: str) -> list[dict[str, Any]]:
        return service.timeline(document_id)

    @app.post("/api/docs/{document_id}/import")
    def import_file(document_id: str, body: ImportRequest) -> dict[str, Any]:
        return service.import_file(document_id, body.path, format=body.format)

    @app.post("/api/docs/{document_id}/import/file")
    def import_upload(document_id: str, body: ImportUpload) -> dict[str, Any]:
        raw = str(body.data or "").strip()
        if raw.startswith("data:") and "," in raw:
            raw = raw.split(",", 1)[1]
        if not raw:
            raise ServiceError("IMPORT_EMPTY", "the imported file is empty", status=400)
        if len(raw) > 70_000_000:
            raise ServiceError(
                "IMPORT_TOO_LARGE", "import larger than 50 MB", status=413
            )
        try:
            payload = base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ServiceError(
                "IMPORT_DATA", "file data is not valid base64", status=400
            ) from exc
        if len(payload) > 50_000_000:
            raise ServiceError(
                "IMPORT_TOO_LARGE", "import larger than 50 MB", status=413
            )
        suffix = Path(body.filename or "").suffix.lower().lstrip(".")
        formats = {
            "step": "step",
            "stp": "step",
            "iges": "iges",
            "igs": "iges",
            "brep": "brep",
            "stl": "stl",
        }
        requested = (body.format or suffix or "step").lower()
        format = formats.get(requested)
        if format is None or (suffix and suffix not in formats):
            shown = Path(body.filename or "").suffix or requested
            raise ServiceError(
                "IMPORT_FORMAT",
                f"unsupported reference format {shown!r}",
                status=400,
                hint="支持 STEP / IGES / BREP / STL",
            )
        return service.import_bytes(
            document_id, Path(body.filename or "reference").name, payload, format=format
        )

    @app.post("/api/docs/{document_id}/variants")
    def create_variants(document_id: str, body: VariantRequest) -> dict[str, Any]:
        return service.create_variants(
            document_id,
            variants=[item.model_dump() for item in body.variants]
            if body.variants
            else None,
            feature=body.feature,
            params=body.params,
            include_base=body.include_base,
            base_version=body.base_version,
            thumbs=body.thumbs,
        )

    @app.get("/api/variants/{set_id}")
    def variant_set(set_id: str) -> dict[str, Any]:
        return service.variant_set(set_id)

    @app.get("/api/variants/{set_id}/{index}/thumb.png")
    def variant_thumbnail(set_id: str, index: int) -> Response:
        return FileResponse(
            service.variant_thumbnail(set_id, index), media_type="image/png"
        )

    @app.get("/api/variants/{set_id}/sheet.png")
    def variant_sheet(set_id: str) -> Response:
        return Response(content=service.variant_sheet(set_id), media_type="image/png")

    @app.get("/api/variants/{set_id}/{index}/step")
    def variant_step(set_id: str, index: int) -> Response:
        return FileResponse(
            service.variant_step_file(set_id, index),
            media_type="application/octet-stream",
        )

    @app.post("/api/variants/{set_id}/{index}/apply")
    def apply_variant(set_id: str, index: int) -> dict[str, Any]:
        return service.apply_variant(set_id, index)

    @app.get("/api/docs/{document_id}/checks")
    def checks(document_id: str) -> dict[str, Any]:
        return service.checks(document_id)

    @app.get("/api/docs/{document_id}/summary")
    def summary(document_id: str) -> dict[str, Any]:
        return service.summary(document_id)

    @app.get("/api/docs/{document_id}/resolve")
    def resolve(document_id: str, q: str, anchor: str | None = None) -> dict[str, Any]:
        return service.resolve_reference(document_id, q, anchor)

    @app.get("/api/docs/{document_id}/scene")
    def scene(
        document_id: str,
        request: Request,
        feature: str | None = None,
        version: int | None = None,
        cached: int = 0,
        edges: int = 1,
    ) -> Response:
        with_edges = bool(edges)
        if cached:
            entry = service.cached_scene_bytes(
                document_id, version=version, edges=with_edges
            )
            if entry is None:
                return JSONResponse(
                    {
                        "error": {
                            "code": "SCENE_NOT_CACHED",
                            "message": "scene is not cached",
                        }
                    },
                    status_code=404,
                )
            raw, etag = entry
            headers = {
                "ETag": etag,
                "Cache-Control": "no-cache",
                "Vary": "Accept-Encoding",
            }
            if request.headers.get("if-none-match") == etag:
                return Response(status_code=304, headers=headers)
            return Response(content=raw, media_type="application/json", headers=headers)
        payload = service.scene(
            document_id, feature=feature, version=version, edges=with_edges
        )
        etag = f'"{payload["version"]}:{payload["feature"]}:{1 if with_edges else 0}"'
        headers = {"ETag": etag, "Cache-Control": "no-cache", "Vary": "Accept-Encoding"}
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=headers)
        return JSONResponse(payload, headers=headers)

    @app.get("/api/docs/{document_id}/render.png")
    def render(
        document_id: str, feature: str | None = None, view: str = "iso"
    ) -> Response:
        payload = service.render(document_id, feature=feature, view=view)
        return Response(content=payload, media_type="image/png")

    @app.get("/api/docs/{document_id}/export/{fmt}")
    def export(
        document_id: str,
        fmt: str,
        feature: str | None = None,
        version: int | None = None,
    ) -> Response:
        payload, media_type = service.export(document_id, fmt, feature, version=version)
        suffix = "json" if fmt == "cfd" else fmt
        return Response(
            content=payload,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{document_id}.{suffix}"'
            },
        )


def create_app(store_root: str | os.PathLike[str] | None = None) -> FastAPI:
    root = (
        store_root or os.environ.get("CADWORK_HOME") or str(Path.cwd() / "cadwork-data")
    )
    service = CADService(Store(root))

    mcp_server = build_mcp_server(service)
    mcp_app = mcp_server.streamable_http_app(
        streamable_http_path="/", json_response=True
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        async with mcp_server.session_manager.run():
            yield

    app = FastAPI(title="cadwork", version=__version__, lifespan=lifespan)
    app.state.service = service

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Preview-Key", "X-Bundle-Key"],
    )

    @app.middleware("http")
    async def web_asset_headers(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if (
            path == "/"
            or path.startswith("/web")
            or path.startswith("/api/plugin")
            or path == "/api/kernel-view"
        ):
            response.headers["Cache-Control"] = "no-cache"
        elif response.status_code in (200, 304) and (
            path.startswith("/pkg/") or path == "/api/kernel/smlibwasm.wasm"
        ):
            # Asset names carry no content hash, so they must stay revalidatable: a bounded
            # freshness window avoids a conditional request per file on every load without
            # pinning a stale file forever.
            response.headers["Cache-Control"] = "public, max-age=86400"
        return response

    app.add_middleware(TextCompressionMiddleware)

    for error_type in (ServiceError, DomainError, StoreError, DocumentError, BuildError):
        app.add_exception_handler(error_type, lambda request, exc: _error(exc))

    register_routes(app, service)
    app.mount("/mcp", mcp_app)

    kernel_wasm = (
        Path(__file__).resolve().parents[2]
        / "plugins"
        / "cadview"
        / "node_modules"
        / "@classcad"
        / "smlibwasm"
        / "wasm"
        / "smlibwasm.wasm"
    )

    @app.get("/api/kernel/smlibwasm.wasm", include_in_schema=False)
    def wasm(request: Request) -> Response:
        if not kernel_wasm.is_file():
            return JSONResponse(
                {
                    "error": {
                        "code": "KERNEL_MISSING",
                        "message": f"kernel not installed at {kernel_wasm}",
                        "hint": "npm install in plugins/cadview",
                    }
                },
                status_code=404,
            )
        stat_result = kernel_wasm.stat()
        # FileResponse sends validators but does not evaluate If-None-Match, so a warm
        # browser would re-download 9.4 MB instead of revalidating; answer it here with the
        # same ETag formula FileResponse would use.
        etag_base = f"{stat_result.st_mtime}-{stat_result.st_size}"
        etag = (
            '"'
            + hashlib.md5(etag_base.encode(), usedforsecurity=False).hexdigest()
            + '"'
        )
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag})
        return FileResponse(
            kernel_wasm,
            media_type="application/wasm",
            headers={"ETag": etag},
            stat_result=stat_result,
        )

    @app.get("/api/probe", include_in_schema=False)
    def probe() -> HTMLResponse:
        page = """<!doctype html><meta charset="utf-8">
<body style="margin:0;padding:16px;background:#0f1115;color:#c9d6ea;font:13px/1.6 monospace">
<pre id="out">probing…</pre>
<script type="importmap">
{"imports": {
  "three": "/pkg/three/build/three.module.js",
  "three/addons/": "/pkg/three/examples/jsm/",
  "@classcad/smlibwasm": "/pkg/@classcad/smlibwasm/dist/index.js",
  "@classcad/smlibwasm/init": "/pkg/@classcad/smlibwasm/dist/init.js",
  "@classcad/smlibpy-three": "/pkg/@classcad/smlibpy-three/dist/index.js",
  "@classcad/smlibpy-three/init": "/pkg/@classcad/smlibpy-three/dist/init.js"
}}
</script>
<script type="module">
const out = document.getElementById('out')
const log = (m) => { out.textContent += m + '\\n' }
const now = () => Math.round(performance.now())
const race = (promise, ms, label) => Promise.race([
  promise,
  new Promise((_, reject) => setTimeout(() => reject(new Error(label + ' pending after ' + ms + ' ms')), ms)),
])
try {
  const r = await fetch('/api/kernel/smlibwasm.wasm')
  const bytes = await r.arrayBuffer()
  log(`fetch ${bytes.byteLength} bytes`)
  const t0 = now()
  try {
    await import('/api/plugin/probe-kernel.mjs')
    const got = await race(window.__kernelProbe(bytes), 5000, 'bundled init')
    log(`bundled   ok  ${got.milliseconds} ms, ${got.exports} exports (wall ${now() - t0})`)
  } catch (e) {
    log(`bundled   FAIL ${e.message}`)
  }
  const t1 = now()
  try {
    const mod = await race(import('@classcad/smlibpy-three/init'), 6000, 'import of init')
    const kernel = await race(mod.init({ wasmBinary: bytes }), 14000, 'unbundled init')
    log(`unbundled ok  ${now() - t1} ms, ${Object.keys(kernel).length} exports`)
  } catch (e) {
    log(`unbundled FAIL ${e.message}`)
  }
} catch (e) {
  log('ERROR ' + e.message)
}
log('done')
</script>"""
        return HTMLResponse(page)

    kernel_view = Path(__file__).with_name("kernel_view.html")

    @app.get("/api/kernel-view", include_in_schema=False)
    def kernel_view_page() -> Response:
        if not kernel_view.is_file():
            return JSONResponse(
                {
                    "error": {
                        "code": "VIEW_MISSING",
                        "message": f"missing {kernel_view}",
                    }
                },
                status_code=404,
            )
        return FileResponse(kernel_view, media_type="text/html")

    node_modules = (
        Path(__file__).resolve().parents[2] / "plugins" / "cadview" / "node_modules"
    )
    if node_modules.is_dir():
        app.mount("/pkg", StaticFiles(directory=str(node_modules)), name="pkg")

    workbench_module = (
        Path(__file__).resolve().parents[2]
        / "plugins"
        / "cadview"
        / "lib"
        / "workbench.mjs"
    )

    @app.get("/api/plugin/workbench.mjs", include_in_schema=False)
    def workbench() -> Response:
        if not workbench_module.is_file():
            return JSONResponse(
                {
                    "error": {
                        "code": "PLUGIN_MISSING",
                        "message": f"workbench bundle not built at {workbench_module}",
                        "hint": "npm run build in plugins/cadview",
                    }
                },
                status_code=404,
            )
        return FileResponse(workbench_module, media_type="text/javascript")

    probe_kernel = (
        Path(__file__).resolve().parents[2]
        / "plugins"
        / "cadview"
        / "lib"
        / "probe-kernel.mjs"
    )

    @app.get("/api/plugin/probe-kernel.mjs", include_in_schema=False)
    def probe_kernel_module() -> Response:
        if not probe_kernel.is_file():
            return JSONResponse(
                {
                    "error": {
                        "code": "PROBE_MISSING",
                        "message": f"probe bundle not built at {probe_kernel}",
                        "hint": "build plugins/cadview/src/probe-kernel.js",
                    }
                },
                status_code=404,
            )
        return FileResponse(probe_kernel, media_type="text/javascript")

    return app
