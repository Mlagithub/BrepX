"""Deterministic generation of the Python scripts the script backend runs.

A plan node is one :class:`Step`: an action name (``k_box``), a target
variable (``n3``), the already-built variables it consumes and its literal
parameters.  :func:`emit_node` turns that into a small, repeatable Python
snippet::

    n3 = Box(height=30, length=10, width=20)
    ...
    print("__BREPX_METRICS__" + json.dumps(_brepx_metrics(n3), sort_keys=True))

Properties the backend relies on:

* **deterministic** — the same step always produces byte-identical text (no
  timestamps, no random ids, sorted keyword arguments);
* **self-contained** — every snippet imports what it uses, because snippets run
  as separate ``run_script`` calls in a persistent smlibpy session;
* **session-state only** — the snippet references only the step's own target
  variable and the ``n*`` variables named in ``step.inputs``, which earlier
  steps left in the session.

The action table below mirrors ``cadwork.design.kernel_actions._ACTIONS`` for
the actions this backend executes.  It is deliberately a copy, not an import:
``kernel_actions`` imports ``smlibpy`` at module import time, and this module
must stay importable before the kernel (and before ``plan_compile``) is
available.  An action outside the table raises :class:`EmitError` instead of
silently emitting something wrong.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:  # type-only: importing plan_compile would pull in smlibpy
    from cadwork.design.plan_compile import BuildProgram, Step  # noqa: F401

#: The generated script prints this marker immediately before a JSON object.
METRICS_PREFIX = "__BREPX_METRICS__"

_VARIABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PLANE_MEMBERS = frozenset(
    {"XY", "XZ", "YZ", "YX", "ZX", "ZY", "front", "back", "left", "right", "top", "bottom"}
)
_AXIS_MEMBERS = frozenset({"X", "Y", "Z"})


class EmitError(ValueError):
    """The step cannot be rendered safely as script text.

    ``code`` distinguishes a genuinely unknown action (``ACTION_UNKNOWN``)
    from a malformed step (``PLAN_INVALID``) so the service layer can map it.
    """

    def __init__(self, message: str, *, code: str = "PLAN_INVALID", node_id: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.node_id = node_id


@dataclass(frozen=True)
class _Input:
    role: str
    many: bool = False
    optional: bool = False


@dataclass(frozen=True)
class _Action:
    source: str
    inputs: tuple[_Input, ...] = ()
    allow: tuple[str, ...] | None = None  # None: no parameters accepted
    call: str = "keywords"  # keywords | method | varargs


def _I(role: str, many: bool = False, optional: bool = False) -> _Input:
    return _Input(role, many, optional)


# Mirrors the relevant rows of kernel_actions._ACTIONS.  Keep this table in
# step with that module when new actions become executable.
_ACTIONS: dict[str, _Action] = {
    "k_box": _Action("Box", allow=("length", "width", "height")),
    "k_cylinder": _Action("Cylinder", allow=("radius", "height", "arc_size")),
    "k_extrude": _Action(
        "extrude",
        (_I("profile"),),
        allow=("amount", "both", "taper", "corners"),
    ),
    "k_sweep": _Action(
        "sweep",
        (_I("profile"), _I("path")),
        # ``scale`` is derived from the plan's scale_start/scale_end pair.
        allow=("orient", "translational", "sharp_corners", "twist", "scale"),
    ),
    "k_spiral": _Action(
        "Spiral",
        allow=("start_radius", "end_radius", "turns", "plane", "clockwise"),
    ),
    "k_fillet": _Action(
        "Part.fillet",
        (_I("target"), _I("edges")),
        allow=("radius", "continuity", "fullness", "propagate", "corners", "setback"),
        call="method",
    ),
    "k_shell": _Action(
        "Part.shell",
        (_I("target"), _I("openings", optional=True)),
        allow=("thickness", "outward", "corners", "walls"),
        call="method",
    ),
    "k_cut": _Action(
        "Part.cut", (_I("target"), _I("others", many=True)), call="method"
    ),
    "k_fuse": _Action(
        "Part.fuse", (_I("target"), _I("others", many=True)), call="method"
    ),
    "k_draft": _Action(
        "Part.draft",
        (_I("target"), _I("faces")),
        allow=("angle", "neutral_plane"),
        call="method",
    ),
    "k_twist": _Action(
        "Part.twist",
        (_I("target"),),
        allow=("angle", "axis", "start", "end", "tolerance"),
        call="method",
    ),
}

#: Bare names accepted in addition to the canonical ``k_<snake>`` action names.
_ALIASES = {"box": "k_box", "cylinder": "k_cylinder"}

_METRICS_HELPER = '''\
def _brepx_metrics(value):
    metrics = {}
    for key in ("volume", "area"):
        try:
            item = getattr(value, key, None)
            metrics[key] = None if item is None else float(item)
        except Exception:
            metrics[key] = None
    for key in ("faces", "edges", "solids"):
        try:
            metrics[key] = len(getattr(value, key)())
        except Exception:
            metrics[key] = None
    try:
        metrics["watertight"] = bool(value.is_valid())
    except Exception:
        metrics["watertight"] = None
    try:
        box = value.bbox()
    except Exception:
        box = None
    if box is None:
        metrics["bbox"] = None
    else:
        try:
            metrics["bbox"] = {
                "min": [float(item) for item in box.min],
                "max": [float(item) for item in box.max],
            }
        except Exception:
            metrics["bbox"] = None
    return metrics
'''


def supported_actions() -> tuple[str, ...]:
    """The action names :func:`emit_node` can render, sorted."""
    return tuple(sorted(_ACTIONS))


def _spec_for(step: Any) -> _Action:
    node_id = str(getattr(step, "node_id", "") or "")
    action = getattr(step, "action", None)
    if not isinstance(action, str) or not action.strip():
        raise EmitError(f"step {node_id!r} has no action", node_id=node_id)
    key = action.strip()
    spec = _ACTIONS.get(key)
    if spec is None:
        spec = _ACTIONS.get(_ALIASES.get(key, ""))
    if spec is None:
        raise EmitError(
            f"action {action!r} is not supported by the script emitter; "
            f"supported actions: {', '.join(supported_actions())}",
            code="ACTION_UNKNOWN",
            node_id=node_id,
        )
    return spec


def _variable(value: Any, role: str, node_id: str) -> str:
    if not isinstance(value, str) or not _VARIABLE_RE.match(value):
        raise EmitError(
            f"node {node_id}: input {role!r} must be a variable name, got {value!r}",
            node_id=node_id,
        )
    return value


def _literal(value: Any, *, node_id: str, what: str = "value") -> str:
    """Render a parameter as a deterministic Python literal."""
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int):
        return repr(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise EmitError(
                f"node {node_id}: {what} is not finite ({value!r})", node_id=node_id
            )
        return repr(value)
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(
            _literal(item, node_id=node_id, what=f"{what}[{index}]")
            for index, item in enumerate(value)
        ) + "]"
    if isinstance(value, Mapping):
        items: list[tuple[str, str]] = []
        for key, item in value.items():
            if not isinstance(key, (str, int, float, bool)):
                raise EmitError(
                    f"node {node_id}: {what} has an unsupported key {key!r}",
                    node_id=node_id,
                )
            items.append(
                (
                    repr(key),
                    _literal(item, node_id=node_id, what=f"{what}[{key!r}]"),
                )
            )
        items.sort(key=lambda pair: pair[0])
        return "{" + ", ".join(f"{key}: {item}" for key, item in items) + "}"
    raise EmitError(
        f"node {node_id}: {what} has unsupported type {type(value).__name__}",
        node_id=node_id,
    )


def _enum_literal(name: str, value: Any, *, node_id: str) -> str:
    if name in ("plane", "neutral_plane"):
        if isinstance(value, str) and value.strip() in _PLANE_MEMBERS:
            return f"Plane.{value.strip()}"
        raise EmitError(
            f"node {node_id}: {name} must be a Plane member (e.g. 'XY'), got {value!r}",
            node_id=node_id,
        )
    if name == "axis":
        if isinstance(value, str) and value.strip() in _AXIS_MEMBERS:
            return value.strip()
        raise EmitError(
            f"node {node_id}: axis must be 'X', 'Y' or 'Z', got {value!r}",
            node_id=node_id,
        )
    raise EmitError(f"node {node_id}: unknown enum parameter {name!r}", node_id=node_id)


def _parameter_literal(name: str, value: Any, *, node_id: str) -> str:
    if name in ("plane", "neutral_plane", "axis"):
        return _enum_literal(name, value, node_id=node_id)
    return _literal(value, node_id=node_id, what=f"parameter {name!r}")


def _render_params(params: Mapping[str, Any], *, node_id: str) -> list[tuple[str, str]]:
    return sorted(
        (
            (name, _parameter_literal(name, value, node_id=node_id))
            for name, value in params.items()
        ),
        key=lambda pair: pair[0],
    )


def _prepare_params(spec: _Action, step: Any, *, node_id: str) -> dict[str, Any]:
    raw = getattr(step, "params", None) or {}
    if not isinstance(raw, Mapping):
        raise EmitError(f"node {node_id}: params must be a mapping", node_id=node_id)
    params: dict[str, Any] = dict(raw)
    # The planner spells the sweep scale as a start/end pair (kernel_actions
    # turns it into the kernel's single ``scale=(start, end)`` argument).
    if "scale_start" in params or "scale_end" in params:
        start = params.pop("scale_start", 1.0)
        end = params.pop("scale_end", 1.0)
        params["scale"] = (start, end)
    if spec.allow is None:
        if params:
            raise EmitError(
                f"node {node_id}: action {getattr(step, 'action', '?')!r} takes no parameters, "
                f"got {', '.join(sorted(map(str, params)))}",
                node_id=node_id,
            )
        return {}
    unknown = sorted(set(params) - set(spec.allow))
    if unknown:
        raise EmitError(
            f"node {node_id}: action {getattr(step, 'action', '?')!r} does not accept "
            f"{', '.join(unknown)}",
            node_id=node_id,
        )
    return params


def _many(value: Any, role: str, node_id: str) -> list[str]:
    items = list(value) if isinstance(value, (list, tuple)) else [value]
    if not items:
        raise EmitError(
            f"node {node_id}: input {role!r} needs at least one variable", node_id=node_id
        )
    return [_variable(item, role, node_id) for item in items]


def _bound_inputs(spec: _Action, step: Any, *, node_id: str) -> dict[str, Any]:
    inputs = getattr(step, "inputs", None) or {}
    if not isinstance(inputs, Mapping):
        raise EmitError(f"node {node_id}: inputs must be a mapping", node_id=node_id)
    allowed = {item.role for item in spec.inputs}
    unknown = sorted(set(inputs) - allowed)
    if unknown:
        raise EmitError(
            f"node {node_id}: action {getattr(step, 'action', '?')!r} has no input role(s) "
            f"{', '.join(unknown)}",
            node_id=node_id,
        )
    return dict(inputs)


def _keyword_for(item: _Input, value: Any, *, node_id: str) -> tuple[str, str] | None:
    if item.many:
        if value is None:
            if item.optional:
                return None
            raise EmitError(
                f"node {node_id}: input {item.role!r} is required", node_id=node_id
            )
        rendered = _many(value, item.role, node_id)
        return item.role, "[" + ", ".join(rendered) + "]"
    if value is None:
        if item.optional:
            return None
        raise EmitError(
            f"node {node_id}: input {item.role!r} is required", node_id=node_id
        )
    return item.role, _variable(value, item.role, node_id)


def _render_call(spec: _Action, step: Any, *, node_id: str) -> str:
    params = _prepare_params(spec, step, node_id=node_id)
    bound = _bound_inputs(spec, step, node_id=node_id)

    if spec.call == "method":
        target = bound.get("target")
        if target is None:
            raise EmitError(
                f"node {node_id}: action {getattr(step, 'action', '?')!r} requires input 'target'",
                node_id=node_id,
            )
        target_var = _variable(target, "target", node_id)
        method = spec.source.split(".", 1)[1]
        positional: list[str] = []
        keywords: list[tuple[str, str]] = []
        for item in spec.inputs:
            if item.role == "target":
                continue
            value = bound.get(item.role)
            if item.many and item.role == "others":
                if value is not None:
                    positional.extend(_many(value, item.role, node_id))
                elif not item.optional:
                    raise EmitError(
                        f"node {node_id}: input {item.role!r} is required",
                        node_id=node_id,
                    )
                continue
            pair = _keyword_for(item, value, node_id=node_id)
            if pair is not None:
                keywords.append(pair)
        keywords.extend(_render_params(params, node_id=node_id))
        keywords.sort(key=lambda pair: pair[0])
        arguments = positional + [f"{name}={text}" for name, text in keywords]
        return f"{target_var}.{method}({', '.join(arguments)})"

    positional = []
    keywords = []
    if spec.call == "varargs":
        for item in spec.inputs:
            value = bound.get(item.role)
            if item.many:
                if value is None:
                    if item.optional:
                        continue
                    raise EmitError(
                        f"node {node_id}: input {item.role!r} is required", node_id=node_id
                    )
                positional.extend(_many(value, item.role, node_id))
            else:
                if value is None:
                    if item.optional:
                        continue
                    raise EmitError(
                        f"node {node_id}: input {item.role!r} is required",
                        node_id=node_id,
                    )
                positional.append(_variable(value, item.role, node_id))
    else:  # keywords, the default and what kernel_actions uses for functions
        for item in spec.inputs:
            pair = _keyword_for(item, bound.get(item.role), node_id=node_id)
            if pair is not None:
                keywords.append(pair)
    keywords.extend(_render_params(params, node_id=node_id))
    keywords.sort(key=lambda pair: pair[0])
    arguments = positional + [f"{name}={text}" for name, text in keywords]
    return f"{spec.source}({', '.join(arguments)})"


def emit_node(step: "Step", step_path: str | None = None) -> str:
    """Render one plan step as a deterministic Python script.

    ``step_path`` optionally adds ``export_step`` for that node's result; the
    backend passes a temporary ``.step`` path when the caller wants a file.
    """
    node_id = str(getattr(step, "node_id", "") or "")
    spec = _spec_for(step)
    variable = _variable(getattr(step, "variable", None), "variable", node_id)
    call = _render_call(spec, step, node_id=node_id)

    tag = " ".join(node_id.split())
    lines = [
        f"# cadwork ScriptBackend: node {tag} ({step.action})",
        "from smlibpy import *",
        "import json",
        "import math",
        "",
        f"{variable} = {call}",
        "",
        _METRICS_HELPER,
    ]
    if step_path is not None:
        lines.append(f"export_step({variable}, {_literal(str(step_path), node_id=node_id, what='step_path')})")
        lines.append("")
    lines.append(
        f"print({METRICS_PREFIX!r} + json.dumps(_brepx_metrics({variable}), sort_keys=True))"
    )
    return "\n".join(lines) + "\n"


__all__ = [
    "EmitError",
    "METRICS_PREFIX",
    "emit_node",
    "supported_actions",
]
