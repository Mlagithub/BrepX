"""Document model: features are data, not code.

The document is an ordered list of features. Every edit produces a new,
immutable Document; nothing here touches geometry.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping

Scalar = int | float | bool | str
Arg = Scalar | list


class DocumentError(Exception):
    """A structural edit is impossible; the document is unchanged."""

    def __init__(self, code: str, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint


_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
_TYPE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_MAX_HISTORY = 50


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def features_digest(features: tuple["Feature", ...]) -> str:
    payload = [feature_to_json(feature) for feature in features]
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()[:16]


def _check_scalar(name: str, value: Any) -> Scalar:
    if isinstance(value, bool) or isinstance(value, (int, float, str)):
        return value
    raise DocumentError("INVALID_VALUE", f"{name} must be a scalar, got {type(value).__name__}")


def _check_arg(name: str, value: Any) -> Arg:
    if isinstance(value, (int, float, bool, str)):
        return value
    if isinstance(value, (list, tuple)) and all(
        isinstance(item, (int, float)) and not isinstance(item, bool) for item in value
    ):
        return list(value)
    raise DocumentError("INVALID_VALUE", f"{name} must be a scalar or a numeric vector")


@dataclass(frozen=True)
class Filter:
    method: str
    args: tuple[Arg, ...] = ()
    kwargs: tuple[tuple[str, Arg], ...] = ()

    def __post_init__(self) -> None:
        if not self.method:
            raise DocumentError("INVALID_FILTER", "filter method cannot be empty")
        for index, value in enumerate(self.args):
            _check_arg(f"filter {self.method} arg {index}", value)
        for key, value in self.kwargs:
            _check_arg(f"filter {self.method} kwarg {key}", value)


@dataclass(frozen=True)
class Ref:
    """A semantic query against an earlier feature's output."""

    source: str
    select: str = "faces"
    filters: tuple[Filter, ...] = ()

    def __post_init__(self) -> None:
        if not _ID.match(self.source):
            raise DocumentError("INVALID_REF", f"invalid ref source {self.source!r}")
        if self.select not in {"self", "faces", "edges", "solids", "vertices"}:
            raise DocumentError("INVALID_REF", f"invalid select {self.select!r}")


@dataclass(frozen=True)
class Feature:
    id: str
    type: str
    params: Mapping[str, Scalar] = field(default_factory=dict)
    refs: Mapping[str, Ref] = field(default_factory=dict)
    enabled: bool = True
    note: str = ""
    actor: str = "human"

    def __post_init__(self) -> None:
        if not _ID.match(self.id):
            raise DocumentError("INVALID_FEATURE", f"invalid feature id {self.id!r}")
        if not _TYPE.match(self.type):
            raise DocumentError("INVALID_FEATURE", f"invalid feature type {self.type!r}")
        for key, value in self.params.items():
            _check_scalar(f"param {key}", value)
        if self.actor not in {"human", "agent"}:
            raise DocumentError("INVALID_FEATURE", f"invalid actor {self.actor!r}")
        object.__setattr__(self, "params", dict(self.params))
        object.__setattr__(self, "refs", dict(self.refs))


@dataclass(frozen=True)
class Document:
    id: str
    name: str
    version: int = 1
    features: tuple[Feature, ...] = ()
    history: tuple[str, ...] = ()
    seq: int = 0


def new_document(name: str = "Untitled", document_id: str | None = None,
                 seq: int = 0) -> Document:
    return Document(id=document_id or f"d_{uuid.uuid4().hex[:10]}", name=name, seq=seq)


def validate_layout(document: Document) -> None:
    """Ids are unique and every reference points to an earlier feature."""
    seen: set[str] = set()
    for feature in document.features:
        if feature.id in seen:
            raise DocumentError("DUPLICATE_ID", f"duplicate feature id {feature.id!r}")
        for role, ref in feature.refs.items():
            if ref.source not in seen:
                raise DocumentError(
                    "FORWARD_REF",
                    f"feature {feature.id} ref {role} points to {ref.source!r}, "
                    "which is not an earlier feature",
                )
        seen.add(feature.id)


# ---------------------------------------------------------------- editing

def _find(features: list[Feature], feature_id: str) -> int:
    for index, feature in enumerate(features):
        if feature.id == feature_id:
            return index
    raise DocumentError("UNKNOWN_ID", f"no feature {feature_id!r}")


def _apply_add(features: list[Feature], op: Mapping[str, Any]) -> None:
    feature = feature_from_json(op.get("feature"))
    if any(item.id == feature.id for item in features):
        raise DocumentError("DUPLICATE_ID", f"feature {feature.id!r} already exists")
    position = op.get("before")
    if position is None:
        features.append(feature)
    else:
        features.insert(_find(features, str(position)), feature)


