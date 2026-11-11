"""HTTP and MCP surface over one process: browser canvas, agent tools."""

from __future__ import annotations

import asyncio
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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cadwork import __version__
from cadwork.design.build import BuildError
from cadwork.design.document import DocumentError, feature_to_json
from cadwork.samples.impeller import impeller_document
from cadwork.samples.registry import SAMPLES
from cadwork.samples.registry import build as build_sample
from cadwork.samples.registry import catalog as sample_catalog

SAMPLE_TITLES = {name: spec.title for name, spec in SAMPLES.items()}

from .mcp import build_mcp_server
from .service import CADService, ServiceError
from .store import Store, StoreError


class CreateDocument(BaseModel):
    name: str = "Untitled"


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
    if isinstance(exc, StoreError):
        return JSONResponse(
            {"error": {"code": exc.code, "message": exc.message}}, status_code=exc.status,
        )
    if isinstance(exc, DocumentError):
        status = 409 if exc.code == "STALE_VERSION" else 400
        return JSONResponse(
            {"error": {"code": exc.code, "message": exc.message, "hint": exc.hint}},
            status_code=status,
        )
    if isinstance(exc, BuildError):
        return JSONResponse({"error": exc.to_json()}, status_code=422)
    return JSONResponse({"error": {"code": "INTERNAL", "message": str(exc)}}, status_code=500)


def _sse(event: str, payload: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def register_routes(app: FastAPI, service: CADService) -> None:
    @app.get("/api/health")
    def health() -> dict[str, Any]:
        from cadwork import smlib as S

        return {"status": "ok", "version": __version__, "smlibpy": S.VERSION}

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

    @app.put("/api/docs/{document_id}")
    def edit_document(document_id: str, body: EditRequest) -> dict[str, Any]:
        return service.commit(document_id, body.base_version, body.ops,
                              title=body.title or "编辑特征", actor="human")

    @app.delete("/api/docs/{document_id}")
    def delete_document(document_id: str) -> dict[str, Any]:
        service.delete_document(document_id)
        return {"deleted": document_id}

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
        ops = [{"op": "remove", "id": feature.id}
               for feature in reversed(document.features)]
        ops += [{"op": "add", "feature": feature_to_json(feature)} for feature in sample.features]
        return service.commit(document_id, document.version, ops, title="载入叶轮", actor="human")

    @app.get("/api/samples")
    def samples() -> list[dict[str, Any]]:
        return sample_catalog()

    @app.post("/api/docs/{document_id}/sample/{name}")
    def load_sample(document_id: str, name: str,
                    body: SampleRequest | None = None) -> dict[str, Any]:
        document = service.read(document_id)
        request = body or SampleRequest()
        try:
            sample = build_sample(name, request.params)
        except KeyError as exc:
            raise ServiceError("NOT_FOUND", f"no sample {name!r}", status=404,
                               hint="read /api/samples for the available ones") from exc
        except ValueError as exc:
            raise ServiceError("INVALID_PARAM", str(exc), status=400) from exc
        ops: list[dict[str, Any]] = []
        if request.replace:
            ops.extend({"op": "remove", "id": feature.id}
                       for feature in reversed(document.features))
        ops.extend({"op": "add", "feature": feature_to_json(feature)}
                   for feature in sample.features)
        return service.commit(
            document_id,
            document.version,
            ops,
            title=SAMPLE_TITLES.get(name, sample.name),
            actor="human",
            name=SAMPLE_TITLES.get(name, sample.name),
        )

    # ------------------------------------------------------------ review loop
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
                        event, payload = await asyncio.to_thread(channel.get, True, 20.0)
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
    def step(document_id: str, request: Request, version: int | None = None) -> Response:
        payload = service.step_bytes(document_id, version=version)
        etag = '"' + hashlib.sha1(payload).hexdigest() + '"'
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "no-cache"})
        return Response(content=payload, media_type="application/octet-stream",
                        headers={"ETag": etag, "Cache-Control": "no-cache"})

    @app.get("/api/docs/{document_id}/diff")
    def diff(document_id: str, base: int, target: int | None = None) -> dict[str, Any]:
        return service.compare_versions(document_id, base, target)

    @app.post("/api/docs/{document_id}/pick")
    def pick(document_id: str, body: PickRequest) -> dict[str, Any]:
        return service.pick(document_id, body.model_dump())

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

    # ------------------------------------------------------------ intents
    @app.post("/api/docs/{document_id}/intents")
    def add_intent(document_id: str, body: IntentRequest) -> dict[str, Any]:
        return service.add_intent_note(document_id, body.text, base_version=body.base_version)

    @app.get("/api/docs/{document_id}/intents")
    def list_intents(document_id: str) -> dict[str, Any]:
        return service.list_intents(document_id)

    @app.delete("/api/docs/{document_id}/intents")
    def clear_intents(document_id: str) -> dict[str, Any]:
        return service.clear_intents(document_id)

    @app.post("/api/docs/{document_id}/intents/{intent_id}/cancel")
    def cancel_intent(document_id: str, intent_id: str) -> dict[str, Any]:
        return service.cancel_intent(document_id, intent_id)

    # ------------------------------------------------------------ variants
    @app.post("/api/docs/{document_id}/variants")
    def create_variants(document_id: str, body: VariantRequest) -> dict[str, Any]:
        return service.create_variants(
            document_id,
            variants=[item.model_dump() for item in body.variants] if body.variants else None,
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
        return FileResponse(service.variant_thumbnail(set_id, index), media_type="image/png")

    @app.get("/api/variants/{set_id}/sheet.png")
    def variant_sheet(set_id: str) -> Response:
        return Response(content=service.variant_sheet(set_id), media_type="image/png")

    @app.get("/api/variants/{set_id}/{index}/step")
    def variant_step(set_id: str, index: int) -> Response:
        return FileResponse(service.variant_step_file(set_id, index),
                            media_type="application/octet-stream")

    @app.post("/api/variants/{set_id}/{index}/apply")
    def apply_variant(set_id: str, index: int) -> dict[str, Any]:
        return service.apply_variant(set_id, index)

    # ------------------------------------------------------------ derived
    @app.get("/api/docs/{document_id}/checks")
    def checks(document_id: str) -> dict[str, Any]:
        return service.checks(document_id)

    @app.get("/api/docs/{document_id}/summary")
    def summary(document_id: str) -> dict[str, Any]:
        return service.summary(document_id)

    @app.get("/api/docs/{document_id}/resolve")
    def resolve(document_id: str, q: str) -> dict[str, Any]:
        return service.resolve_reference(document_id, q)

    @app.get("/api/docs/{document_id}/scene")
    def scene(document_id: str, request: Request,
              feature: str | None = None) -> Response:
        payload = service.scene(document_id, feature=feature)
        etag = f'"{payload["version"]}:{payload["feature"]}"'
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag})
        return JSONResponse(payload, headers={"ETag": etag})

    @app.get("/api/docs/{document_id}/render.png")
    def render(document_id: str, feature: str | None = None, view: str = "iso") -> Response:
        payload = service.render(document_id, feature=feature, view=view)
        return Response(content=payload, media_type="image/png")

    @app.get("/api/docs/{document_id}/export/{fmt}")
    def export(document_id: str, fmt: str, feature: str | None = None,
               version: int | None = None) -> Response:
        payload, media_type = service.export(document_id, fmt, feature, version=version)
        suffix = "json" if fmt == "cfd" else fmt
        return Response(
            content=payload,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{document_id}.{suffix}"'},
        )


