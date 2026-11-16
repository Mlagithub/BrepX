"""In-process backend: execute a compiled step against the feature registry.

This is the reference implementation used for equivalence tests against the
script backend.  It deliberately does not know about plans: a ``Step`` carries
an action, resolved parameter values and input variable names; ``prior_vars``
carries the Python values those names refer to.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..features import resolve_params, spec_for
from .base import BackendError, NodeResult


def _metrics(value: Any) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for name in ("volume", "area", "length"):
        if hasattr(value, name):
            try:
                metrics[name] = float(getattr(value, name))
            except Exception:
                pass
    for name, method in (
        ("faces", "faces"),
        ("edges", "edges"),
        ("solids", "solids"),
        ("vertices", "vertices"),
    ):
        accessor = getattr(value, method, None)
        if callable(accessor):
            try:
                metrics[name] = len(accessor())
            except Exception:
                pass
    bbox = getattr(value, "bbox", None)
    if callable(bbox):
        try:
            box = bbox()
            metrics["bbox_min"] = [float(box.min[i]) for i in range(3)]
            metrics["bbox_max"] = [float(box.max[i]) for i in range(3)]
            metrics["bbox_size"] = [float(box.size[i]) for i in range(3)]
        except Exception:
            pass
    is_valid = getattr(value, "is_valid", None)
    if callable(is_valid):
        try:
            metrics["watertight"] = bool(is_valid(strict=True))
        except Exception:
            metrics["watertight"] = False
    if not hasattr(value, "volume"):
        metrics.setdefault("volume", 0.0)
    return metrics


class LocalBackend:
    """Execute one step in this process; no kernel session is involved."""

    name = "local"

    def build_node(
        self,
        document_id: str,
        step: Any,
        prior_vars: Mapping[str, Any] | None = None,
        step_path: str | None = None,
    ) -> NodeResult:
        del document_id, step_path
        spec = spec_for(step.action)
        if spec is None:
            raise BackendError(f"unknown action {step.action!r}", code="ACTION_UNKNOWN")
        params = resolve_params(spec, step.params)
        values = dict(prior_vars or {})
        inputs: dict[str, Any] = {}
        for role in spec.inputs:
            bound = step.inputs.get(role.role)
            if bound is None:
                if role.optional:
                    inputs[role.role] = None
                    continue
                raise BackendError(
                    f"{step.node_id}.{role.role} is required", code="INVALID_REFS"
                )
            if isinstance(bound, tuple):
                inputs[role.role] = tuple(values[item] for item in bound)
            else:
                inputs[role.role] = values[bound]
        try:
            output = spec.build(inputs, params)
        except Exception as exc:
            raise BackendError(
                f"{step.node_id} ({step.action}) failed: {exc}", raw=str(exc)
            ) from exc
        failed = [
            check for check in spec.check(output.value, params, inputs) if not check.ok
        ]
        if failed:
            first = failed[0]
            raise BackendError(
                f"{step.node_id} ({step.action}) failed: {first.name}",
                code="EXPECT_FAILED",
                raw=str(first.observed),
            )
        return NodeResult(metrics=_metrics(output.value), raw=None, value=output.value)

    def reset(self, document_id: str) -> None:
        del document_id

    def close(self) -> None:
        pass
