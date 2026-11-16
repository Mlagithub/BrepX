"""The modeling plan: a small, ordered DAG the LLM proposes before geometry.

A plan is deliberately data-only.  It records intent (a goal), the feature
steps that should materialise it, and the checks that decide whether the
result is acceptable.  Nothing in this module executes geometry or touches a
document; :mod:`cadwork.design.plan_compile` lowers a plan to document ops or
to the backend IR, and :mod:`cadwork.design.verify` evaluates its expectations.

Structural rules enforced by :func:`validate_plan`:

* node ids are unique and match ``^[A-Za-z][A-Za-z0-9_]{0,31}$``;
* every dependency names an earlier node, so the graph is acyclic;
* every reference source names an earlier *feature* node in this plan.  A plan
  stays self-contained even when it is validated against an existing document,
  so a missing source is always a plan error rather than a deferred document
  lookup;
* a goal carries no action and no expectation;
* a feature carries an action;
* a check carries exactly one dependency, no action, and at least one
  expectation.

``new_plan`` starts at ``revision=1``.  Helpers are pure: ``with_node`` and
``with_revision`` return a new plan and never mutate the input.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from . import document as _document
from .document import Filter, Ref

_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
_KINDS = frozenset({"goal", "feature", "check"})
_DEFAULT_STATUS = "draft"


class PlanError(Exception):
    """A plan is structurally impossible; the plan is unchanged."""

    def __init__(self, code: str, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "hint": self.hint}


@dataclass(frozen=True)
class Expect:
    """One assertion about a built output."""

    metric: str
    op: str
    value: Any = None
    tolerance: float = 1e-6
    ref: Ref | None = None

    def __post_init__(self) -> None:
        # A between bound is a pair.  Keeping it as a tuple makes the dataclass
        # value survive a JSON round trip (JSON decodes lists, not tuples).
        if self.op == "between" and isinstance(self.value, (list, tuple)):
            object.__setattr__(self, "value", tuple(self.value))

    def to_json(self) -> dict[str, Any]:
        return expect_to_json(self)

    @classmethod
    def from_json(cls, payload: Mapping[str, Any] | str) -> Expect:
        return expect_from_json(payload)


@dataclass(frozen=True)
class PlanNode:
    """One node of the plan DAG."""

    id: str
    kind: str
    title: str
    action: str | None = None
    params: Mapping[str, Any] = field(default_factory=dict)
    refs: Mapping[str, Ref | tuple[Ref, ...]] = field(default_factory=dict)
    deps: tuple[str, ...] = ()
    expect: tuple[Expect, ...] = ()
    feature_id: str | None = None
    note: str = ""
    status: str = "pending"
    milestone_version: int | None = None
    observed: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "params", dict(self.params))
        normalized: dict[str, Ref | tuple[Ref, ...]] = {}
        for role, value in dict(self.refs).items():
            if isinstance(value, (list, tuple)):
                normalized[str(role)] = tuple(value)
            else:
                normalized[str(role)] = value
        object.__setattr__(self, "refs", normalized)
        object.__setattr__(self, "deps", tuple(self.deps))
        object.__setattr__(self, "expect", tuple(self.expect))
        object.__setattr__(self, "observed", dict(self.observed))

    def to_json(self) -> dict[str, Any]:
        return plan_node_to_json(self)

    @classmethod
    def from_json(cls, payload: Mapping[str, Any] | str) -> PlanNode:
        return plan_node_from_json(payload)


@dataclass(frozen=True)
class ModelingPlan:
    """An ordered plan against one document version."""

    id: str
    document_id: str
    goal: str
    base_version: int
    revision: int
    nodes: tuple[PlanNode, ...]
    status: str = _DEFAULT_STATUS
    created: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))

    def to_json(self) -> dict[str, Any]:
        return plan_to_json(self)

    @classmethod
    def from_json(
        cls, payload: Mapping[str, Any] | str, *, validate: bool = False
    ) -> ModelingPlan:
        plan = plan_from_json(payload)
        if validate:
            validate_plan(plan)
        return plan

    def with_node(self, node: PlanNode) -> ModelingPlan:
        return with_node(self, node)

    def with_revision(self, revision: int | None = None) -> ModelingPlan:
        return with_revision(self, revision)

    def next_node_id(self, prefix: str = "n") -> str:
        return next_node_id(self, prefix)

    def validate(self, document: Any | None = None) -> None:
        validate_plan(self, document)


def new_plan(
    document_id: str, goal: str, base_version: int, nodes: Iterable[PlanNode] = ()
) -> ModelingPlan:
    """Create a fresh draft revision of a plan."""
    return ModelingPlan(
        id=f"p_{uuid.uuid4().hex[:10]}",
        document_id=str(document_id),
        goal=str(goal),
        base_version=int(base_version),
        revision=1,
        nodes=tuple(nodes),
        status=_DEFAULT_STATUS,
        created=time.time(),
    )


def with_node(plan: ModelingPlan, node: PlanNode) -> ModelingPlan:
    """Append ``node``, or replace the node with the same id in place."""
    nodes = list(plan.nodes)
    for index, current in enumerate(nodes):
        if current.id == node.id:
            nodes[index] = node
            break
    else:
        nodes.append(node)
    return replace(plan, nodes=tuple(nodes))


def with_revision(plan: ModelingPlan, revision: int | None = None) -> ModelingPlan:
    """Return the plan at an explicit revision, or the next revision."""
    return replace(
        plan, revision=plan.revision + 1 if revision is None else int(revision)
    )


def next_node_id(
    plan: ModelingPlan | Iterable[PlanNode] | None = None, prefix: str = "n"
) -> str:
    """Return the first unused ``<prefix><number>`` id."""
    if plan is None:
        nodes: Iterable[Any] = ()
    elif isinstance(plan, ModelingPlan):
        nodes = plan.nodes
    else:
        nodes = plan
    used = {getattr(node, "id", node) for node in nodes}
    if isinstance(plan, ModelingPlan):
        used.update(
            node.feature_id for node in plan.nodes if node.feature_id is not None
        )
    index = 1
    while f"{prefix}{index}" in used:
        index += 1
    return f"{prefix}{index}"


def validate_expect(expect: Expect) -> None:
    """Validate one expectation without evaluating it.

    Metric and op names are checked here so an unsupported plan is rejected
    before a build starts.  The lazy import keeps ``plan`` and ``verify`` from
    forming an import cycle.
    """
    from .verify import METRICS, OPS

    if not isinstance(expect, Expect):
        raise PlanError(
            "PLAN_INVALID",
            f"expectation must be an Expect, got {type(expect).__name__}",
        )
    if not isinstance(expect.metric, str) or expect.metric not in METRICS:
        raise PlanError(
            "PLAN_INVALID",
            f"unknown expectation metric {expect.metric!r}",
            hint=f"known metrics: {', '.join(sorted(METRICS))}",
        )
    if not isinstance(expect.op, str) or expect.op not in OPS:
        raise PlanError(
            "PLAN_INVALID",
            f"unknown expectation op {expect.op!r}",
            hint=f"known ops: {', '.join(sorted(OPS))}",
        )
    if isinstance(expect.tolerance, bool) or not isinstance(
        expect.tolerance, (int, float)
    ):
        raise PlanError("PLAN_INVALID", "expectation tolerance must be a number")
    if float(expect.tolerance) < 0.0:
        raise PlanError("PLAN_INVALID", "expectation tolerance cannot be negative")

    if expect.op == "between":
        if not isinstance(expect.value, (list, tuple)) or len(expect.value) != 2:
            raise PlanError(
                "PLAN_INVALID",
                f"{expect.metric} between expects a (low, high) pair",
                hint="for example Expect('volume', 'between', (10.0, 20.0))",
            )
    elif expect.op != "true" and expect.value is None:
        raise PlanError(
            "PLAN_INVALID",
            f"{expect.metric} {expect.op} requires a value",
        )

    if expect.metric in {"distance", "intersects"}:
        if expect.ref is None or not getattr(expect.ref, "source", None):
            raise PlanError(
                "PLAN_INVALID",
                f"{expect.metric} requires expect.ref naming another output",
                hint="for example Expect('distance', 'le', 1.0, ref=Ref('f1', 'self'))",
            )


def _iter_refs(node: PlanNode) -> Iterable[tuple[str, Any]]:
    for role, value in node.refs.items():
        if isinstance(value, (tuple, list)):
            for ref in value:
                yield str(role), ref
        else:
            yield str(role), value


def _check_acyclic(nodes: tuple[PlanNode, ...]) -> None:
    graph = {node.id: tuple(node.deps) for node in nodes}
    state: dict[str, int] = {}

    def visit(node_id: str, trail: list[str]) -> None:
        status = state.get(node_id, 0)
        if status == 2:
            return
        if status == 1:
            cycle = " -> ".join(trail + [node_id])
            raise PlanError(
                "PLAN_INVALID", f"plan contains a dependency cycle: {cycle}"
            )
        state[node_id] = 1
        for dep in graph.get(node_id, ()):
            if dep in graph:
                visit(dep, trail + [node_id])
        state[node_id] = 2

    for node_id in graph:
        visit(node_id, [])


def validate_plan(plan: ModelingPlan, document: Any | None = None) -> None:
    """Raise :class:`PlanError` unless the plan is structurally valid.

    ``document`` is accepted so callers can validate against the document they
    intend to compile against, but the plan is intentionally self-contained:
    reference sources must be feature nodes in this plan even when a document
    is supplied.  This makes a submitted plan checkable before any replay.
    """
    del (
        document
    )  # self-contained: reference sources are validated against plan features only

    if not isinstance(plan, ModelingPlan):
        raise PlanError(
            "PLAN_INVALID", f"expected a ModelingPlan, got {type(plan).__name__}"
        )
    if not isinstance(plan.id, str) or not plan.id.strip():
        raise PlanError("PLAN_INVALID", "plan id must be a non-empty string")
    if not isinstance(plan.document_id, str) or not plan.document_id.strip():
        raise PlanError("PLAN_INVALID", "plan document_id must be a non-empty string")
    if isinstance(plan.base_version, bool) or not isinstance(plan.base_version, int):
        raise PlanError("PLAN_INVALID", "plan base_version must be an integer")
    if isinstance(plan.revision, bool) or not isinstance(plan.revision, int):
        raise PlanError("PLAN_INVALID", "plan revision must be an integer")

    seen: set[str] = set()
    seen_features: set[str] = set()

    for node in plan.nodes:
        if not isinstance(node, PlanNode):
            raise PlanError(
                "PLAN_INVALID",
                f"plan node must be a PlanNode, got {type(node).__name__}",
            )
        if not isinstance(node.id, str) or not _ID.fullmatch(node.id):
            raise PlanError(
                "PLAN_INVALID",
                f"invalid node id {node.id!r}",
                hint="ids must match ^[A-Za-z][A-Za-z0-9_]{0,31}$",
            )
        if node.id in seen:
            raise PlanError("NODE_ID_CONFLICT", f"duplicate node id {node.id!r}")
        if not isinstance(node.kind, str) or node.kind not in _KINDS:
            raise PlanError(
                "PLAN_INVALID",
                f"node {node.id!r} has unknown kind {node.kind!r}",
                hint="kind must be goal, feature or check",
            )
        if node.feature_id is not None and not _ID.fullmatch(str(node.feature_id)):
            raise PlanError(
                "PLAN_INVALID",
                f"node {node.id!r} has invalid feature_id {node.feature_id!r}",
            )

        for dep in node.deps:
            if not isinstance(dep, str) or dep not in seen:
                raise PlanError(
                    "PLAN_INVALID",
                    f"node {node.id!r} depends on {dep!r}, which is not an earlier node",
                    hint="dependencies must name a node listed before this one",
                )
        for role, ref in _iter_refs(node):
            source = getattr(ref, "source", None)
            if not isinstance(source, str) or source not in seen_features:
                raise PlanError(
                    "PLAN_INVALID",
                    f"node {node.id!r} ref {role!r} points at {source!r}, "
                    "which is not an earlier feature node",
                    hint="reference sources must name an earlier feature node in this plan",
                )

        if node.kind == "goal":
            if node.action:
                raise PlanError(
                    "PLAN_INVALID", f"goal node {node.id!r} cannot have an action"
                )
            if node.expect:
                raise PlanError(
                    "PLAN_INVALID", f"goal node {node.id!r} cannot have expectations"
                )
        elif node.kind == "feature":
            if not isinstance(node.action, str) or not node.action.strip():
                raise PlanError(
                    "PLAN_INVALID", f"feature node {node.id!r} requires an action"
                )
        elif node.kind == "check":
            if len(node.deps) != 1:
                raise PlanError(
                    "PLAN_INVALID",
                    f"check node {node.id!r} requires exactly 1 dependency, got {len(node.deps)}",
                )
            if node.action:
                raise PlanError(
                    "PLAN_INVALID", f"check node {node.id!r} cannot have an action"
                )
            if not node.expect:
                raise PlanError(
                    "PLAN_INVALID",
                    f"check node {node.id!r} requires at least one expectation",
                )

        for expect in node.expect:
            validate_expect(expect)

        seen.add(node.id)
        if node.kind == "feature":
            seen_features.add(node.id)

    _check_acyclic(tuple(plan.nodes))


def _filter_to_json(value: Filter) -> dict[str, Any]:
    helper = getattr(_document, "filter_to_json", None)
    if callable(helper):
        return helper(value)
    return {
        "method": value.method,
        "args": list(value.args),
        "kwargs": {key: item for key, item in value.kwargs},
    }


def _filter_from_json(payload: Mapping[str, Any]) -> Filter:
    helper = getattr(_document, "filter_from_json", None)
    if callable(helper):
        return helper(payload)
    return Filter(
        method=str(payload.get("method", "")),
        args=tuple(payload.get("args") or ()),
        kwargs=tuple(sorted(dict(payload.get("kwargs") or {}).items())),
    )


def ref_to_json(ref: Ref) -> dict[str, Any]:
    """Serialize a document reference including ``since`` and ``extra``."""
    payload: dict[str, Any] = {
        "source": ref.source,
        "select": ref.select,
        "filters": [_filter_to_json(item) for item in getattr(ref, "filters", ())],
    }
    # ``since`` and ``extra`` are always present: ``document.ref_to_json`` emits
    # them even when empty, so omitting them here would give the two serializers
    # different shapes.
    for name in ("since", "extra"):
        payload[name] = list(getattr(ref, name, ()) or ())
    return payload


def ref_from_json(payload: Mapping[str, Any] | None) -> Ref:
    """Parse a reference produced by :func:`ref_to_json`."""
    if not isinstance(payload, Mapping):
        raise PlanError("PLAN_INVALID", "ref payload must be an object")
    kwargs: dict[str, Any] = {
        "source": str(payload.get("source", "")),
        "select": str(payload.get("select", "faces")),
        "filters": tuple(
            _filter_from_json(item) for item in payload.get("filters") or ()
        ),
    }
    for name in ("since", "extra"):
        if name in payload:
            kwargs[name] = tuple(str(item) for item in payload.get(name) or ())
    try:
        return Ref(**kwargs)
    except TypeError:
        # Fall back for a Ref without ``since``/``extra`` fields.
        kwargs.pop("since", None)
        kwargs.pop("extra", None)
        try:
            return Ref(**kwargs)
        except Exception as exc:  # pragma: no cover - defensive
            raise PlanError("PLAN_INVALID", f"invalid ref: {exc}") from exc
    except Exception as exc:
        raise PlanError("PLAN_INVALID", f"invalid ref: {exc}") from exc


def expect_to_json(expect: Expect) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "metric": expect.metric,
        "op": expect.op,
        "value": expect.value,
        "tolerance": expect.tolerance,
    }
    if expect.ref is not None:
        payload["ref"] = ref_to_json(expect.ref)
    return payload


def expect_from_json(payload: Mapping[str, Any] | str) -> Expect:
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, Mapping):
        raise PlanError("PLAN_INVALID", "expect payload must be an object")
    op = str(payload.get("op", ""))
    value = payload.get("value")
    if op == "between" and isinstance(value, list):
        value = tuple(value)
    ref_payload = payload.get("ref")
    return Expect(
        metric=str(payload.get("metric", "")),
        op=op,
        value=value,
        tolerance=float(payload.get("tolerance", 1e-6)),
        ref=ref_from_json(ref_payload) if ref_payload is not None else None,
    )


def _refs_to_json(refs: Mapping[str, Ref | tuple[Ref, ...]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for role, value in refs.items():
        if isinstance(value, (tuple, list)):
            output[str(role)] = [ref_to_json(ref) for ref in value]
        else:
            output[str(role)] = ref_to_json(value)
    return output


def _refs_from_json(
    payload: Mapping[str, Any] | None,
) -> dict[str, Ref | tuple[Ref, ...]]:
    output: dict[str, Ref | tuple[Ref, ...]] = {}
    for role, value in dict(payload or {}).items():
        if isinstance(value, list):
            output[str(role)] = tuple(ref_from_json(item) for item in value)
        else:
            output[str(role)] = ref_from_json(value)
    return output


def plan_node_to_json(node: PlanNode) -> dict[str, Any]:
    return {
        "id": node.id,
        "kind": node.kind,
        "title": node.title,
        "action": node.action,
        "params": dict(node.params),
        "refs": _refs_to_json(node.refs),
        "deps": list(node.deps),
        "expect": [expect_to_json(item) for item in node.expect],
        "feature_id": node.feature_id,
        "note": node.note,
        "status": node.status,
        "milestone_version": node.milestone_version,
        "observed": dict(node.observed),
        "error": node.error,
    }


def plan_node_from_json(payload: Mapping[str, Any] | str) -> PlanNode:
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, Mapping):
        raise PlanError("PLAN_INVALID", "node payload must be an object")
    milestone = payload.get("milestone_version")
    return PlanNode(
        id=str(payload.get("id", "")),
        kind=str(payload.get("kind", "")),
        title=str(payload.get("title", "")),
        action=payload.get("action"),
        params=dict(payload.get("params") or {}),
        refs=_refs_from_json(payload.get("refs")),
        deps=tuple(str(item) for item in payload.get("deps") or ()),
        expect=tuple(expect_from_json(item) for item in payload.get("expect") or ()),
        feature_id=payload.get("feature_id"),
        note=str(payload.get("note", "")),
        status=str(payload.get("status", "pending")),
        milestone_version=int(milestone) if milestone is not None else None,
        observed=dict(payload.get("observed") or {}),
        error=payload.get("error"),
    )


def plan_to_json(plan: ModelingPlan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "document_id": plan.document_id,
        "goal": plan.goal,
        "base_version": plan.base_version,
        "revision": plan.revision,
        "nodes": [plan_node_to_json(node) for node in plan.nodes],
        "status": plan.status,
        "created": plan.created,
    }


def plan_from_json(payload: Mapping[str, Any] | str) -> ModelingPlan:
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, Mapping):
        raise PlanError("PLAN_INVALID", "plan payload must be an object")
    return ModelingPlan(
        id=str(payload.get("id", "")),
        document_id=str(payload.get("document_id", "")),
        goal=str(payload.get("goal", "")),
        base_version=int(payload.get("base_version", 0)),
        revision=int(payload.get("revision", 0)),
        nodes=tuple(plan_node_from_json(item) for item in payload.get("nodes") or ()),
        status=str(payload.get("status", _DEFAULT_STATUS)),
        created=float(payload.get("created", 0.0) or 0.0),
    )


__all__ = [
    "Expect",
    "ModelingPlan",
    "PlanError",
    "PlanNode",
    "expect_from_json",
    "expect_to_json",
    "new_plan",
    "next_node_id",
    "plan_from_json",
    "plan_node_from_json",
    "plan_node_to_json",
    "plan_to_json",
    "ref_from_json",
    "ref_to_json",
    "validate_expect",
    "validate_plan",
    "with_node",
    "with_revision",
]
