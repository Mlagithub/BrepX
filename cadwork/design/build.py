"""Replay the feature list. Geometry is a cache of the document, not its state."""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from cadwork import smlib as S

from . import refs
from .checks import CheckResult
from .document import Document, Feature, canonical_json, filter_to_json
from .features import (
    INPUT_KINDS,
    FeatureError,
    FeatureOutput,
    InputRole,
    resolve_params,
    validate_feature,
)

CACHE_EPOCH = f"2026-11-12.1 smlibpy-{S.VERSION}"


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


@dataclass(frozen=True)
class BodyInfo:
    """One editable feature output, independent of the final fused shape."""

    feature_id: str
    feature_type: str
    params: Mapping[str, Any]
    inputs: tuple[str, ...]
    metrics: Mapping[str, Any]
    visible: bool = True
    is_final: bool = False

    def summary(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "feature_type": self.feature_type,
            "params": dict(self.params),
            "inputs": list(self.inputs),
            "metrics": dict(self.metrics),
            "visible": self.visible,
            "is_final": self.is_final,
        }


def _body_metrics(value: Any) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for name in ("volume", "area"):
        try:
            metrics[name] = float(getattr(value, name))
        except (AttributeError, TypeError, ValueError):
            continue
    for name in ("faces", "edges", "vertices"):
        try:
            metrics[name] = len(getattr(value, name)())
        except (AttributeError, TypeError):
            continue
    try:
        box = value.bbox()
        metrics["bbox_min"] = [float(item) for item in box.min]
        metrics["bbox_max"] = [float(item) for item in box.max]
        metrics["bbox_size"] = [float(item) for item in box.size]
    except (AttributeError, TypeError, ValueError):
        pass
    return metrics


def _body_inputs(feature: Feature) -> tuple[str, ...]:
    inputs: list[str] = []
    for value in feature.refs.values():
        items = value if isinstance(value, (list, tuple)) else (value,)
        for ref in items:
            for source in (ref.source, *ref.since, *ref.extra):
                if source not in inputs:
                    inputs.append(source)
    return tuple(inputs)


@dataclass
class BuildResult:
    document_version: int
    outputs: dict[str, Any]
    final: Any | None
    features: list[FeatureResult] = field(default_factory=list)
    tags: dict[str, dict[str, Any]] = field(default_factory=dict)
    seconds: float = 0.0
    cache_hits: int = 0
    configuration: str = "default"
    bodies: dict[str, BodyInfo] = field(default_factory=dict)
    final_feature_id: str | None = None

    def summary(self) -> dict[str, Any]:
        return {
            "version": self.document_version,
            "configuration": self.configuration,
            "features": [
                {
                    "id": item.feature_id,
                    "seconds": round(item.seconds, 4),
                    "cached": item.cached,
                    "checks": [c.__dict__ for c in item.checks],
                }
                for item in self.features
            ],
            "bodies": [self.bodies[key].summary() for key in sorted(self.bodies)],
            "tags": self.tags,
            "seconds": round(self.seconds, 4),
            "cache_hits": self.cache_hits,
        }


