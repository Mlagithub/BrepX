"""FastAPI app: /api for the workbench, /mcp for the agent, one process."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cadwork import __version__
from cadwork.design.build import BuildError
from cadwork.design.document import DocumentError, feature_to_json
from cadwork.samples.impeller import impeller_document

from .mcp import build_mcp_server
from .service import CADService, ServiceError
from .store import Store, StoreError


class CreateDocument(BaseModel):
    name: str = "Untitled"


class EditRequest(BaseModel):
    base_version: int
    ops: list[dict[str, Any]]


class PreviewRequest(BaseModel):
    ops: list[dict[str, Any]]


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
    return JSONResponse(
        {"error": {"code": "INTERNAL", "message": str(exc)}}, status_code=500,
    )


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
        return service.apply(document_id, body.base_version, body.ops)

    @app.post("/api/docs/{document_id}/preview")
    def preview(document_id: str, body: PreviewRequest) -> dict[str, Any]:
        return service.preview(document_id, body.ops)

    @app.post("/api/docs/{document_id}/undo")
    def undo(document_id: str) -> dict[str, Any]:
        return service.undo(document_id)

    @app.post("/api/docs/{document_id}/sample/impeller")
    def sample_impeller(document_id: str, count: int = 9) -> dict[str, Any]:
        document = service.read(document_id)
        ops = [
            {"op": "add", "feature": feature_to_json(feature)}
            for feature in impeller_document(count=count).features
        ]
        return service.apply(document_id, document.version, ops)

    @app.get("/api/docs/{document_id}/checks")
    def checks(document_id: str) -> dict[str, Any]:
        return service.checks(document_id)

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
    def export(document_id: str, fmt: str, feature: str | None = None) -> Response:
        payload, media_type = service.export(document_id, fmt, feature)
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

    @app.middleware("http")
    async def revalidate_web_assets(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path == "/" or path.startswith("/web"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    for error_type in (ServiceError, StoreError, DocumentError, BuildError):
        app.add_exception_handler(error_type, lambda request, exc: _error(exc))

    register_routes(app, service)
    app.mount("/mcp", mcp_app)

    web_dir = Path(__file__).resolve().parents[2] / "web"
    if web_dir.is_dir():
        app.mount("/web", StaticFiles(directory=str(web_dir)), name="web")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(web_dir / "index.html")

    return app
