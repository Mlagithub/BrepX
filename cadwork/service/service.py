"""Business layer shared by the HTTP surface, the MCP surface and tests."""

from __future__ import annotations

import hashlib
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping

from cadwork.design.build import CACHE_EPOCH, BuildCache, BuildError, build
from cadwork.design.diff import compare_parts
from cadwork.design.document import (
    Document,
    DocumentError,
    FocusParam,
    Milestone,
    apply_ops,
    document_to_json,
    feature_to_json,
    features_digest,
    milestone_to_json,
)
from cadwork.design.features import FEATURES, catalog
from cadwork.design.probe import pick_to_ref, probe_geometry, probe_ref

from .export import export_bytes
from .resolve import resolve as resolve_phrase
from .resolve import summarize as summarize_document
from .scene import build_scene, display_feature
from .store import Store, StoreError
from .variants import VariantBook

MAX_FOCUS = 4
FOCUS_PREFERENCE = (
    "r_out", "radius", "length", "width", "height", "thickness", "depth",
    "count", "angle", "amount", "diameter", "wrap", "factor", "distance",
    "fillet_r", "r_in", "turns", "pitch", "height_mm",
)


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


class EventBus:
    """Fan-out of version facts to every connected browser stream."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[queue.Queue]] = {}

    def subscribe(self, document_id: str) -> queue.Queue:
        channel: queue.Queue = queue.Queue(maxsize=512)
        with self._lock:
            self._subscribers.setdefault(document_id, []).append(channel)
        return channel

    def unsubscribe(self, document_id: str, channel: queue.Queue) -> None:
        with self._lock:
            channels = self._subscribers.get(document_id) or []
            if channel in channels:
                channels.remove(channel)
            if not channels:
                self._subscribers.pop(document_id, None)

    def publish(self, document_id: str, event: str, payload: Mapping[str, Any]) -> None:
        with self._lock:
            channels = list(self._subscribers.get(document_id, ()))
        for channel in channels:
            try:
                channel.put_nowait((event, dict(payload)))
            except queue.Full:
                pass


@dataclass
class IntentStep:
    index: int
    title: str
    status: str = "pending"
    milestone_version: int | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "title": self.title,
            "status": self.status,
            "milestone_version": self.milestone_version,
        }


@dataclass
class IntentState:
    intent_id: str
    document_id: str
    base_version: int
    prompt: str
    status: str = "running"
    steps: list[IntentStep] = field(default_factory=list)
    created: float = field(default_factory=time.time)

    def to_json(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "document_id": self.document_id,
            "base_version": self.base_version,
            "prompt": self.prompt,
            "status": self.status,
            "created": self.created,
            "steps": [step.to_json() for step in self.steps],
        }


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
        self.bus = EventBus()
        self._lock = threading.RLock()
        self._intents: dict[str, IntentState] = {}
        self._active_intent: dict[str, str] = {}

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

    def read(self, document_id: str, version: int | None = None) -> Document:
        try:
            if version is not None:
                return self.store.get_version(document_id, version)
            return self.store.get(document_id)
        except StoreError as exc:
            raise ServiceError(exc.code, exc.message, status=exc.status) from exc

    def document_json(self, document_id: str) -> dict[str, Any]:
        document = self.read(document_id)
        payload = document_to_json(document)
        payload["build"] = self._build_summary(document)
        return payload

    def catalog(self) -> list[dict[str, Any]]:
        return catalog()

    # ------------------------------------------------------------ state
    def state(self, document_id: str) -> dict[str, Any]:
        document = self.read(document_id)
        vacant = document.version == 0 or not document.features
        result = None
        metrics: dict[str, Any] | None = None
        checks = {"passed": 0, "total": 0, "ok": True, "items": []}
        if not vacant:
            result = self._build(document)
            metrics = self._metrics(result)
            checks = self._checks_projection(result)
        latest = document.milestones[-1] if document.milestones else None
        return {
            "document": {"id": document.id, "name": document.name, "version": document.version},
            "vacant": vacant,
            "metrics": metrics,
            "checks": checks,
            "milestones": [
                self._milestone_projection(document, item) for item in document.milestones
            ],
            "focus_params": self._focus_projection(document, latest),
            "features": self._feature_projection(document),
            "active_intent": self._intent_json(document.id),
        }

    def _milestone_projection(self, document: Document, item: Milestone) -> dict[str, Any]:
        payload = milestone_to_json(item)
        feature_map = {feature.id: feature for feature in document.features}
        values = []
        for focus in item.focus_params:
            feature = feature_map.get(focus.feature_id)
            value = feature.params.get(focus.param) if feature else None
            entry = focus_param_json_with_bounds(focus, feature)
            entry["value"] = value
            values.append(entry)
        payload["focus_params"] = values
        return payload

    def _focus_projection(self, document: Document,
                          latest: Milestone | None) -> list[dict[str, Any]]:
        if latest is None or document.version == 0:
            return []
        feature_map = {feature.id: feature for feature in document.features}
        entries: list[dict[str, Any]] = []
        for focus in latest.focus_params:
            feature = feature_map.get(focus.feature_id)
            if feature is None or focus.param not in feature.params:
                continue
            entry = focus_param_json_with_bounds(focus, feature)
            entry["value"] = feature.params[focus.param]
            entries.append(entry)
        if entries:
            return entries[:MAX_FOCUS]
        return self._derive_focus(document, list(latest.changed_features))

    def _derive_focus(self, document: Document,
                      changed_ids: list[str]) -> list[dict[str, Any]]:
        feature_map = {feature.id: feature for feature in document.features}
        ordered: list[str] = [item for item in changed_ids if item in feature_map]
        ordered += [item.id for item in reversed(document.features) if item.id not in ordered]
        entries: list[dict[str, Any]] = []
        for feature_id in ordered:
            feature = feature_map.get(feature_id)
            if feature is None or not feature.enabled:
                continue
            spec = FEATURES.get(feature.type)
            numeric = [
                key for key, value in feature.params.items()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            ]
            numeric.sort(key=lambda key: (
                FOCUS_PREFERENCE.index(key) if key in FOCUS_PREFERENCE else len(FOCUS_PREFERENCE),
                key,
            ))
            for key in numeric:
                if len(entries) >= MAX_FOCUS:
                    return entries
                param = spec.params.get(key) if spec else None
                entries.append({
                    "feature_id": feature_id,
                    "param": key,
                    "label": f"{feature_id}.{key}",
                    "unit": (param.unit or "") if param else "",
                    "minimum": param.minimum if param else None,
                    "maximum": param.maximum if param else None,
                    "origin": "derived",
                    "value": feature.params[key],
                })
        return entries

    def _feature_projection(self, document: Document) -> list[dict[str, Any]]:
        referenced: set[str] = set()
        for feature in document.features:
            for ref in feature.refs.values():
                referenced.add(ref.source)
        entries: list[dict[str, Any]] = []
        for feature in document.features:
            entries.append({
                "id": feature.id,
                "type": feature.type,
                "enabled": feature.enabled,
                "can_toggle": feature.id not in referenced,
                "actor": feature.actor,
            })
        return entries

    def _metrics(self, result: Any) -> dict[str, Any]:
        final = getattr(result, "final", None)
        if final is None:
            return {"faces": 0, "volume": 0.0, "area": 0.0, "edges": 0, "watertight": False}
        faces = list(final.faces()) if hasattr(final, "faces") else []
        edges = list(final.edges()) if hasattr(final, "edges") else []
        area = sum(float(getattr(face, "area", 0.0)) for face in faces)
        watertight = all(
            check.ok for item in result.features for check in item.checks
            if check.name == "watertight"
        )
        return {
            "faces": len(faces),
            "volume": round(float(getattr(final, "volume", 0.0)), 2),
            "area": round(area, 2),
            "edges": len(edges),
            "watertight": watertight,
        }

    def _checks_projection(self, result: Any) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for item in result.features:
            for check in item.checks:
                items.append({
                    "feature_id": item.feature_id,
                    "name": check.name,
                    "ok": check.ok,
                    "expected": check.expected,
                    "hint": check.hint,
                })
        passed = sum(1 for item in items if item["ok"])
        return {
            "passed": passed,
            "total": len(items),
            "ok": passed == len(items),
            "items": items,
        }

    def _build_summary(self, document: Document) -> dict[str, Any]:
        if not document.features:
            return {"version": document.version, "features": [], "tags": {},
                    "seconds": 0.0, "cache_hits": 0}
        result = self._build(document)
        return result.summary()

    # ------------------------------------------------------------ writes
    def delete_document(self, document_id: str) -> None:
        try:
            self.store.delete(document_id)
        except StoreError as exc:
            raise ServiceError(exc.code, exc.message, status=exc.status) from exc

    def apply(
        self,
        document_id: str,
        base_version: int | None,
        ops: list[Mapping[str, Any]],
        name: str | None = None,
        milestone_title: str | None = None,
        focus_params: list[Mapping[str, Any] | FocusParam] | None = None,
        actor: str = "human",
    ) -> dict[str, Any]:
        return self.commit(
            document_id,
            base_version,
            ops,
            title=milestone_title or "",
            focus_params=focus_params,
            actor=actor,
            name=name,
        )

    def commit(
        self,
        document_id: str,
        base_version: int | None,
        ops: list[Mapping[str, Any]],
        title: str = "",
        focus_params: list[Mapping[str, Any] | FocusParam] | None = None,
        actor: str = "agent",
        intent_id: str | None = None,
        step_index: int | None = None,
        parent_version: int | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            document = self.read(document_id)
            self._guard_intent(intent_id, document_id)
            try:
                updated = apply_ops(
                    document,
                    list(ops),
                    base_version,
                    name,
                    milestone_title=title or None,
                    focus_params=focus_params,
                    actor=actor,
                    intent_id=intent_id,
                    step_index=step_index,
                    parent_version=parent_version,
                )
            except DocumentError as exc:
                raise _document_error(exc) from exc
            latest = updated.milestones[-1] if updated.milestones else None
            focus = self._resolve_focus(updated, document, latest, focus_params)
            updated = self._replace_latest(updated, latest, focus=focus)
            if updated.features:
                result = self._build(updated)
                metrics = self._metrics(result)
                delta = self._changed_faces(document, updated)
            else:
                result = None
                metrics = {"faces": 0, "volume": 0.0, "area": 0.0, "edges": 0, "watertight": False}
                delta = {"indices": [], "centers": []}
            changed_faces = delta["indices"]
            updated = self._replace_latest(updated, updated.milestones[-1],
                                           metrics=metrics, changed_faces=changed_faces)
            self.store.save(updated)
            if intent_id:
                self._advance_intent(intent_id, step_index, "done", updated.version)
            payload = self._milestone_event(updated, result, metrics, changed_faces)
            payload["changed_face_centers"] = delta["centers"]
            self.bus.publish(document_id, "milestone", payload)
            return {
                "document": document_to_json(updated),
                "build": result.summary() if result is not None else {
                    "version": updated.version, "features": [], "tags": {},
                    "seconds": 0.0, "cache_hits": 0,
                },
                "tags": result.tags if result is not None else {},
                "milestone": payload,
            }

    def _resolve_focus(
        self,
        updated: Document,
        previous: Document,
        latest: Milestone | None,
        provided: list[Mapping[str, Any] | FocusParam] | None,
    ) -> tuple[FocusParam, ...]:
        if latest is None:
            return ()
        entries: list[FocusParam] = []
        for item in provided or ():
            focus = item if isinstance(item, FocusParam) else focus_param_from_json(item)
            bounded = self._with_bounds(updated, focus)
            if bounded is not None:
                entries.append(bounded)
        if len(entries) < MAX_FOCUS:
            keep = {item.feature_id for item in entries}
            for derived in self._derive_focus(updated, list(latest.changed_features)):
                if derived["feature_id"] in keep:
                    continue
                entries.append(FocusParam(
                    feature_id=derived["feature_id"],
                    param=derived["param"],
                    label=derived["label"],
                    unit=derived["unit"],
                    minimum=derived["minimum"],
                    maximum=derived["maximum"],
                    origin="derived",
                ))
                if len(entries) >= MAX_FOCUS:
                    break
        return tuple(entries[:MAX_FOCUS])

    def _with_bounds(self, document: Document, focus: FocusParam) -> FocusParam | None:
        feature = next((item for item in document.features if item.id == focus.feature_id), None)
        if feature is None or focus.param not in feature.params:
            return None
        spec = FEATURES.get(feature.type)
        param = spec.params.get(focus.param) if spec else None
        return FocusParam(
            feature_id=focus.feature_id,
            param=focus.param,
            label=focus.label or f"{focus.feature_id}.{focus.param}",
            unit=focus.unit or ((param.unit or "") if param else ""),
            minimum=focus.minimum if focus.minimum is not None else (param.minimum if param else None),
            maximum=focus.maximum if focus.maximum is not None else (param.maximum if param else None),
            origin=focus.origin or "agent",
        )

    def _replace_latest(
        self,
        document: Document,
        latest: Milestone | None,
        focus: tuple[FocusParam, ...] | None = None,
        metrics: Mapping[str, Any] | None = None,
        changed_faces: list[int] | None = None,
    ) -> Document:
        if latest is None:
            return document
        milestones = list(document.milestones)
        updated = latest
        if focus is not None:
            updated = replace(updated, focus_params=focus)
        if metrics is not None:
            updated = replace(updated, metrics=tuple(sorted(metrics.items())))
        if changed_faces is not None:
            updated = replace(updated, changed_face_indices=tuple(changed_faces))
        milestones[-1] = updated
        return Document(id=document.id, name=document.name, version=document.version,
                        features=document.features, milestones=tuple(milestones),
                        history=document.history, seq=document.seq)

    def _changed_faces(self, before: Document, after: Document) -> dict[str, list]:
        if not before.features:
            return {"indices": [], "centers": []}
        try:
            before_result = self._build(before)
        except ServiceError:
            return {"indices": [], "centers": []}
        after_result = self._build(after)
        before_feature = display_feature(before)
        after_feature = display_feature(after)
        if before_feature is None or after_feature is None:
            return {"indices": [], "centers": []}
        report = compare_parts(before_result.outputs.get(before_feature),
                               after_result.outputs.get(after_feature))
        return {
            "indices": report["changed_face_indices"],
            "centers": report["changed_face_centers"],
        }

    def _milestone_event(self, document: Document, result: Any,
                         metrics: Mapping[str, Any], changed_faces: list[int]) -> dict[str, Any]:
        latest = document.milestones[-1]
        checks = self._checks_projection(result) if result is not None else {
            "passed": 0, "total": 0,
        }
        return {
            "version": document.version,
            "parent_version": latest.parent_version,
            "title": latest.title,
            "actor": latest.actor,
            "intent_id": latest.intent_id,
            "step_index": latest.step_index,
            "changed_face_indices": list(changed_faces),
            "focus_params": self._focus_projection(document, latest),
            "metrics": dict(metrics),
            "checks_passed": checks["passed"],
            "checks_total": checks["total"],
        }

    # ------------------------------------------------------------ intents
    def begin_intent(self, document_id: str, prompt: str, steps: list[str],
                     base_version: int | None = None) -> dict[str, Any]:
        document = self.read(document_id)
        intent = IntentState(
            intent_id=f"in_{uuid.uuid4().hex[:8]}",
            document_id=document_id,
            base_version=document.version if base_version is None else base_version,
            prompt=prompt,
            steps=[IntentStep(index=index + 1, title=str(title))
                   for index, title in enumerate(steps)],
        )
        with self._lock:
            self._intents[intent.intent_id] = intent
            self._active_intent[document_id] = intent.intent_id
        self.bus.publish(document_id, "intent", intent.to_json())
        return intent.to_json()

    def intent_json(self, document_id: str) -> dict[str, Any] | None:
        return self._intent_json(document_id)

    def _intent_json(self, document_id: str) -> dict[str, Any] | None:
        intent_id = self._active_intent.get(document_id)
        if intent_id is None:
            return None
        intent = self._intents.get(intent_id)
        if intent is None:
            return None
        return intent.to_json()

    def _advance_intent(self, intent_id: str, step_index: int | None,
                        status: str, milestone_version: int) -> None:
        intent = self._intents.get(intent_id)
        if intent is None:
            return
        if step_index is not None:
            for step in intent.steps:
                if step.index == step_index:
                    step.status = status
                    step.milestone_version = milestone_version
        if intent.steps and all(step.status == "done" for step in intent.steps):
            intent.status = "completed"
        self.bus.publish(intent.document_id, "intent", intent.to_json())

    def _guard_intent(self, intent_id: str | None, document_id: str) -> None:
        if not intent_id:
            return
        intent = self._intents.get(intent_id)
        if intent is None:
            raise ServiceError("UNKNOWN_INTENT", f"no intent {intent_id!r}", status=404)
        if intent.status == "cancelled":
            raise ServiceError("INTENT_CANCELLED", "this intent was cancelled", status=409)

    def cancel_intent(self, document_id: str, intent_id: str) -> dict[str, Any]:
        intent = self._intents.get(intent_id)
        if intent is None or intent.document_id != document_id:
            raise ServiceError("UNKNOWN_INTENT", f"no intent {intent_id!r}", status=404)
        intent.status = "cancelled"
        for step in intent.steps:
            if step.status in {"pending", "running"}:
                step.status = "skipped"
        self.bus.publish(document_id, "intent", intent.to_json())
        return intent.to_json()

    def add_intent_note(self, document_id: str, text: str,
                        base_version: int | None = None) -> dict[str, Any]:
        """Queue a typed request for the agent, kept in the document store."""
        phrase = text.strip()
        if not phrase:
            raise ServiceError("INVALID_INTENT", "intent text is empty", status=400)
        try:
            entry = self.store.add_intent(document_id, phrase, base_version=base_version)
        except StoreError as exc:
            raise ServiceError(exc.code, exc.message, status=exc.status) from exc
        return {"intent": entry, "pending": len(self.store.list_intents(document_id))}

    def list_intents(self, document_id: str) -> dict[str, Any]:
        self.read(document_id)
        return {"intents": self.store.list_intents(document_id)}

    def clear_intents(self, document_id: str) -> dict[str, Any]:
        self.read(document_id)
        return {"cleared": self.store.clear_intents(document_id)}

    # ------------------------------------------------------------ review edits
    def tweak(
        self,
        document_id: str,
        changes: list[Mapping[str, Any]],
        base_version: int | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        ops = [
            {"op": "update", "id": str(change.get("feature_id")),
             "params": dict(change.get("params") or {})}
            for change in changes
        ]
        if not ops:
            raise ServiceError("INVALID_TWEAK", "no changes supplied", status=400)
        labels = ", ".join(
            f"{key}={value}"
            for change in changes
            for key, value in dict(change.get("params") or {}).items()
        )
        focus = [
            {"feature_id": str(change.get("feature_id")), "param": key}
            for change in changes
            for key in dict(change.get("params") or {})
        ]
        return self.commit(
            document_id,
            base_version,
            ops,
            title=title or f"微调 {labels}",
            focus_params=focus,
            actor="human",
        )

    def toggle(self, document_id: str, feature_id: str) -> dict[str, Any]:
        document = self.read(document_id)
        projection = {item["id"]: item for item in self._feature_projection(document)}
        entry = projection.get(feature_id)
        if entry is None:
            raise ServiceError("UNKNOWN_ID", f"no feature {feature_id!r}", status=404)
        if not entry["can_toggle"]:
            raise ServiceError(
                "FEATURE_NOT_TOGGLEABLE",
                f"{feature_id} still feeds later features",
                status=409,
                hint="只可启停没有下游引用的末端特征",
            )
        return self.commit(
            document_id,
            document.version,
            [{"op": "update", "id": feature_id, "enabled": not entry["enabled"]}],
            title=f"{'开启' if not entry['enabled'] else '关闭'} {feature_id}",
            actor="human",
        )

    def revert(self, document_id: str, target_version: int,
               title: str | None = None) -> dict[str, Any]:
        document = self.read(document_id)
        if target_version == document.version:
            return {"document": document_to_json(document), "build": self._build_summary(document)}
        target = self.read(document_id, version=target_version)
        ops: list[dict[str, Any]] = [
            {"op": "remove", "id": feature.id}
            for feature in reversed(document.features)
        ]
        ops += [{"op": "add", "feature": feature_to_json(feature)} for feature in target.features]
        focus = [
            {"feature_id": item.feature_id, "param": item.param}
            for item in target.milestones[-1].focus_params
        ] if target.milestones else None
        return self.commit(
            document_id,
            document.version,
            ops,
            title=title or f"回到 v{target_version}",
            focus_params=focus,
            actor="human",
            parent_version=target_version,
        )

    def undo(self, document_id: str) -> dict[str, Any]:
        document = self.read(document_id)
        latest = document.milestones[-1]
        target = latest.parent_version
        if target is None:
            raise ServiceError("NO_HISTORY", "已是初始版本，无法撤销", status=409)
        return self.revert(document_id, target)

    def preview(self, document_id: str, ops: list[Mapping[str, Any]],
                base_version: int | None = None) -> dict[str, Any]:
        document = self.read(document_id)
        try:
            candidate = apply_ops(document, list(ops), base_version)
        except DocumentError as exc:
            raise _document_error(exc) from exc
        try:
            result = build(candidate, self.cache)
        except BuildError as exc:
            detail = {"feature_id": exc.feature_id,
                      "blocked_downstream": list(exc.blocked),
                      "checks": [check.__dict__ for check in exc.checks]}
            self.bus.publish(document_id, "error", {**exc.to_json(), **detail})
            raise ServiceError(exc.code, exc.message, status=422, hint=exc.hint,
                               detail=detail) from exc
        metrics = self._metrics(result)
        changed = []
        if document.features:
            before_result = self._build(document)
            before_feature = display_feature(document)
            after_feature = display_feature(candidate)
            if before_feature and after_feature:
                changed = compare_parts(before_result.outputs.get(before_feature),
                                        result.outputs.get(after_feature))["changed_face_indices"]
        return {
            "document": document_to_json(candidate),
            "build": result.summary(),
            "tags": result.tags,
            "diff": diff_documents(document, candidate),
            "metrics": metrics,
            "changed_face_indices": changed,
        }

    def pick(self, document_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        document = self.read(
            document_id,
            version=int(payload["version"]) if payload.get("version") is not None else None,
        )
        result = self._build(document)
        point = payload.get("point") or []
        if len(point) != 3:
            raise ServiceError("INVALID_PICK", "point must hold three numbers", status=400)
        found = pick_to_ref(
            document,
            result,
            point=[float(point[0]), float(point[1]), float(point[2])],
            normal=payload.get("normal"),
            area=float(payload["area"]) if payload.get("area") is not None else None,
            feature_id=payload.get("feature_id"),
        )
        if not found.get("ok"):
            raise ServiceError("PICK_FAILED", found.get("message", "no face matched"), status=422)
        label = self._anchor_label(found)
        return {
            "label": label,
            "feature_id": found["feature_id"],
            "face_index": found["face_index"],
            "surface_type": found.get("surface_type", "face"),
            "dimensions": {
                "area": found["area"],
                "center": found["center"],
                "normal": found["normal"],
                "orientation": found["orientation"],
            },
            "suggested_ref": found["suggested_ref"],
        }

    def _anchor_label(self, found: Mapping[str, Any]) -> str:
        orientation = found.get("orientation") or "face"
        surface_type = found.get("surface_type") or "face"
        feature_id = found.get("feature_id") or ""
        area = float(found.get("area") or 0.0)
        center = found.get("center") or [0.0, 0.0, 0.0]
        prefix = f"{feature_id} " if feature_id else ""
        return (
            f"@{prefix}{orientation} · {surface_type} · {area:.1f} mm² · "
            f"({center[0]:.1f}, {center[1]:.1f}, {center[2]:.1f})"
        )

    def probe(self, document_id: str, *, feature_id: str | None = None,
              ref: Mapping[str, Any] | None = None,
              picked_point: list[float] | None = None,
              picked_normal: list[float] | None = None,
              picked_area: float | None = None) -> dict[str, Any]:
        document = self.read(document_id)
        result = self._build(document)
        payload: dict[str, Any] = {
            "document_id": document.id,
            "version": document.version,
            "geometry": probe_geometry(document, result, feature_id=feature_id),
        }
        if ref is not None:
            payload["ref_probe"] = probe_ref(result, ref)
        if picked_point is not None and len(picked_point) == 3:
            payload["pick_probe"] = pick_to_ref(
                document, result, point=picked_point, normal=picked_normal,
                area=picked_area, feature_id=feature_id,
            )
        return payload

    def compare_versions(self, document_id: str, base_version: int,
                         target_version: int | None = None) -> dict[str, Any]:
        doc_after = self.read(document_id, version=target_version)
        doc_before = self.read(document_id, version=base_version)
        res_before = self._build(doc_before)
        res_after = self._build(doc_after)
        before_feature = display_feature(doc_before)
        after_feature = display_feature(doc_after)
        part_before = res_before.outputs.get(before_feature) if before_feature else None
        part_after = res_after.outputs.get(after_feature) if after_feature else None
        report = compare_parts(part_before, part_after)
        return {
            "document_id": document_id,
            "doc_diff": diff_documents(doc_before, doc_after),
            **report,
        }

    # ------------------------------------------------------------ legacy reads
    def summary(self, document_id: str) -> dict[str, Any]:
        document = self.read(document_id)
        if not document.features:
            return summarize_document(document, None)
        return summarize_document(document, self._build(document))

    def resolve_reference(self, document_id: str, phrase: str) -> dict[str, Any]:
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
        payload = entry.to_json()
        payload["all_failed"] = all(not item["ok"] for item in payload["variants"])
        self.bus.publish(document_id, "variants", payload)
        return payload

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
        document = self.read(entry.document_id)
        return self.commit(
            entry.document_id,
            document.version,
            variant.ops,
            title=f"采纳方案 {variant.label}",
            actor="human",
        )

    # ------------------------------------------------------------ derived
    def scene(self, document_id: str, feature: str | None = None) -> dict[str, Any]:
        document = self.read(document_id)
        if not document.features:
            return {"version": document.version, "feature": None, "faces": [], "edges": [],
                    "metrics": {"faces": 0, "volume": 0.0, "edges": 0}}
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
        if not document.features:
            raise ServiceError("EMPTY_DOCUMENT", "空白文档没有可渲染的几何", status=409)
        result = self._build(document)
        feature_id = feature or display_feature(document)
        if feature_id is None or feature_id not in result.outputs:
            raise ServiceError("UNKNOWN_FEATURE", "nothing to render", status=404)
        from .render import render_png

        try:
            return render_png(result.outputs[feature_id], view=view)
        except Exception as exc:
            raise ServiceError("RENDER_FAILED", str(exc), status=500) from exc

    def export(self, document_id: str, fmt: str, feature: str | None = None,
               version: int | None = None) -> tuple[bytes, str]:
        document = self.read(document_id, version=version)
        if not document.features:
            raise ServiceError("EMPTY_DOCUMENT", "空白文档没有可导出的几何", status=409)
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

    def step_bytes(self, document_id: str, version: int | None = None) -> bytes:
        document = self.read(document_id, version=version)
        if not document.features:
            raise ServiceError("EMPTY_DOCUMENT", "空白文档没有可导出的几何", status=409)
        enabled = tuple(item for item in document.features if item.enabled)
        if not enabled:
            raise ServiceError("EMPTY_DOCUMENT", "没有启用的特征可导出", status=409)
        digest_key = hashlib.sha256(
            f"{CACHE_EPOCH}:{features_digest(enabled)}".encode("utf-8")
        ).hexdigest()
        cached = self.store.get_step(digest_key)
        if cached is not None:
            return cached
        payload = self.export(document_id, "step", version=version)[0]
        self.store.put_step(digest_key, payload)
        return payload

    def checks(self, document_id: str) -> dict[str, Any]:
        document = self.read(document_id)
        if not document.features:
            return {"version": document.version, "features": [], "tags": {}, **self._checks_projection_empty()}
        result = self._build(document)
        payload = {
            "version": document.version,
            "features": [
                {"id": item.feature_id, "checks": [check.__dict__ for check in item.checks]}
                for item in result.features
            ],
            "tags": result.tags,
        }
        projection = self._checks_projection(result)
        payload.update({"passed": projection["passed"], "total": projection["total"],
                        "ok": projection["ok"]})
        return payload

    @staticmethod
    def _checks_projection_empty() -> dict[str, Any]:
        return {"passed": 0, "total": 0, "ok": True}

    # ------------------------------------------------------------ helpers
    def _build(self, document: Document):
        if not document.features:
            raise ServiceError("EMPTY_DOCUMENT", "empty document has no geometry", status=409)
        try:
            return build(document, self.cache)
        except BuildError as exc:
            detail = {"feature_id": exc.feature_id,
                      "blocked_downstream": list(exc.blocked),
                      "checks": [check.__dict__ for check in exc.checks]}
            raise ServiceError(exc.code, exc.message, status=422, hint=exc.hint,
                               detail=detail) from exc


def focus_param_json_with_bounds(focus: FocusParam, feature: Any) -> dict[str, Any]:
    payload = {
        "feature_id": focus.feature_id,
        "param": focus.param,
        "label": focus.label or f"{focus.feature_id}.{focus.param}",
        "unit": focus.unit,
        "minimum": focus.minimum,
        "maximum": focus.maximum,
        "origin": focus.origin,
        "value": None,
    }
    if feature is not None:
        spec = FEATURES.get(feature.type)
        param = spec.params.get(focus.param) if spec else None
        if param is not None:
            payload["unit"] = payload["unit"] or (param.unit or "")
            if payload["minimum"] is None:
                payload["minimum"] = param.minimum
            if payload["maximum"] is None:
                payload["maximum"] = param.maximum
    return payload


def focus_param_from_json(payload: Mapping[str, Any]) -> FocusParam:
    maximum = payload.get("maximum")
    minimum = payload.get("minimum")
    return FocusParam(
        feature_id=str(payload.get("feature_id", "")),
        param=str(payload.get("param", "")),
        label=str(payload.get("label", "")),
        unit=str(payload.get("unit", "")),
        minimum=float(minimum) if minimum is not None else None,
        maximum=float(maximum) if maximum is not None else None,
        origin=str(payload.get("origin", "agent")),
    )


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