class BuildCache:
    """Content-addressed LRU. Deleting it only costs time, never correctness."""

    def __init__(self, capacity: int = 128) -> None:
        self.capacity = capacity
        self._data: OrderedDict[str, tuple[FeatureOutput, tuple[CheckResult, ...]]] = (
            OrderedDict()
        )

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
        "since": list(ref.since),
        "extra": list(ref.extra),
        "source_key": source_key,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _feature_key(
    feature: Feature,
    params: Mapping[str, Any],
    input_keys: list[str],
    configuration: str = "default",
) -> str:
    payload = {
        "epoch": CACHE_EPOCH,
        "configuration": configuration,
        "type": feature.type,
        "params": dict(params),
        "inputs": input_keys,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _configuration_overrides(
    document: Document, configuration: str | None
) -> tuple[str, Mapping[str, Mapping[str, Any]]]:
    name = configuration or "default"
    if name == "default":
        return name, {}
    overrides = document.configurations.get(name)
    if overrides is None:
        raise BuildError(
            "UNKNOWN_CONFIG",
            f"document has no configuration {name!r}",
            hint=f"known configurations: {', '.join(sorted(document.configurations)) or '(none)'}",
        )
    return name, overrides


def _parameter_overrides(
    document: Document, overrides: Mapping[str, Any] | None
) -> dict[str, dict[str, Any]]:
    """Translate public parameter names into feature-parameter updates."""
    if not overrides:
        return {}
    specs = {parameter.name: parameter for parameter in document.parameters}
    unknown = sorted(set(overrides) - set(specs))
    if unknown:
        raise BuildError(
            "UNKNOWN_OVERRIDE",
            f"document has no parameter {unknown[0]!r}",
            hint=f"known parameters: {', '.join(sorted(specs)) or '(none)'}",
        )
    result: dict[str, dict[str, Any]] = {}
    for name, value in overrides.items():
        spec = specs[name]
        if (
            spec.kind in {"float", "int"}
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        ):
            if spec.minimum is not None and value < spec.minimum:
                raise BuildError(
                    "INVALID_OVERRIDE", f"parameter {name!r} is below {spec.minimum}"
                )
            if spec.maximum is not None and value > spec.maximum:
                raise BuildError(
                    "INVALID_OVERRIDE", f"parameter {name!r} is above {spec.maximum}"
                )
        result.setdefault(spec.feature_id, {})[spec.param] = value
    return result


def _check_kind(feature: Feature, role: str, role_spec: InputRole, ref: Any) -> Any:
    spec = INPUT_KINDS.get(role_spec.kind)
    if spec is None:
        raise BuildError(
            "UNKNOWN_KIND",
            f"{feature.id}.{role} uses unknown input kind {role_spec.kind!r}",
            feature.id,
            hint=f"known kinds: {', '.join(sorted(INPUT_KINDS))}",
        )
    if ref.select not in spec.selects:
        expected = " or ".join(repr(select) for select in spec.selects)
        raise BuildError(
            "INVALID_REF_KIND",
            f"{feature.id}.{role} must use select={expected}, got {ref.select!r}",
            feature.id,
        )
    return spec


def build(
    document: Document,
    cache: BuildCache | None = None,
    configuration: str | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> BuildResult:
    cache = cache if cache is not None else _DEFAULT_CACHE
    config_name, configuration_overrides = _configuration_overrides(
        document, configuration
    )
    parameter_overrides = _parameter_overrides(document, overrides)
    merged_overrides: dict[str, dict[str, Any]] = {
        feature_id: dict(params)
        for feature_id, params in configuration_overrides.items()
    }
    for feature_id, params in parameter_overrides.items():
        merged_overrides.setdefault(feature_id, {}).update(params)
    overrides = merged_overrides
    enabled = [feature for feature in document.features if feature.enabled]
    outputs: dict[str, Any] = {}
    bodies: dict[str, BodyInfo] = {}
    fingerprints: dict[str, str] = {}
    results: list[FeatureResult] = []
    tags: dict[str, dict[str, Any]] = {}
    hits = 0
    started = time.perf_counter()

    for index, feature in enumerate(enabled):
        try:
            spec = validate_feature(feature.type, feature.refs)
            merged_params = dict(feature.params)
            merged_params.update(overrides.get(feature.id, {}))
            params = resolve_params(spec, merged_params)
        except FeatureError as exc:
            raise BuildError(
                exc.code,
                exc.message,
                feature.id,
                exc.hint,
                blocked=tuple(f.id for f in enabled[index + 1 :]),
            ) from exc

        inputs: dict[str, Any] = {}
        input_keys: list[str] = []
        for role_spec in spec.inputs:
            role = role_spec.role
            bound = feature.refs.get(role)
            if bound is None:
                if role_spec.optional:
                    inputs[role] = None
                    continue
                raise BuildError(
                    "INVALID_REFS",
                    f"{feature.id}.{role} is required",
                    feature.id,
                    hint=f"required roles: {', '.join(item.role for item in spec.inputs if not item.optional)}",
                )
            refs_here = tuple(bound) if isinstance(bound, (list, tuple)) else (bound,)
            if not role_spec.many and len(refs_here) != 1:
                raise BuildError(
                    "INVALID_REFS",
                    f"{feature.id}.{role} accepts exactly one ref, got {len(refs_here)}",
                    feature.id,
                )
            resolved: list[Any] = []
            for ref in refs_here:
                kind_spec = _check_kind(feature, role, role_spec, ref)
                try:
                    value = refs.resolve(ref, outputs)
                except refs.RefError as exc:
                    raise BuildError(
                        exc.code,
                        exc.message,
                        feature.id,
                        exc.hint,
                        blocked=tuple(f.id for f in enabled[index + 1 :]),
                    ) from exc
                if kind_spec.accepts and not isinstance(value, kind_spec.accepts):
                    expected = ", ".join(item.__name__ for item in kind_spec.accepts)
                    raise BuildError(
                        "INVALID_REF_TYPE",
                        f"{feature.id}.{role} resolved to {type(value).__name__}, "
                        f"expected {expected}",
                        feature.id,
                    )
                resolved.append(value)
                input_keys.append(_ref_key(ref, fingerprints[ref.source]))
            inputs[role] = tuple(resolved) if role_spec.many else resolved[0]

        key = _feature_key(feature, params, input_keys, config_name)
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
                    blocked=tuple(f.id for f in enabled[index + 1 :]),
                ) from exc
            checks = tuple(spec.check(output.value, params, inputs))
            cache.put(key, (output, checks))
            seconds = time.perf_counter() - started_feature
        else:
            output, checks = entry
            seconds = 0.0
            hits += 1

        outputs[feature.id] = output.value
        bodies[feature.id] = BodyInfo(
            feature_id=feature.id,
            feature_type=feature.type,
            params=dict(params),
            inputs=_body_inputs(feature),
            metrics=_body_metrics(output.value),
        )
        fingerprints[feature.id] = key
        if "tag" in output.meta:
            tags[feature.id] = dict(output.meta["tag"])
        results.append(
            FeatureResult(feature.id, checks, seconds, cached, dict(output.meta))
        )

        failed = tuple(check for check in checks if not check.ok)
        if failed:
            hint = next((check.hint for check in failed if check.hint), None)
            raise BuildError(
                "CHECK_FAILED",
                f"{feature.id} ({feature.type}) failed: {failed[0].name}",
                feature.id,
                hint=hint,
                checks=failed,
                blocked=tuple(f.id for f in enabled[index + 1 :]),
            )

    final_id = enabled[-1].id if enabled else None
    final = outputs[final_id] if final_id is not None else None
    if final_id is not None and final_id in bodies:
        current = bodies[final_id]
        bodies[final_id] = BodyInfo(
            feature_id=current.feature_id,
            feature_type=current.feature_type,
            params=current.params,
            inputs=current.inputs,
            metrics=current.metrics,
            visible=current.visible,
            is_final=True,
        )
    return BuildResult(
        document_version=document.version,
        outputs=outputs,
        final=final,
        features=results,
        tags=tags,
        seconds=time.perf_counter() - started,
        cache_hits=hits,
        configuration=config_name,
        bodies=bodies,
        final_feature_id=final_id,
    )