def create_app(store_root: str | os.PathLike[str] | None = None) -> FastAPI:
    root = store_root or os.environ.get("CADWORK_HOME") or str(Path.cwd() / "cadwork-data")
    service = CADService(Store(root))

    mcp_server = build_mcp_server(service)
    mcp_app = mcp_server.streamable_http_app(streamable_http_path="/", json_response=True)

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
    )

    @app.middleware("http")
    async def revalidate_web_assets(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path == "/" or path.startswith("/web") or path.startswith("/api/plugin") \
                or path == "/api/kernel-view":
            response.headers["Cache-Control"] = "no-cache"
        return response

    for error_type in (ServiceError, StoreError, DocumentError, BuildError):
        app.add_exception_handler(error_type, lambda request, exc: _error(exc))

    register_routes(app, service)
    app.mount("/mcp", mcp_app)

    kernel_wasm = (
        Path(__file__).resolve().parents[2]
        / "plugins" / "cadview" / "node_modules"
        / "@classcad" / "smlibwasm" / "wasm" / "smlibwasm.wasm"
    )

    @app.get("/api/kernel/smlibwasm.wasm", include_in_schema=False)
    def wasm() -> Response:
        if not kernel_wasm.is_file():
            return JSONResponse(
                {"error": {"code": "KERNEL_MISSING",
                           "message": f"kernel not installed at {kernel_wasm}",
                           "hint": "npm install in plugins/cadview"}},
                status_code=404,
            )
        return FileResponse(kernel_wasm, media_type="application/wasm")

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
                {"error": {"code": "VIEW_MISSING", "message": f"missing {kernel_view}"}},
                status_code=404,
            )
        return FileResponse(kernel_view, media_type="text/html")

    node_modules = Path(__file__).resolve().parents[2] / "plugins" / "cadview" / "node_modules"
    if node_modules.is_dir():
        app.mount("/pkg", StaticFiles(directory=str(node_modules)), name="pkg")

    viewport_module = (
        Path(__file__).resolve().parents[2] / "plugins" / "cadview" / "lib" / "viewport.mjs"
    )

    @app.get("/api/plugin/viewport.mjs", include_in_schema=False)
    def viewport() -> Response:
        if not viewport_module.is_file():
            return JSONResponse(
                {"error": {"code": "PLUGIN_MISSING",
                           "message": f"viewport bundle not built at {viewport_module}",
                           "hint": "npm run build in plugins/cadview"}},
                status_code=404,
            )
        return FileResponse(viewport_module, media_type="text/javascript")

    probe_kernel = (
        Path(__file__).resolve().parents[2] / "plugins" / "cadview" / "lib" / "probe-kernel.mjs"
    )

    @app.get("/api/plugin/probe-kernel.mjs", include_in_schema=False)
    def probe_kernel_module() -> Response:
        if not probe_kernel.is_file():
            return JSONResponse(
                {"error": {"code": "PROBE_MISSING",
                           "message": f"probe bundle not built at {probe_kernel}",
                           "hint": "build plugins/cadview/src/probe-kernel.js"}},
                status_code=404,
            )
        return FileResponse(probe_kernel, media_type="text/javascript")

    return app