def _apply_update(features: list[Feature], op: Mapping[str, Any]) -> None:
    index = _find(features, str(op.get("id")))
    current = features[index]
    if "type" in op and op["type"] != current.type:
        raise DocumentError("INVALID_OP", "feature type is immutable; remove and re-add instead")
    params = dict(current.params)
    for key, value in dict(op.get("params") or {}).items():
        params[key] = _check_scalar(f"param {key}", value)
    refs = dict(current.refs)
    for role, payload in dict(op.get("refs") or {}).items():
        if payload is None:
            refs.pop(role, None)
        else:
            refs[role] = ref_from_json(payload)
    enabled = bool(op.get("enabled", current.enabled))
    features[index] = Feature(
        id=current.id,
        type=current.type,
        params=params,
        refs=refs,
        enabled=enabled,
        note=str(op.get("note", current.note)),
        actor=str(op.get("actor", current.actor)),
    )


def _apply_remove(features: list[Feature], op: Mapping[str, Any]) -> None:
    feature_id = str(op.get("id"))
    index = _find(features, feature_id)
    for later in features:
        for role, ref in later.refs.items():
            if ref.source == feature_id:
                raise DocumentError(
                    "DANGLING_REF",
                    f"cannot remove {feature_id}: {later.id}.{role} still references it",
                )
    del features[index]


def _apply_reorder(features: list[Feature], op: Mapping[str, Any]) -> None:
    index = _find(features, str(op.get("id")))
    feature = features.pop(index)
    before = op.get("before")
    if before is None:
        features.append(feature)
    else:
        features.insert(_find(features, str(before)), feature)


_OPS = {
    "add": _apply_add,
    "update": _apply_update,
    "remove": _apply_remove,
    "reorder": _apply_reorder,
}


def apply_ops(
    document: Document,
    ops: list[Mapping[str, Any]],
    base_version: int | None = None,
    name: str | None = None,
) -> Document:
    """Apply a batch atomically. Any failure leaves the input untouched."""
    if base_version is not None and base_version != document.version:
        raise DocumentError(
            "STALE_VERSION",
            f"document is at version {document.version}, edit expected {base_version}",
        )
    if not ops and not name:
        return document

    features = list(document.features)
    for op in ops:
        op_name = op.get("op")
        handler = _OPS.get(str(op_name))
        if handler is None:
            raise DocumentError("INVALID_OP", f"unknown op {op_name!r}")
        handler(features, op)

    history = (document.history + (features_digest(document.features),))[-_MAX_HISTORY:]
    updated = Document(
        id=document.id,
        name=name or document.name,
        version=document.version + 1,
        features=tuple(features),
        history=history,
        seq=document.seq,
    )
    validate_layout(updated)
    return updated


# ---------------------------------------------------------------- json

def filter_to_json(value: Filter) -> dict[str, Any]:
    return {
        "method": value.method,
        "args": list(value.args),
        "kwargs": {key: item for key, item in value.kwargs},
    }


def filter_from_json(payload: Mapping[str, Any]) -> Filter:
    return Filter(
        method=str(payload.get("method", "")),
        args=tuple(payload.get("args") or ()),
        kwargs=tuple(sorted(dict(payload.get("kwargs") or {}).items())),
    )


def ref_to_json(value: Ref) -> dict[str, Any]:
    return {
        "source": value.source,
        "select": value.select,
        "filters": [filter_to_json(item) for item in value.filters],
    }


def ref_from_json(payload: Mapping[str, Any] | None) -> Ref:
    if payload is None:
        raise DocumentError("INVALID_REF", "ref payload is required")
    return Ref(
        source=str(payload.get("source", "")),
        select=str(payload.get("select", "faces")),
        filters=tuple(filter_from_json(item) for item in payload.get("filters") or ()),
    )


def feature_to_json(value: Feature) -> dict[str, Any]:
    return {
        "id": value.id,
        "type": value.type,
        "params": dict(value.params),
        "refs": {role: ref_to_json(ref) for role, ref in value.refs.items()},
        "enabled": value.enabled,
        "note": value.note,
        "actor": value.actor,
    }


def feature_from_json(payload: Mapping[str, Any] | None) -> Feature:
    if payload is None:
        raise DocumentError("INVALID_FEATURE", "feature payload is required")
    return Feature(
        id=str(payload.get("id", "")),
        type=str(payload.get("type", "")),
        params=dict(payload.get("params") or {}),
        refs={role: ref_from_json(ref) for role, ref in dict(payload.get("refs") or {}).items()},
        enabled=bool(payload.get("enabled", True)),
        note=str(payload.get("note", "")),
        actor=str(payload.get("actor", "human")),
    )


def document_to_json(value: Document) -> dict[str, Any]:
    return {
        "id": value.id,
        "name": value.name,
        "version": value.version,
        "features": [feature_to_json(item) for item in value.features],
        "history": list(value.history),
        "seq": value.seq,
    }


def document_from_json(payload: Mapping[str, Any]) -> Document:
    document = Document(
        id=str(payload.get("id", "")),
        name=str(payload.get("name", "Untitled")),
        version=int(payload.get("version", 1)),
        features=tuple(feature_from_json(item) for item in payload.get("features") or ()),
        history=tuple(payload.get("history") or ()),
        seq=int(payload.get("seq", 0) or 0),
    )
    validate_layout(document)
    return document
