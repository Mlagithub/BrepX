"""CAD service: the single business layer behind HTTP, MCP and tests."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from cadwork.design.build import BuildCache, BuildError, build
from cadwork.design.document import (
    Document,
    DocumentError,
    apply_ops,
    document_to_json,
    feature_to_json,
)
from cadwork.design.features import catalog

from .export import export_bytes
from .resolve import resolve as resolve_phrase
from .resolve import summarize as summarize_document
from .scene import build_scene, display_feature
from .store import Store, StoreError
from .variants import VariantBook


class ServiceError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, hint: str | None = None,
                 detail: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.hint = hint
        self.detail = dict(detail or {})

    def to_json(self) -> dict[str, Any]:
        payload = {"code": self.code, "message": self.message}
        if self.hint:
            payload["hint"] = self.hint
        payload.update(self.detail)
        return payload


@dataclass
class SceneCacheEntry:
    key: str
    payload: dict[str, Any]


class CADService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.cache = BuildCache()
        self._scene_cache: dict[str, SceneCacheEntry] = {}
        self.variants = VariantBook(self._build, self._variant_preview, self._variant_step)

    @staticmethod
    def _variant_preview(part: Any) -> bytes:
        from .render import render_png

        return render_png(part, view="iso")

    @staticmethod
    def _variant_step(part: Any) -> bytes:
        return export_bytes(part, "step")[0]

    # ------------------------------------------------------------ reads
    def list_documents(self) -> list[dict[str, Any]]:
        return self.store.list()

    def read(self, document_id: str) -> Document:
        try:
            return self.store.get(document_id)
        except StoreError as exc:
            raise ServiceError(exc.code, exc.message, status=exc.status) from exc

    def document_json(self, document_id: str) -> dict[str, Any]:
        document = self.read(document_id)
        result = self._build(document)
        payload = document_to_json(document)
        payload["build"] = result.summary()
        return payload

    def catalog(self) -> list[dict[str, Any]]:
        return catalog()

    # ------------------------------------------------------------ writes
    def delete_document(self, document_id: str) -> None:
        try:
            self.store.delete(document_id)
        except StoreError as exc:
            raise ServiceError(exc.code, exc.message, status=exc.status) from exc

    def apply(self, document_id: str, base_version: int | None,
              ops: list[Mapping[str, Any]], name: str | None = None) -> dict[str, Any]:
        document = self.read(document_id)
        try:
            updated = apply_ops(document, ops, base_version, name)
        except DocumentError as exc:
            raise _document_error(exc) from exc
        result = self._build(updated)
        self.store.save(updated)
        return {
            "document": document_to_json(updated),
            "build": result.summary(),
            "tags": result.tags,
        }

    def preview(self, document_id: str, ops: list[Mapping[str, Any]]) -> dict[str, Any]:
        document = self.read(document_id)
        try:
            candidate = apply_ops(document, list(ops))
        except DocumentError as exc:
            raise _document_error(exc) from exc
        try:
            result = build(candidate, self.cache)
        except BuildError as exc:
            raise ServiceError(
                exc.code, exc.message, status=422, hint=exc.hint,
                detail={"feature_id": exc.feature_id,
                        "blocked_downstream": list(exc.blocked),
                        "checks": [check.__dict__ for check in exc.checks]},
            ) from exc
        return {
            "document": document_to_json(candidate),
            "build": result.summary(),
            "tags": result.tags,
            "diff": diff_documents(document, candidate),
        }

    def undo(self, document_id: str) -> dict[str, Any]:
        try:
            document = self.store.undo(document_id)
        except StoreError as exc:
            raise ServiceError(exc.code, exc.message, status=exc.status) from exc
        result = self._build(document)
        return {"document": document_to_json(document), "build": result.summary()}

    # ------------------------------------------------------------ reading it back
    def summary(self, document_id: str) -> dict[str, Any]:
        """Compact, talk-able view for the model and the panels."""
        document = self.read(document_id)
        return summarize_document(document, self._build(document))

    def resolve_reference(self, document_id: str, phrase: str) -> dict[str, Any]:
        """Turn "左边的沉头" into feature ids, reasons, and a question if unsure."""
        return resolve_phrase(self.read(document_id), phrase)

    # ------------------------------------------------------------ variants
    def create_variants(self, document_id: str, *,
                        variants: list[dict[str, Any]] | None = None,
                        feature: str | None = None,
                        params: dict[str, list[Any]] | None = None,
                        include_base: bool = False,
                        base_version: int | None = None,
                        thumbs: bool = True) -> dict[str, Any]:
        document = self.read(document_id)
        if base_version is not None and base_version != document.version:
            raise ServiceError(
                "STALE_VERSION",
                f"document is at version {document.version}, variants expected {base_version}",
                status=409,
            )
        try:
            if variants:
                entry = self.variants.create(document, variants, include_base=include_base,
                                             thumbs=thumbs)
            elif feature and params:
                entry = self.variants.create_sweep(document, feature, params,
                                                   include_base=include_base, thumbs=thumbs)
            else:
                raise ValueError("give either `variants` or `feature` with `params`")
        except ValueError as exc:
            raise ServiceError("INVALID_VARIANT", str(exc), status=400) from exc
        return entry.to_json()

    def variant_set(self, set_id: str) -> dict[str, Any]:
        try:
            return self.variants.get(set_id).to_json()
        except KeyError as exc:
            raise ServiceError("NOT_FOUND", f"no variant set {set_id!r}", status=404) from exc

    def variant_thumbnail(self, set_id: str, index: int) -> Path:
        try:
            entry = self.variants.get(set_id)
        except KeyError as exc:
            raise ServiceError("NOT_FOUND", f"no variant set {set_id!r}", status=404) from exc
        variant = next((item for item in entry.variants if item.index == index), None)
        if variant is None or variant.thumb is None:
            raise ServiceError("NOT_FOUND", f"variant {index} has no picture", status=404)
        return variant.thumb

    def variant_sheet(self, set_id: str) -> bytes:
        try:
            return self.variants.sheet(set_id)
        except KeyError as exc:
            raise ServiceError("NOT_FOUND", f"no variant set {set_id!r}", status=404) from exc
        except LookupError as exc:
            raise ServiceError("NOT_FOUND", str(exc), status=404) from exc

    def variant_step_file(self, set_id: str, index: int) -> Path:
        try:
            entry = self.variants.get(set_id)
        except KeyError as exc:
            raise ServiceError("NOT_FOUND", f"no variant set {set_id!r}", status=404) from exc
        variant = next((item for item in entry.variants if item.index == index), None)
        if variant is None:
            raise ServiceError("NOT_FOUND", f"no variant {index}", status=404)
        if variant.step is not None and variant.step.exists():
            return variant.step
        if not variant.ok:
            raise ServiceError("NOT_FOUND", f"variant {index} does not build", status=404)
        # Built on first request, then cached: generating candidates stays cheap.
        candidate = apply_ops(self.read(entry.document_id), variant.ops)
        result = self._build(candidate)
        path = entry.folder / f"{index}.step"
        path.write_bytes(export_bytes(result.final, "step")[0])
        variant.step = path
        return path

    def apply_variant(self, set_id: str, index: int) -> dict[str, Any]:
        try:
            entry = self.variants.get(set_id)
        except KeyError as exc:
            raise ServiceError("NOT_FOUND", f"no variant set {set_id!r}", status=404) from exc
        variant = next((item for item in entry.variants if item.index == index), None)
        if variant is None:
            raise ServiceError("NOT_FOUND", f"no variant {index}", status=404)
        if not variant.ok:
            raise ServiceError(
                "VARIANT_FAILED",
                f"variant {index} does not build; nothing to apply",
                status=422,
                hint=(variant.error or {}).get("hint"),
            )
        return self.apply(entry.document_id, None, variant.ops)

    # ------------------------------------------------------------ derived
    def scene(self, document_id: str, feature: str | None = None) -> dict[str, Any]:
        document = self.read(document_id)
        result = self._build(document)
        feature_id = feature or display_feature(document)
        if feature_id is None:
            return {"version": document.version, "feature": None, "faces": [], "edges": []}
        if feature_id not in result.outputs:
            raise ServiceError("UNKNOWN_FEATURE", f"no output {feature_id!r}", status=404)
        key = f"{document_id}:{document.version}:{feature_id}"
        cached = self._scene_cache.get(document_id)
        if cached and cached.key == key:
            return cached.payload
        payload = build_scene(result.outputs[feature_id], feature_id)
        payload["version"] = document.version
        self._scene_cache[document_id] = SceneCacheEntry(key, payload)
        return payload

    def render(self, document_id: str, feature: str | None = None,
               view: str = "iso") -> bytes:
        document = self.read(document_id)
        result = self._build(document)
        feature_id = feature or display_feature(document)
        if feature_id is None or feature_id not in result.outputs:
            raise ServiceError("UNKNOWN_FEATURE", "nothing to render", status=404)
        from .render import render_png

        try:
            return render_png(result.outputs[feature_id], view=view)
        except Exception as exc:
            raise ServiceError("RENDER_FAILED", str(exc), status=500) from exc

    def export(self, document_id: str, fmt: str, feature: str | None = None) -> tuple[bytes, str]:
        document = self.read(document_id)
        result = self._build(document)
        if fmt == "cfd":
            import json

            payload = [
                {"feature": feature_id, **tag}
                for feature_id, tag in sorted(result.tags.items())
            ]
            return json.dumps({"boundaries": payload}, ensure_ascii=False).encode("utf-8"), "json"
        feature_id = feature or display_feature(document)
        if feature_id is None or feature_id not in result.outputs:
            raise ServiceError("UNKNOWN_FEATURE", "nothing to export", status=404)
        try:
            return export_bytes(result.outputs[feature_id], fmt)
        except ValueError as exc:
            raise ServiceError("UNSUPPORTED_FORMAT", str(exc), status=400) from exc

    def checks(self, document_id: str) -> dict[str, Any]:
        document = self.read(document_id)
        result = self._build(document)
        return {
            "version": document.version,
            "features": [
                {"id": item.feature_id, "checks": [check.__dict__ for check in item.checks]}
                for item in result.features
            ],
            "tags": result.tags,
        }

    # ------------------------------------------------------------ helpers
    def _build(self, document: Document):
        try:
            return build(document, self.cache)
        except BuildError as exc:
            raise ServiceError(
                exc.code, exc.message, status=422, hint=exc.hint,
                detail={"feature_id": exc.feature_id,
                        "blocked_downstream": list(exc.blocked),
                        "checks": [check.__dict__ for check in exc.checks]},
            ) from exc


def diff_documents(before: Document, after: Document) -> dict[str, Any]:
    old = {feature.id: feature_to_json(feature) for feature in before.features}
    new = {feature.id: feature_to_json(feature) for feature in after.features}
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(
        feature_id for feature_id in set(old) & set(new) if old[feature_id] != new[feature_id]
    )
    return {
        "version_before": before.version,
        "version_after": after.version,
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def _document_error(exc: DocumentError) -> ServiceError:
    status = 409 if exc.code == "STALE_VERSION" else 400
    return ServiceError(exc.code, exc.message, status=status, hint=exc.hint)
