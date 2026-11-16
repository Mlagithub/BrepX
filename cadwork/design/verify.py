"""Evaluate a plan's expectations against already-built geometry.

``evaluate`` is intentionally independent of the build engine: the caller
passes the value for the current node plus a context containing all outputs.
That keeps local checks cheap and makes the module usable by both the document
build loop and the plan backend.

All measurement happens here, but no geometry is *created*.  Unsupported
metrics and operators are rejected by ``plan.validate_expect`` before a build
starts; a metric that cannot be measured on a particular value becomes a
failed :class:`CheckResult` rather than an exception.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from .checks import CheckResult
from .plan import Expect, PlanError, validate_expect

METRICS = frozenset(
    {
        "volume",
        "area",
        "faces",
        "edges",
        "solids",
        "watertight",
        "bbox_size",
        "bbox_min",
        "bbox_max",
        "distance",
        "intersects",
    }
)
OPS = frozenset({"ge", "le", "between", "eq", "true"})
VECTOR_METRICS = frozenset({"bbox_size", "bbox_min", "bbox_max"})


@dataclass(frozen=True)
class VerifyContext:
    """The minimum context ``evaluate`` needs."""

    outputs: Mapping[str, Any] = field(default_factory=dict)
    plan: Any = None
    document: Any = None


class _MetricError(Exception):
    """A metric cannot be measured on this value."""


def _context_parts(context: Any) -> tuple[Mapping[str, Any], Any, Any]:
    if context is None:
        return {}, None, None
    if isinstance(context, Mapping):
        if "outputs" in context:
            outputs = context.get("outputs") or {}
        else:
            # Convenient for direct tests: a bare outputs mapping is allowed.
            outputs = context
        return outputs, context.get("plan"), context.get("document")
    outputs = getattr(context, "outputs", {}) or {}
    return outputs, getattr(context, "plan", None), getattr(context, "document", None)


def _unwrap(value: Any) -> Any:
    """Accept either a raw kernel value or a FeatureOutput-like wrapper."""
    if type(value).__name__ == "FeatureOutput" and hasattr(value, "value"):
        return value.value
    return value


def _is_sequence(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes))


def _number(value: Any) -> float:
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise _MetricError(f"{type(value).__name__} is not numeric") from exc


def _pair(value: Any) -> tuple[Any, Any]:
    if not _is_sequence(value) or len(value) != 2:
        raise _MetricError("between expects a (low, high) pair")
    return value[0], value[1]


def _vec3(value: Any) -> tuple[float, float, float]:
    if isinstance(value, Mapping):
        if {"x", "y", "z"} <= set(value):
            return (_number(value["x"]), _number(value["y"]), _number(value["z"]))
        raise _MetricError("vector object needs x, y and z")
    if hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z"):
        return (_number(value.x), _number(value.y), _number(value.z))
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        value = tolist()
    if _is_sequence(value) and len(value) >= 3:
        return (_number(value[0]), _number(value[1]), _number(value[2]))
    try:
        return (_number(value[0]), _number(value[1]), _number(value[2]))
    except (TypeError, IndexError) as exc:
        raise _MetricError(f"{type(value).__name__} is not a 3-vector") from exc


def _plain(value: Any) -> Any:
    """A JSON-friendly projection used only for display/observed payloads."""
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    return value


def _attr(value: Any, name: str) -> Any:
    attr = getattr(value, name, None)
    if attr is None:
        raise _MetricError(f"{type(value).__name__} has no {name!r}")
    return attr() if callable(attr) else attr


def _items(value: Any, name: str) -> Any:
    attr = getattr(value, name, None)
    if attr is None:
        raise _MetricError(f"{type(value).__name__} has no {name!r}")
    return attr() if callable(attr) else attr


def _count(value: Any, name: str) -> int:
    items = _items(value, name)
    if isinstance(items, bool):
        raise _MetricError(f"{name} is a boolean, not a collection")
    if isinstance(items, int):
        return items
    try:
        return len(items)
    except TypeError:
        try:
            return len(list(items))
        except TypeError as exc:
            raise _MetricError(f"{name} is not countable") from exc


def _area(value: Any) -> float:
    attr = getattr(value, "area", None)
    if attr is not None:
        return _number(attr() if callable(attr) else attr)
    faces = _items(value, "faces")
    try:
        iterator = iter(faces)
    except TypeError as exc:
        raise _MetricError("faces is not iterable, so area cannot be summed") from exc
    total = 0.0
    for face in iterator:
        total += _number(_attr(face, "area"))
    return total


def _watertight(value: Any) -> bool:
    for name in ("is_watertight", "watertight"):
        attr = getattr(value, name, None)
        if attr is not None:
            return bool(attr() if callable(attr) else attr)
    mesh_attr = getattr(value, "mesh", None)
    if mesh_attr is not None:
        mesh = mesh_attr() if callable(mesh_attr) else mesh_attr
        for name in ("is_closed", "closed"):
            attr = getattr(mesh, name, None)
            if attr is not None:
                return bool(attr() if callable(attr) else attr)
    attr = getattr(value, "is_closed", None)
    if attr is not None:
        return bool(attr() if callable(attr) else attr)
    raise _MetricError(f"{type(value).__name__} cannot report watertightness")


def _bbox(value: Any) -> tuple[tuple[float, float, float], ...]:
    attr = getattr(value, "bbox", None)
    if attr is None:
        raise _MetricError(f"{type(value).__name__} has no bbox()")
    box = attr() if callable(attr) else attr
    if box is None:
        raise _MetricError("bbox() returned None")
    if isinstance(box, Mapping):
        minimum = box.get("min")
        maximum = box.get("max")
        size = box.get("size")
    else:
        minimum = getattr(box, "min", None)
        maximum = getattr(box, "max", None)
        size = getattr(box, "size", None)
    minimum = minimum() if callable(minimum) else minimum
    maximum = maximum() if callable(maximum) else maximum
    size = size() if callable(size) else size
    if minimum is not None and maximum is not None:
        low, high = _vec3(minimum), _vec3(maximum)
        if size is None:
            size_vec = tuple(high[index] - low[index] for index in range(3))
        else:
            size_vec = _vec3(size)
        return low, high, size_vec
    if _is_sequence(box) and len(box) == 2:
        low, high = _vec3(box[0]), _vec3(box[1])
        return low, high, tuple(high[index] - low[index] for index in range(3))
    raise _MetricError("bbox() did not expose min, max and size")


def _resolve_lazily(ref: Any, outputs: Mapping[str, Any]) -> Any:
    """Resolve through ``refs.resolve``, or a local reader when it is unavailable."""
    try:
        from .refs import resolve  # type: ignore[attr-defined]
    except Exception:
        resolve = None
    if callable(resolve):
        return resolve(ref, outputs)
    return _local_resolve(ref, outputs)


def _local_resolve(ref: Any, outputs: Mapping[str, Any]) -> Any:
    source = getattr(ref, "source", None)
    if source not in outputs:
        raise _MetricError(f"source {source!r} has no output yet")
    target = outputs[source]
    select = getattr(ref, "select", "faces")
    if select == "self":
        return target
    accessor = getattr(target, select, None)
    if not callable(accessor):
        raise _MetricError(f"output has no {select}()")
    items = accessor()
    for item in getattr(ref, "filters", ()) or ():
        method = getattr(items, item.method, None)
        if not callable(method):
            raise _MetricError(f"{item.method} is not available on this value")
        args = list(getattr(item, "args", ()) or ())
        kwargs = {key: value for key, value in (getattr(item, "kwargs", ()) or ())}
        items = method(*args, **kwargs)
    return items


def _variable(node_id: str) -> str:
    import re

    return "n" + re.sub(r"[^A-Za-z0-9_]", "_", str(node_id))


def _aliases(ref: Any, plan: Any) -> list[str]:
    source = getattr(ref, "source", None)
    aliases: list[str] = []
    if isinstance(source, str):
        aliases.append(source)
    if plan is not None:
        for node in getattr(plan, "nodes", ()) or ():
            node_id = getattr(node, "id", None)
            feature_id = getattr(node, "feature_id", None)
            if node_id == source:
                if feature_id:
                    aliases.append(str(feature_id))
                aliases.append(_variable(str(node_id)))
            elif feature_id == source:
                aliases.append(str(node_id))
                aliases.append(_variable(str(node_id)))
    # Preserve order while removing duplicates.
    return list(dict.fromkeys(item for item in aliases if item))


def _resolve_expect_ref(ref: Any, outputs: Mapping[str, Any], plan: Any) -> Any:
    for alias in _aliases(ref, plan):
        if alias in outputs:
            if alias == getattr(ref, "source", None):
                return _resolve_lazily(ref, outputs)
            try:
                translated = replace(ref, source=alias)
            except TypeError:
                translated = ref
            return _resolve_lazily(translated, outputs)
    # No alias matched: delegate so the normal RefError carries the message.
    return _resolve_lazily(ref, outputs)


def _distance(one: Any, other: Any) -> float:
    one, other = _unwrap(one), _unwrap(other)
    if _is_sequence(other):
        if not other:
            raise _MetricError("cannot measure distance to an empty selection")
        return min(_distance(one, item) for item in other)
    if _is_sequence(one):
        if not one:
            raise _MetricError("cannot measure distance from an empty selection")
        return min(_distance(item, other) for item in one)

    for target in (one, other):
        for name in ("distance", "distance_to"):
            method = getattr(target, name, None)
            if method is not None:
                value = (
                    method(other if target is one else one)
                    if callable(method)
                    else method
                )
                return _number(value)
    try:
        from cadwork import smlib as S

        for name in ("distance", "distance_between"):
            method = getattr(S, name, None)
            if callable(method):
                return _number(method(one, other))
    except Exception:
        pass
    raise _MetricError(
        f"distance is unavailable between {type(one).__name__} and {type(other).__name__}"
    )


def _intersects(one: Any, other: Any) -> bool:
    one, other = _unwrap(one), _unwrap(other)
    if _is_sequence(other):
        return any(_intersects(one, item) for item in other)
    if _is_sequence(one):
        return any(_intersects(item, other) for item in one)

    for target in (one, other):
        for name in ("intersects", "intersects_with", "touches"):
            method = getattr(target, name, None)
            if method is not None:
                return (
                    bool(method(other if target is one else one))
                    if callable(method)
                    else bool(method)
                )
    # A curve list is itself the observable: any curve means the shapes meet.
    # An empty list means "no boundary contact", not necessarily "no overlap"
    # (one solid can contain another), so fall through to the volume test.
    for target in (one, other):
        method = getattr(target, "intersection_curves", None)
        if callable(method):
            try:
                result = method(other if target is one else one)
            except Exception:
                continue
            try:
                if len(result) > 0:
                    return True
            except TypeError:
                if result:
                    return True
    # The kernel expresses a volumetric intersection as a boolean operation
    # returning a shape, so a non-empty result is the observable.
    for target in (one, other):
        method = getattr(target, "intersect", None)
        if callable(method):
            try:
                result = method(other if target is one else one)
            except Exception:
                continue
            if isinstance(result, bool):
                return result
            if result is None:
                return False
            volume = getattr(result, "volume", None)
            if volume is not None:
                try:
                    if float(volume) > 1e-12:
                        return True
                except (TypeError, ValueError):
                    pass
            faces = getattr(result, "faces", None)
            if callable(faces):
                try:
                    return len(faces()) > 0
                except Exception:
                    pass
            try:
                return bool(result)
            except Exception:
                pass
    try:
        from cadwork import smlib as S

        for name in ("intersects", "intersect_shapes"):
            method = getattr(S, name, None)
            if callable(method):
                return bool(method(one, other))
    except Exception:
        pass
    raise _MetricError(
        f"intersects is unavailable between {type(one).__name__} and {type(other).__name__}"
    )


def _measure(
    metric: str, value: Any, expect: Expect, outputs: Mapping[str, Any], plan: Any
) -> Any:
    value = _unwrap(value)
    if metric == "volume":
        return _number(_attr(value, "volume"))
    if metric == "area":
        return _area(value)
    if metric == "faces":
        return _count(value, "faces")
    if metric == "edges":
        return _count(value, "edges")
    if metric == "solids":
        return _count(value, "solids")
    if metric == "watertight":
        return _watertight(value)
    if metric in VECTOR_METRICS:
        low, high, size = _bbox(value)
        if metric == "bbox_size":
            return size
        if metric == "bbox_min":
            return low
        return high
    if metric == "distance":
        other = _resolve_expect_ref(expect.ref, outputs, plan)
        return _distance(value, other)
    if metric == "intersects":
        other = _resolve_expect_ref(expect.ref, outputs, plan)
        return _intersects(value, other)
    # validate_expect normally catches this; keep a precise guard for direct use.
    raise PlanError(
        "PLAN_INVALID",
        f"unknown expectation metric {metric!r}",
        hint=f"known metrics: {', '.join(sorted(METRICS))}",
    )


def _compare_scalar(observed: Any, expected: Any, op: str, tolerance: float) -> bool:
    if isinstance(observed, bool):
        if op == "eq":
            if isinstance(expected, str):
                expected = expected.strip().lower() in {"true", "1", "yes"}
            return bool(observed) == bool(expected)
        observed = int(observed)
        expected = int(bool(expected)) if isinstance(expected, bool) else expected

    if op == "between":
        low, high = _pair(expected)
        number = _number(observed)
        return _number(low) - tolerance <= number <= _number(high) + tolerance

    number = _number(observed)
    target = _number(expected)
    if op == "ge":
        return number >= target - tolerance
    if op == "le":
        return number <= target + tolerance
    if op == "eq":
        return abs(number - target) <= tolerance
    raise PlanError("PLAN_INVALID", f"unknown expectation op {op!r}")


def _compare_vector(observed: Any, expected: Any, op: str, tolerance: float) -> bool:
    actual = _vec3(observed)
    if op == "between":
        low, high = _pair(expected)
        lower, upper = _vec3(low), _vec3(high)
        return all(
            lower[index] - tolerance <= actual[index] <= upper[index] + tolerance
            for index in range(3)
        )
    target = _vec3(expected)
    if op == "ge":
        return all(actual[index] >= target[index] - tolerance for index in range(3))
    if op == "le":
        return all(actual[index] <= target[index] + tolerance for index in range(3))
    if op == "eq":
        return all(
            abs(actual[index] - target[index]) <= tolerance for index in range(3)
        )
    raise PlanError("PLAN_INVALID", f"unknown expectation op {op!r}")


def _compare(
    metric: str, op: str, observed: Any, expected: Any, tolerance: float
) -> bool:
    if op == "true":
        return bool(observed)
    if metric in VECTOR_METRICS:
        return _compare_vector(observed, expected, op, tolerance)
    return _compare_scalar(observed, expected, op, tolerance)


def _expected_text(expect: Expect) -> str:
    metric = expect.metric
    op = expect.op
    tolerance = float(expect.tolerance)
    if op == "true":
        return f"{metric} must be true"
    if op == "between":
        return f"{metric} between {_plain(expect.value)} (tolerance {tolerance:g})"
    text = f"{metric} {op} {_plain(expect.value)} (tolerance {tolerance:g})"
    if metric in {"distance", "intersects"} and expect.ref is not None:
        text += f" against {expect.ref.source!r}"
    return text


def _observed_payload(
    metric: str, op: str, expect: Expect, observed: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "metric": metric,
        "observed": _plain(observed),
        "op": op,
        "expected": _plain(expect.value),
        "tolerance": float(expect.tolerance),
    }
    if metric not in payload:
        payload[metric] = _plain(observed)
    if metric in {"distance", "intersects"} and expect.ref is not None:
        payload["ref"] = expect.ref.source
    return payload


def evaluate(
    expects: Iterable[Expect] | Expect | None, value: Any, context: Any | None = None
) -> list[CheckResult]:
    """Evaluate expectations against ``value``.

    ``context`` may be a :class:`VerifyContext`, an object with ``outputs``,
    ``plan`` and ``document`` attributes, or a mapping of those keys.  The
    return value is a list of :class:`cadwork.design.checks.CheckResult`, one
    per expectation, in input order.
    """
    if expects is None:
        return []
    if isinstance(expects, Expect):
        expects = (expects,)

    outputs, plan, _document = _context_parts(context)
    _ = _document
    results: list[CheckResult] = []
    for expect in expects:
        # Structural problems (unknown metric/op) are plan errors, not check
        # failures, so they are raised before measurement.
        validate_expect(expect)
        text = _expected_text(expect)
        try:
            observed = _measure(expect.metric, value, expect, outputs, plan)
            ok = _compare(
                expect.metric,
                expect.op,
                observed,
                expect.value,
                float(expect.tolerance),
            )
        except Exception as exc:
            results.append(
                CheckResult(
                    name=expect.metric,
                    ok=False,
                    observed={"metric": expect.metric, "error": str(exc)},
                    expected=text,
                    hint=str(exc),
                )
            )
            continue
        results.append(
            CheckResult(
                name=expect.metric,
                ok=bool(ok),
                observed=_observed_payload(expect.metric, expect.op, expect, observed),
                expected=text,
                hint=None if ok else text,
            )
        )
    return results


__all__ = [
    "METRICS",
    "OPS",
    "VECTOR_METRICS",
    "CheckResult",
    "VerifyContext",
    "evaluate",
]
