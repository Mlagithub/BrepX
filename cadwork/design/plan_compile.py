"""Lower a :class:`~cadwork.design.plan.ModelingPlan` to executable data.

Two outputs are provided:

``compile_node``
    document ops (``add``/``update``) for one feature node.  This is what the
    document layer consumes.

``compile_program``
    a backend-neutral :class:`BuildProgram` of :class:`Step` objects.  Each
    feature node becomes one step; input roles point at earlier steps by their
    sanitized ``n<node.id>`` variable.  A step carries only the expectations of
    its own feature node; ``check`` nodes are evaluated separately by
    ``verify.evaluate`` against the dependency's built output.

No geometry is built here.  Actions and parameters are validated against the
feature registry, and references are translated from plan node ids to document
feature ids.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any, Mapping

from . import features as _features
from .document import Ref
from .plan import (
    Expect,
    ModelingPlan,
    PlanError,
    PlanNode,
    ref_to_json,
    validate_plan,
)

_VARIABLE_BAD = re.compile(r"[^A-Za-z0-9_]")


class CompileError(Exception):
    """A plan node cannot be lowered to a document op or a step."""

    def __init__(self, code: str, message: str, node_id: str | None = None,
                 hint: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.node_id = node_id
        self.hint = hint

    def to_json(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "node_id": self.node_id,
            "hint": self.hint,
        }


@dataclass(frozen=True)
class Step:
    node_id: str
    action: str
    variable: str
    inputs: Mapping[str, str | tuple[str, ...]]
    params: Mapping[str, Any]
    expect: tuple[Expect, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "action": self.action,
            "variable": self.variable,
            "inputs": {
                role: list(value) if isinstance(value, tuple) else value
                for role, value in self.inputs.items()
            },
            "params": dict(self.params),
            "expect": [item.to_json() for item in self.expect],
        }


@dataclass(frozen=True)
class BuildProgram:
    steps: tuple[Step, ...]
    final: str | None

    def to_json(self) -> dict[str, Any]:
        return {
            "steps": [step.to_json() for step in self.steps],
            "final": self.final,
        }


@dataclass(frozen=True)
class CompileIssue:
    code: str
    message: str
    node_id: str | None = None
    hint: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "node_id": self.node_id,
            "hint": self.hint,
        }


class Coverage(dict):
    """Coverage summary that is both a mapping and an attribute bag."""

    @property
    def found(self) -> list[str]:
        return list(self.get("found", ()))

    @property
    def known(self) -> list[str]:
        return list(self.get("known", ()))

    @property
    def unknown(self) -> list[str]:
        return list(self.get("unknown", ()))

    @property
    def actions(self) -> dict[str, int]:
        return dict(self.get("actions", {}))

    @property
    def feature_nodes(self) -> int:
        return int(self.get("feature_nodes", 0))


@dataclass(frozen=True)
class CompileReport:
    plan_id: str
    ops: list[dict[str, Any]]
    issues: tuple[CompileIssue, ...]
    coverage: Mapping[str, Any]
    program: BuildProgram | None = None

    @property
    def ok(self) -> bool:
        return not self.issues

    @property
    def ops_count(self) -> int:
        return len(self.ops)

    @property
    def op_count(self) -> int:
        return len(self.ops)

    @property
    def steps(self) -> tuple[Step, ...]:
        return self.program.steps if self.program is not None else ()

    @property
    def final(self) -> str | None:
        return self.program.final if self.program is not None else None

    def to_json(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "ok": self.ok,
            "ops_count": self.ops_count,
            "ops": list(self.ops),
            "issues": [issue.to_json() for issue in self.issues],
            "coverage": dict(self.coverage),
            "program": self.program.to_json() if self.program is not None else None,
        }


def spec_for(action: str):
    """Look up an action, tolerating a feature module that exposes only ``FEATURES``."""
    getter = getattr(_features, "spec_for", None)
    if callable(getter):
        try:
            return getter(action)
        except Exception:
            return None
    registry = getattr(_features, "FEATURES", {}) or {}
    try:
        return registry.get(action)
    except TypeError:
        return None


def resolve_params(spec: Any, provided: Mapping[str, Any]) -> dict[str, Any]:
    helper = getattr(_features, "resolve_params", None)
    if callable(helper):
        return helper(spec, provided)
    return dict(provided)


def validate_feature(action: str, refs: Mapping[str, Any]) -> Any:
    helper = getattr(_features, "validate_feature", None)
    if callable(helper):
        return helper(action, refs)
    return _fallback_validate(action, refs)


def _input_roles(spec: Any) -> list[tuple[str, str, bool, bool]]:
    optional = set(getattr(spec, "optional", ()) or ())
    roles: list[tuple[str, str, bool, bool]] = []
    for item in getattr(spec, "inputs", ()) or ():
        if isinstance(item, (tuple, list)):
            role = str(item[0]) if len(item) > 0 else ""
            kind = str(item[1]) if len(item) > 1 else ""
            many = False
            is_optional = role in optional
        else:
            role = str(getattr(item, "role", "") or getattr(item, "name", ""))
            kind = str(getattr(item, "kind", ""))
            many = bool(getattr(item, "many", False))
            is_optional = bool(getattr(item, "optional", False) or role in optional)
        roles.append((role, kind, many, is_optional))
    return roles


def _fallback_validate(action: str, refs: Mapping[str, Any]) -> Any:
    spec = spec_for(action)
    if spec is None:
        raise CompileError(
            "ACTION_UNKNOWN",
            f"unknown action {action!r}",
            hint="call the catalog tool to inspect known actions",
        )
    roles = _input_roles(spec)
    required = {role for role, _kind, _many, optional in roles if not optional}
    allowed = {role for role, _kind, _many, _optional in roles}
    missing = sorted(required - set(refs))
    extra = sorted(set(refs) - allowed)
    if missing or extra:
        raise CompileError(
            "PLAN_INVALID",
            f"{action} refs: missing {missing}, unexpected {extra}",
            hint=f"required roles: {', '.join(sorted(required)) or '(none)'}",
        )
    return spec


def _variable(node_id: str) -> str:
    return "n" + _VARIABLE_BAD.sub("_", str(node_id))


def _feature_id(node: PlanNode) -> str:
    return node.feature_id or node.id


def _feature_map(plan: ModelingPlan) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for node in getattr(plan, "nodes", ()) or ():
        if getattr(node, "kind", None) == "feature":
            mapping[str(node.id)] = _feature_id(node)
    return mapping


def _feature_variables(plan: ModelingPlan) -> dict[str, str]:
    return {
        str(node.id): _variable(str(node.id))
        for node in getattr(plan, "nodes", ()) or ()
        if getattr(node, "kind", None) == "feature"
    }


def _translate_ref(ref: Any, id_map: Mapping[str, str], node_id: str) -> Ref:
    source = getattr(ref, "source", None)
    if not isinstance(source, str) or source not in id_map:
        raise CompileError(
            "PLAN_INVALID",
            f"node {node_id!r} ref source {source!r} is not a feature node in this plan",
            node_id=node_id,
            hint="reference sources must name an earlier feature node",
        )
    kwargs: dict[str, Any] = {"source": id_map[source]}
    # ``since``/``extra`` name earlier features too, so they need the same id
    # translation as ``source``.
    for name in ("since", "extra"):
        if hasattr(ref, name):
            values = tuple(getattr(ref, name) or ())
            if values:
                kwargs[name] = tuple(id_map.get(str(item), str(item)) for item in values)
    try:
        return replace(ref, **kwargs)
    except TypeError as exc:
        try:
            return Ref(
                source=id_map[source],
                select=getattr(ref, "select", "faces"),
                filters=tuple(getattr(ref, "filters", ()) or ()),
            )
        except Exception as inner:  # pragma: no cover - defensive
            raise CompileError(
                "PLAN_INVALID",
                f"node {node_id!r} has an invalid ref: {inner}",
                node_id=node_id,
            ) from exc


def _translate_refs(plan: ModelingPlan, node: PlanNode) -> dict[str, Ref | tuple[Ref, ...]]:
    id_map = _feature_map(plan)
    output: dict[str, Ref | tuple[Ref, ...]] = {}
    for role, value in dict(node.refs).items():
        if isinstance(value, (tuple, list)):
            output[str(role)] = tuple(
                _translate_ref(ref, id_map, node.id) for ref in value
            )
        else:
            output[str(role)] = _translate_ref(value, id_map, node.id)
    return output


def _refs_json(refs: Mapping[str, Ref | tuple[Ref, ...]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for role, value in refs.items():
        if isinstance(value, (tuple, list)):
            output[str(role)] = [ref_to_json(ref) for ref in value]
        else:
            output[str(role)] = ref_to_json(value)
    return output


def _feature_payload(node: PlanNode, feature_id: str, params: Mapping[str, Any],
                     refs: Mapping[str, Ref | tuple[Ref, ...]]) -> dict[str, Any]:
    return {
        "id": feature_id,
        "type": node.action,
        "params": dict(params),
        "refs": _refs_json(refs),
        "enabled": True,
        "note": node.note or "",
        "actor": "agent",
    }


def _feature_field(feature: Any, name: str, default: Any = None) -> Any:
    if isinstance(feature, Mapping):
        return feature.get(name, default)
    return getattr(feature, name, default)


def _find_existing(document: Any, feature_id: str) -> Any | None:
    if document is None:
        return None
    for feature in getattr(document, "features", ()) or ():
        if _feature_field(feature, "id") == feature_id:
            return feature
    return None


@dataclass(frozen=True)
class _Parts:
    spec: Any
    feature_id: str
    params: dict[str, Any]
    refs: dict[str, Ref | tuple[Ref, ...]]


def _compile_feature_parts(plan: ModelingPlan, node: PlanNode,
                           document: Any | None) -> _Parts:
    del document  # node lowering is independent of the current document
    action = node.action
    if not isinstance(action, str) or not action.strip():
        raise CompileError(
            "PLAN_INVALID",
            f"feature node {node.id!r} has no action",
            node_id=node.id,
        )

    spec = spec_for(action)
    if spec is None:
        raise CompileError(
            "ACTION_UNKNOWN",
            f"unknown action {action!r}",
            node_id=node.id,
            hint="call the catalog tool to inspect known actions",
        )

    try:
        resolved = resolve_params(spec, node.params)
    except Exception as exc:
        code = getattr(exc, "code", None)
        raise CompileError(
            "ACTION_UNKNOWN" if code in {"UNKNOWN_FEATURE_TYPE", "ACTION_UNKNOWN"} else "PLAN_INVALID",
            str(exc),
            node_id=node.id,
            hint=getattr(exc, "hint", None),
        ) from exc
    # ``None`` is the absence of an optional value, not a document value: the
    # document layer rejects it, and a backend should fall back to the kernel's
    # own default rather than receive an explicit None.
    params = {name: value for name, value in resolved.items() if value is not None}

    refs = _translate_refs(plan, node)
    try:
        validate_feature(action, refs)
    except CompileError:
        raise
    except Exception as exc:
        code = getattr(exc, "code", None)
        raise CompileError(
            "ACTION_UNKNOWN" if code in {"UNKNOWN_FEATURE_TYPE", "ACTION_UNKNOWN"} else "PLAN_INVALID",
            str(exc),
            node_id=node.id,
            hint=getattr(exc, "hint", None),
        ) from exc

    return _Parts(spec=spec, feature_id=_feature_id(node), params=params, refs=refs)


def compile_node(plan: ModelingPlan, node: PlanNode,
                 document: Any | None) -> list[dict[str, Any]]:
    """Lower one feature node to document ops (``add`` or ``update``)."""
    if getattr(node, "kind", None) != "feature":
        return []

    parts = _compile_feature_parts(plan, node, document)
    existing = _find_existing(document, parts.feature_id)
    if existing is not None:
        existing_type = _feature_field(existing, "type")
        if existing_type is not None and existing_type != node.action:
            raise CompileError(
                "PLAN_INVALID",
                f"feature {parts.feature_id!r} already exists with type "
                f"{existing_type!r}; type is immutable",
                node_id=node.id,
                hint="use a new feature id or remove the existing feature first",
            )
        return [{
            "op": "update",
            "id": parts.feature_id,
            "params": dict(parts.params),
            "refs": _refs_json(parts.refs),
        }]

    return [{
        "op": "add",
        "feature": _feature_payload(node, parts.feature_id, parts.params, parts.refs),
    }]


def _input_variable(ref: Any, feature_vars: Mapping[str, str], node_id: str) -> str:
    source = getattr(ref, "source", None)
    if not isinstance(source, str) or source not in feature_vars:
        raise CompileError(
            "PLAN_INVALID",
            f"node {node_id!r} input source {source!r} is not a feature node",
            node_id=node_id,
        )
    return feature_vars[source]


def compile_program(plan: ModelingPlan, document: Any | None = None) -> BuildProgram:
    """Lower every feature node to a backend-neutral :class:`BuildProgram`."""
    try:
        validate_plan(plan, document)
    except PlanError as exc:
        raise CompileError(exc.code, exc.message, hint=exc.hint) from exc

    feature_vars = _feature_variables(plan)
    steps: list[Step] = []
    seen_features: set[str] = set()

    for node in plan.nodes:
        if node.kind != "feature":
            continue
        parts = _compile_feature_parts(plan, node, document)
        if parts.feature_id in seen_features:
            raise CompileError(
                "NODE_ID_CONFLICT",
                f"duplicate document feature id {parts.feature_id!r}",
                node_id=node.id,
            )
        seen_features.add(parts.feature_id)

        inputs: dict[str, str | tuple[str, ...]] = {}
        for role, value in dict(node.refs).items():
            if isinstance(value, (tuple, list)):
                inputs[str(role)] = tuple(
                    _input_variable(ref, feature_vars, node.id) for ref in value
                )
            else:
                inputs[str(role)] = _input_variable(value, feature_vars, node.id)

        steps.append(Step(
            node_id=node.id,
            action=str(node.action),
            variable=feature_vars[node.id],
            inputs=inputs,
            params=dict(parts.params),
            expect=tuple(node.expect),
        ))

    return BuildProgram(
        steps=tuple(steps),
        final=steps[-1].variable if steps else None,
    )


def _coverage(plan: ModelingPlan) -> dict[str, Any]:
    actions: dict[str, int] = {}
    found: list[str] = []
    unknown: list[str] = []

    for node in getattr(plan, "nodes", ()) or ():
        if getattr(node, "kind", None) != "feature":
            continue
        action = node.action if isinstance(node.action, str) and node.action.strip() else ""
        label = action or "<missing>"
        actions[label] = actions.get(label, 0) + 1
        if action and spec_for(action) is not None:
            if action not in found:
                found.append(action)
        elif label not in unknown:
            unknown.append(label)

    found.sort()
    unknown.sort()
    return Coverage({
        "actions": dict(sorted(actions.items())),
        "found": found,
        "known": found,
        "known_actions": found,
        "unknown": unknown,
        "unknown_actions": unknown,
        "feature_nodes": sum(actions.values()),
        "total_actions": len(actions),
    })


def compile_plan(plan: ModelingPlan, document: Any | None = None) -> CompileReport:
    """Compile a whole plan, collecting issues instead of stopping at the first."""
    coverage = _coverage(plan)
    issues: list[CompileIssue] = []

    try:
        validate_plan(plan, document)
    except PlanError as exc:
        issues.append(CompileIssue(exc.code, exc.message, hint=exc.hint))
        return CompileReport(
            plan_id=plan.id,
            ops=[],
            issues=tuple(issues),
            coverage=coverage,
            program=None,
        )

    ops: list[dict[str, Any]] = []
    seen_features: dict[str, str] = {}

    for node in plan.nodes:
        if node.kind != "feature":
            continue
        feature_id = _feature_id(node)
        if feature_id in seen_features:
            issues.append(CompileIssue(
                "NODE_ID_CONFLICT",
                f"document feature id {feature_id!r} is used by both "
                f"{seen_features[feature_id]!r} and {node.id!r}",
                node_id=node.id,
            ))
            continue
        try:
            node_ops = compile_node(plan, node, document)
        except CompileError as exc:
            issues.append(CompileIssue(exc.code, exc.message, node.id, exc.hint))
            continue
        seen_features[feature_id] = node.id
        ops.extend(node_ops)

    program: BuildProgram | None = None
    if not issues:
        try:
            program = compile_program(plan, document)
        except CompileError as exc:
            issues.append(CompileIssue(exc.code, exc.message, exc.node_id, exc.hint))

    return CompileReport(
        plan_id=plan.id,
        ops=ops,
        issues=tuple(issues),
        coverage=coverage,
        program=program,
    )


__all__ = [
    "BuildProgram",
    "CompileError",
    "CompileIssue",
    "CompileReport",
    "Coverage",
    "Step",
    "compile_node",
    "compile_plan",
    "compile_program",
    "resolve_params",
    "spec_for",
    "validate_feature",
]
