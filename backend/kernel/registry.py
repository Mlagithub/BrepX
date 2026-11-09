"""Operator specification and registry for BrepX geometry engine."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any, Callable

from backend.core.command import Assertion
from backend.core.errors import OperatorNotFoundError
from backend.core.params import ParamSpec

VALID_CATEGORIES = {
    "primitive",
    "feature",
    "pattern",
    "surface",
    "cfd",
    "turbomachinery",
    "annotation",
}

REQUIRED_DOC_KEYS = ("用途", "场景", "区别", "参数", "约束", "示例")

CORE_OPS = (
    "box",
    "cylinder",
    "extrude",
    "revolve",
    "fillet",
    "chamfer",
    "hole",
    "shell",
    "boolean_cut",
    "boolean_join",
    "polar_array",
    "cavity_extraction",
)


@dataclass(frozen=True)
class OperatorSpec:
    op: str
    category: str
    produces: str
    params: dict[str, ParamSpec]
    needs_target: bool
    needs_tool: bool
    default_assertions: tuple[Assertion, ...]
    doc: str
    call: Callable[..., Any]

    def __post_init__(self) -> None:
        if self.category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid operator category '{self.category}'. Allowed categories: {sorted(VALID_CATEGORIES)}"
            )
        for key in REQUIRED_DOC_KEYS:
            if key not in self.doc:
                raise ValueError(
                    f"Operator '{self.op}' docstring missing mandatory section keyword: '{key}'"
                )


class OperatorRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, OperatorSpec] = {}

    def register(self, spec: OperatorSpec) -> None:
        if spec.op in self._specs:
            raise ValueError(f"Operator '{spec.op}' is already registered.")
        self._specs[spec.op] = spec

    def get(self, op: str) -> OperatorSpec:
        if op not in self._specs:
            closest = difflib.get_close_matches(op, self._specs.keys(), n=3, cutoff=0.4)
            raise OperatorNotFoundError(op, closest)
        return self._specs[op]

    def all_ops(self) -> list[str]:
        return sorted(self._specs.keys())

    def specs_by_category(self, category: str) -> list[OperatorSpec]:
        return [spec for spec in self._specs.values() if spec.category == category]

    def core_specs(self) -> list[OperatorSpec]:
        return [self._specs[op] for op in CORE_OPS if op in self._specs]

    def find(self, query: str) -> list[OperatorSpec]:
        q = query.strip().lower()
        if not q:
            return []

        matched: list[tuple[float, OperatorSpec]] = []
        for op, spec in self._specs.items():
            if op in CORE_OPS:
                continue

            score = 0.0
            if q == op.lower():
                score += 10.0
            elif q in op.lower():
                score += 5.0

            if q in spec.category.lower():
                score += 3.0

            if q in spec.doc.lower():
                score += 2.0

            if score > 0.0:
                matched.append((score, spec))

        matched.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in matched[:8]]


_DEFAULT_REGISTRY: OperatorRegistry | None = None


def default_registry() -> OperatorRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = OperatorRegistry()
    return _DEFAULT_REGISTRY
