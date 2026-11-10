"""Replay the feature list. Geometry is a cache of the document, not its state."""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Mapping

from cadwork import smlib as S

from . import refs
from .checks import CheckResult
from .document import Document, Feature, canonical_json, filter_to_json
from .features import (
    FEATURES,
    FeatureError,
    FeatureOutput,
    resolve_params,
    validate_feature,
)

from cadwork.design.features import INPUT_KINDS

CACHE_EPOCH = "2026-11-10.2 smlibpy-0.6"


class BuildError(Exception):
    """A feature failed. The document is untouched; downstream is blocked."""

    def __init__(
        self,
        code: str,
        message: str,
        feature_id: str | None = None,
        hint: str | None = None,
        checks: tuple[CheckResult, ...] = (),
        blocked: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.feature_id = feature_id
        self.hint = hint
        self.checks = checks
        self.blocked = blocked

    def to_json(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "feature_id": self.feature_id,
            "hint": self.hint,
            "checks": [check.__dict__ for check in self.checks],
            "blocked_downstream": list(self.blocked),
        }


@dataclass(frozen=True)
class FeatureResult:
    feature_id: str
    checks: tuple[CheckResult, ...]
    seconds: float
    cached: bool
    meta: dict[str, Any]


@dataclass
class BuildResult:
    document_version: int
    outputs: dict[str, Any]
    final: Any | None
    features: list[FeatureResult] = field(default_factory=list)
    tags: dict[str, dict[str, Any]] = field(default_factory=dict)
    seconds: float = 0.0
    cache_hits: int = 0

    def summary(self) -> dict[str, Any]:
        return {
            "version": self.document_version,
            "features": [
                {"id": item.feature_id, "seconds": round(item.seconds, 4),
                 "cached": item.cached, "checks": [c.__dict__ for c in item.checks]}
                for item in self.features
            ],
            "tags": self.tags,
            "seconds": round(self.seconds, 4),
            "cache_hits": self.cache_hits,
        }


class BuildCache:
    """Content-addressed LRU. Deleting it only costs time, never correctness."""

    def __init__(self, capacity: int = 64) -> None:
        self.capacity = capacity
        self._data: OrderedDict[str, tuple[FeatureOutput, tuple[CheckResult, ...]]] = OrderedDict()

    def get(self, key: str):
        value = self._data.get(key)
        if value is not None:
            self._data.move_to_end(key)
        return value

    def put(self, key: str, value) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


_DEFAULT_CACHE = BuildCache()


def _ref_key(ref, source_key: str) -> str:
    payload = {
        "source": ref.source,
        "select": ref.select,
        "filters": [filter_to_json(item) for item in ref.filters],
        "source_key": source_key,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _feature_key(feature: Feature, params: Mapping[str, Any], input_keys: list[str]) -> str:
    payload = {
        "epoch": CACHE_EPOCH,
        "type": feature.type,
        "params": dict(params),
        "inputs": input_keys,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _check_kind(feature: Feature, role: str, kind: str) -> Any:
    spec = INPUT_KINDS.get(kind)
    if spec is None:
        raise BuildError(
            "UNKNOWN_KIND",
            f"{feature.id}.{role} uses unknown input kind {kind!r}",
            feature.id,
            hint=f"known kinds: {', '.join(sorted(INPUT_KINDS))}",
        )
    ref = feature.refs[role]
    if ref.select not in spec.selects:
        expected = " or ".join(repr(select) for select in spec.selects)
        raise BuildError(
            "INVALID_REF_KIND",
            f"{feature.id}.{role} must use select={expected}, got {ref.select!r}",
            feature.id,
        )
    return spec


def build(document: Document, cache: BuildCache | None = None) -> BuildResult:
    cache = cache if cache is not None else _DEFAULT_CACHE
    enabled = [feature for feature in document.features if feature.enabled]
    outputs: dict[str, Any] = {}
    fingerprints: dict[str, str] = {}
    results: list[FeatureResult] = []
    tags: dict[str, dict[str, Any]] = {}
    hits = 0
    started = time.perf_counter()

    for index, feature in enumerate(enabled):
        try:
            spec = validate_feature(feature.type, feature.refs)
            params = resolve_params(spec, feature.params)
        except FeatureError as exc:
            raise BuildError(exc.code, exc.message, feature.id, exc.hint,
                             blocked=tuple(f.id for f in enabled[index + 1:])) from exc

        inputs: dict[str, Any] = {}
        input_keys: list[str] = []
        for role, kind in spec.inputs:
            ref = feature.refs.get(role)
            if ref is None:
                inputs[role] = None
                continue
            kind_spec = _check_kind(feature, role, kind)
            try:
                value = refs.resolve(ref, outputs)
            except refs.RefError as exc:
                raise BuildError(exc.code, exc.message, feature.id, exc.hint,
                                 blocked=tuple(f.id for f in enabled[index + 1:])) from exc
            if kind_spec.accepts and not isinstance(value, kind_spec.accepts):
                expected = ", ".join(item.__name__ for item in kind_spec.accepts)
                raise BuildError(
                    "INVALID_REF_TYPE",
                    f"{feature.id}.{role} resolved to {type(value).__name__}, "
                    f"expected {expected}",
                    feature.id,
                )
            inputs[role] = value
            input_keys.append(_ref_key(ref, fingerprints[ref.source]))

        key = _feature_key(feature, params, input_keys)
        entry = cache.get(key)
        cached = entry is not None
        if entry is None:
            started_feature = time.perf_counter()
            try:
                output = spec.build(inputs, params)
            except Exception as exc:  # kernel failures are normal outcomes
                raise BuildError(
                    "BUILD_FAILED",
                    f"{feature.id} ({feature.type}) failed",
                    feature.id,
                    hint=S.error_text(exc),
                    blocked=tuple(f.id for f in enabled[index + 1:]),
                ) from exc
            checks = tuple(spec.check(output.value, params, inputs))
            cache.put(key, (output, checks))
            seconds = time.perf_counter() - started_feature
        else:
            output, checks = entry
            seconds = 0.0
            hits += 1

        outputs[feature.id] = output.value
        fingerprints[feature.id] = key
        if "tag" in output.meta:
            tags[feature.id] = dict(output.meta["tag"])
        results.append(FeatureResult(feature.id, checks, seconds, cached, dict(output.meta)))

        failed = tuple(check for check in checks if not check.ok)
        if failed:
            hint = next((check.hint for check in failed if check.hint), None)
            raise BuildError(
                "CHECK_FAILED",
                f"{feature.id} ({feature.type}) failed: {failed[0].name}",
                feature.id,
                hint=hint,
                checks=failed,
                blocked=tuple(f.id for f in enabled[index + 1:]),
            )

    final = outputs[enabled[-1].id] if enabled else None
    return BuildResult(
        document_version=document.version,
        outputs=outputs,
        final=final,
        features=results,
        tags=tags,
        seconds=time.perf_counter() - started,
        cache_hits=hits,
    )
