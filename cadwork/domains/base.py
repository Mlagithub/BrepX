"""Domain package contracts shared by the CAD core and domain implementations.

A domain package supplies semantic inputs, typed plan nodes, checks, component
definitions and gate descriptions. The geometry kernel, document store and
preview path remain shared; a package never owns its own document format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


class DomainError(Exception):
    """A domain package request cannot be served as stated."""

    def __init__(
        self, code: str, message: str, hint: str | None = None, status: int = 400
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.status = status

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "hint": self.hint}


@dataclass(frozen=True)
class FieldSpec:
    """One design-brief field with its unit and constraint surface."""

    name: str
    kind: str = "string"
    required: bool = False
    unit: str = ""
    default: Any = None
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[str, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise DomainError("INVALID_FIELD", "field name cannot be empty")
        if self.kind not in {
            "string", "number", "integer", "boolean", "enum", "vector"
        }:
            raise DomainError(
                "INVALID_FIELD", f"unknown field kind {self.kind!r}"
            )
        if self.kind == "enum" and not self.choices:
            raise DomainError(
                "INVALID_FIELD", f"enum field {self.name!r} needs choices"
            )

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "required": self.required,
            "unit": self.unit,
            "default": self.default,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "choices": list(self.choices),
            "description": self.description,
        }


@dataclass(frozen=True)
class BriefSchema:
    """The declarative questions a domain asks before generation."""

    id: str
    title: str
    fields: tuple[FieldSpec, ...] = ()
    description: str = ""
    assumptions: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if not self.id:
            raise DomainError("INVALID_BRIEF", "brief id cannot be empty")
        object.__setattr__(self, "fields", tuple(self.fields))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))

    def field(self, name: str) -> FieldSpec:
        for item in self.fields:
            if item.name == name:
                return item
        raise DomainError("UNKNOWN_FIELD", f"no brief field {name!r}")

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "fields": [item.to_json() for item in self.fields],
            "assumptions": [dict(item) for item in self.assumptions],
        }


@dataclass(frozen=True)
class Assumption:
    """A recorded design assumption, never a silent default."""

    id: str
    text: str
    source: str = "system"
    confirmed: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "source": self.source,
            "confirmed": self.confirmed,
        }


@dataclass(frozen=True)
class NodeKind:
    """A typed domain node the plan executor may dispatch."""

    id: str
    description: str = ""
    output: str = ""
    compiler_version: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "output": self.output,
            "compiler_version": self.compiler_version,
        }


@dataclass(frozen=True)
class GateSpec:
    """One human-approved acceptance gate owned by a domain package."""

    id: str
    title: str
    required_checks: tuple[str, ...] = ()
    approval_role: str = "owner"
    description: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise DomainError("INVALID_GATE", "gate id cannot be empty")
        object.__setattr__(self, "required_checks", tuple(self.required_checks))

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "required_checks": list(self.required_checks),
            "approval_role": self.approval_role,
            "description": self.description,
        }


@dataclass(frozen=True)
class Waiver:
    """A visible exception to a soft check."""

    check_id: str
    reason: str
    approved_by: str
    expires_version: int | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "reason": self.reason,
            "approved_by": self.approved_by,
            "expires_version": self.expires_version,
        }


@runtime_checkable
class DomainPack(Protocol):
    """The surface every domain implementation must provide."""

    id: str
    version: str

    def brief_schema(self) -> BriefSchema: ...

    def node_kinds(self) -> Sequence[NodeKind]: ...

    def compile(
        self, node: Mapping[str, Any], context: Mapping[str, Any] | None = None
    ) -> Sequence[Mapping[str, Any]]: ...

    def validate(
        self, document: Any, context: Mapping[str, Any] | None = None
    ) -> Sequence[Any]: ...

    def components(self) -> Sequence[Any]: ...

    def gates(self) -> Sequence[GateSpec]: ...


def pack_to_json(pack: DomainPack) -> dict[str, Any]:
    return {
        "id": pack.id,
        "version": pack.version,
        "brief": pack.brief_schema().to_json(),
        "node_kinds": [item.to_json() for item in pack.node_kinds()],
        "components": len(list(pack.components())),
        "gates": [item.to_json() for item in pack.gates()],
    }
