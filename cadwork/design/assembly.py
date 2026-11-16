"""Assembly documents: instances pin exact part and sub-assembly versions.

An assembly is a flat list of instances. Each instance names a referenced
document by identity and immutable version, so a later edit to that document
does not move existing geometry; changing a pin is an explicit edit. A
placement is a rigid transform in caller units. This module validates
structure and JSON shape only and never touches geometry.
"""

from __future__ import annotations

import json
import math
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from cadwork.design.document import DocumentError

_IDENTITY_ROTATION = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)
_IDENTITY_TRANSLATION = (0.0, 0.0, 0.0)


def _check_text(value: Any, label: str) -> str:
    """An identifier is a non-empty token without surrounding whitespace.

    Ids become part of composite selection paths and cache keys, so an id that
    is empty, padded, or holds a control character cannot round-trip as an
    unambiguous string.
    """
    if not isinstance(value, str) or not value:
        raise DocumentError("INVALID_ID", f"{label} must be a non-empty string")
    if value != value.strip() or any(ord(char) < 32 for char in value):
        raise DocumentError(
            "INVALID_ID",
            f"{label} must not contain surrounding whitespace or control characters",
        )
    return value


def _check_name(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise DocumentError("INVALID_FIELD", f"{label} must be a string")
    return value


def _check_version(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DocumentError("INVALID_VERSION", f"{label} must be an integer >= 1")
    if value < 1:
        raise DocumentError("INVALID_VERSION", f"{label} must be >= 1, got {value}")
    return value


def _check_seq(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DocumentError("INVALID_FIELD", "seq must be an integer")
    if value < 0:
        raise DocumentError("INVALID_FIELD", f"seq must be >= 0, got {value}")
    return value


def _check_configuration(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise DocumentError(
            "INVALID_CONFIGURATION", "configuration must be a non-empty string"
        )
    if value != value.strip() or any(ord(char) < 32 for char in value):
        raise DocumentError(
            "INVALID_CONFIGURATION",
            "configuration must not contain surrounding whitespace or control characters",
        )
    return value


def _check_value(label: str, value: Any) -> Any:
    """A parameter value is a scalar, a numeric vector, or a point list."""
    if isinstance(value, bool) or isinstance(value, (int, float, str)):
        if isinstance(value, float) and not math.isfinite(value):
            raise DocumentError("INVALID_VALUE", f"{label} must be finite")
        return value
    if isinstance(value, (list, tuple)) and value:
        if all(
            isinstance(item, (int, float)) and not isinstance(item, bool)
            for item in value
        ):
            return list(value)
        if all(
            isinstance(item, (list, tuple))
            and len(item) in (2, 3)
            and all(
                isinstance(number, (int, float)) and not isinstance(number, bool)
                for number in item
            )
            for item in value
        ):
            return [list(item) for item in value]
    raise DocumentError(
        "INVALID_VALUE",
        f"{label} must be a scalar, a numeric vector, or a point list",
    )


def _check_named_values(value: Any, label: str) -> dict[str, Any]:
    """A named value map holds JSON parameter values under non-empty names.

    Overrides and mate parameters share the parameter value grammar so that a
    value surviving JSON also survives a part build without a second dialect.
    """
    if not isinstance(value, Mapping):
        raise DocumentError("INVALID_FIELD", f"{label} must be a JSON object")
    result: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise DocumentError(
                "INVALID_FIELD", f"{label} keys must be non-empty strings"
            )
        result[key] = _check_value(f"{label} {key}", item)
    return result


def _check_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DocumentError("INVALID_PLACEMENT", f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise DocumentError("INVALID_PLACEMENT", f"{label} must be finite")
    return number


def _check_rotation(value: Any) -> tuple[tuple[float, float, float], ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise DocumentError("INVALID_PLACEMENT", "rotation must be a 3x3 array")
    if len(value) != 3:
        raise DocumentError("INVALID_PLACEMENT", "rotation must have exactly 3 rows")
    rows: list[tuple[float, float, float]] = []
    for index, row in enumerate(value):
        if (
            isinstance(row, (str, bytes))
            or not isinstance(row, (list, tuple))
            or len(row) != 3
        ):
            raise DocumentError(
                "INVALID_PLACEMENT",
                f"rotation row {index} must hold exactly 3 numbers",
            )
        rows.append(tuple(_check_number(item, f"rotation[{index}]") for item in row))
    return tuple(rows)


def _check_translation(value: Any) -> tuple[float, float, float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise DocumentError(
            "INVALID_PLACEMENT", "translation must hold exactly 3 numbers"
        )
    if len(value) != 3:
        raise DocumentError(
            "INVALID_PLACEMENT", "translation must hold exactly 3 numbers"
        )
    return tuple(_check_number(item, "translation") for item in value)


def _check_instances(value: Any) -> tuple[Instance, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise DocumentError("INVALID_FIELD", "instances must be an array of instances")
    for item in value:
        if not isinstance(item, Instance):
            raise DocumentError("INVALID_FIELD", "instances must hold Instance values")
    return tuple(value)


def _check_mates(value: Any) -> tuple[Mate, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise DocumentError("INVALID_FIELD", "mates must be an array of mates")
    for item in value:
        if not isinstance(item, Mate):
            raise DocumentError("INVALID_FIELD", "mates must hold Mate values")
    return tuple(value)


def _require_object(payload: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise DocumentError("INVALID_JSON", f"{label} payload must be a JSON object")
    return payload


def _reject_unknown(payload: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unknown = [key for key in payload if key not in allowed]
    if unknown:
        names = ", ".join(sorted(repr(key) for key in unknown))
        raise DocumentError("UNKNOWN_FIELD", f"unknown {label} field(s): {names}")


def _required(payload: Mapping[str, Any], key: str, label: str) -> Any:
    if key not in payload:
        raise DocumentError("MISSING_FIELD", f"{label} requires field {key!r}")
    return payload[key]


@dataclass(frozen=True)
class Transform:
    """A rigid placement: row-major rotation plus translation.

    Rotation rows are orthonormal by the producer's contract; this type
    enforces the array shape and finite numbers so a malformed placement fails
    at load time instead of producing sheared geometry later.
    """

    rotation: tuple[tuple[float, float, float], ...] = _IDENTITY_ROTATION
    translation: tuple[float, float, float] = _IDENTITY_TRANSLATION

    def __post_init__(self) -> None:
        object.__setattr__(self, "rotation", _check_rotation(self.rotation))
        object.__setattr__(self, "translation", _check_translation(self.translation))


@dataclass(frozen=True)
class PartRef:
    """A pin on one immutable part document version and configuration."""

    document_id: str
    version: int
    configuration: str = "default"

    def __post_init__(self) -> None:
        _check_text(self.document_id, "part document id")
        _check_version(self.version, "part reference version")
        _check_configuration(self.configuration)


@dataclass(frozen=True)
class AssemblyRef:
    """A pin on one immutable sub-assembly document version."""

    document_id: str
    version: int

    def __post_init__(self) -> None:
        _check_text(self.document_id, "assembly document id")
        _check_version(self.version, "assembly reference version")


@dataclass(frozen=True)
class Instance:
    """One placed occurrence of a part or sub-assembly inside an assembly."""

    id: str
    ref: PartRef | AssemblyRef
    placement: Transform
    overrides: Mapping[str, Any] = field(default_factory=dict)
    name: str = ""
    suppressed: bool = False
    visible: bool = True

    def __post_init__(self) -> None:
        _check_text(self.id, "instance id")
        if not isinstance(self.ref, (PartRef, AssemblyRef)):
            raise DocumentError(
                "INVALID_REF", "instance ref must be a part or assembly reference"
            )
        if not isinstance(self.placement, Transform):
            raise DocumentError(
                "INVALID_PLACEMENT", "instance placement must be a transform"
            )
        _check_name(self.name, "instance name")
        if not isinstance(self.suppressed, bool):
            raise DocumentError(
                "INVALID_FIELD", "instance suppressed must be a boolean"
            )
        if not isinstance(self.visible, bool):
            raise DocumentError("INVALID_FIELD", "instance visible must be a boolean")
        object.__setattr__(
            self, "overrides", _check_named_values(self.overrides, "overrides")
        )


@dataclass(frozen=True)
class Mate:
    """A named relationship between two distinct instances of one assembly."""

    id: str
    a_instance: str
    b_instance: str
    kind: str
    params: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_text(self.id, "mate id")
        for label, endpoint in (
            ("mate a_instance", self.a_instance),
            ("mate b_instance", self.b_instance),
        ):
            if not isinstance(endpoint, str) or not endpoint:
                raise DocumentError(
                    "INVALID_MATE", f"{label} must be a non-empty instance id"
                )
        if not isinstance(self.kind, str) or not self.kind:
            raise DocumentError("INVALID_MATE", "mate kind must be a non-empty string")
        if self.a_instance == self.b_instance:
            raise DocumentError(
                "INVALID_MATE", f"mate {self.id!r} joins an instance to itself"
            )
        object.__setattr__(
            self, "params", _check_named_values(self.params, "mate params")
        )


@dataclass(frozen=True)
class AssemblyDocument:
    """An immutable assembly definition at one committed version.

    Instances pin their referenced documents; a mate only groups two distinct
    instances already present. Cycles that span several documents cannot be
    decided from one document and are left to reference resolution.
    """

    id: str
    name: str
    version: int
    instances: tuple[Instance, ...]
    mates: tuple[Mate, ...] = ()
    seq: int = 0
    generation: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_text(self.id, "assembly document id")
        _check_name(self.name, "assembly name")
        _check_version(self.version, "assembly document version")
        _check_seq(self.seq)
        if not isinstance(self.generation, Mapping):
            raise DocumentError(
                "INVALID_GENERATION", "generation metadata must be an object"
            )
        try:
            generation = json.loads(
                json.dumps(dict(self.generation), ensure_ascii=False)
            )
        except (TypeError, ValueError) as exc:
            raise DocumentError(
                "INVALID_GENERATION", "generation metadata must be JSON data"
            ) from exc
        object.__setattr__(self, "instances", _check_instances(self.instances))
        object.__setattr__(self, "mates", _check_mates(self.mates))
        object.__setattr__(self, "generation", generation)
        validate_assembly(self)


def validate_assembly(document: AssemblyDocument) -> None:
    """Instance ids are unique and no instance pins the assembly itself.

    A mate may only name two distinct instances that exist in this document.
    Cross-document cycles are outside what one document can prove.
    """
    seen: set[str] = set()
    for instance in document.instances:
        if instance.id in seen:
            raise DocumentError(
                "DUPLICATE_ID", f"duplicate instance id {instance.id!r}"
            )
        seen.add(instance.id)
        if instance.ref.document_id == document.id:
            raise DocumentError(
                "SELF_REFERENCE",
                f"instance {instance.id!r} references assembly {document.id!r} inside itself",
            )
    mate_ids: set[str] = set()
    for mate in document.mates:
        if mate.id in mate_ids:
            raise DocumentError("DUPLICATE_ID", f"duplicate mate id {mate.id!r}")
        mate_ids.add(mate.id)
        for endpoint in (mate.a_instance, mate.b_instance):
            if endpoint not in seen:
                raise DocumentError(
                    "UNKNOWN_INSTANCE",
                    f"mate {mate.id!r} names unknown instance {endpoint!r}",
                )


def new_assembly_document(
    name: str = "Untitled",
    document_id: str | None = None,
    seq: int = 0,
    instances: tuple[Instance, ...] = (),
    mates: tuple[Mate, ...] = (),
) -> AssemblyDocument:
    """A new assembly is at version 1 because only committed versions are pinnable."""
    return AssemblyDocument(
        id=document_id or f"a_{uuid.uuid4().hex[:10]}",
        name=name,
        version=1,
        instances=instances,
        mates=mates,
        seq=seq,
    )


def transform_to_json(value: Transform) -> dict[str, Any]:
    return {
        "rotation": [list(row) for row in value.rotation],
        "translation": list(value.translation),
    }


def transform_from_json(payload: Mapping[str, Any]) -> Transform:
    payload = _require_object(payload, "transform")
    _reject_unknown(payload, {"rotation", "translation"}, "transform")
    return Transform(
        rotation=payload.get("rotation", _IDENTITY_ROTATION),
        translation=payload.get("translation", _IDENTITY_TRANSLATION),
    )


def part_ref_to_json(value: PartRef) -> dict[str, Any]:
    return {
        "kind": "part",
        "document_id": value.document_id,
        "version": value.version,
        "configuration": value.configuration,
    }


def part_ref_from_json(payload: Mapping[str, Any]) -> PartRef:
    payload = _require_object(payload, "part reference")
    _reject_unknown(
        payload,
        {"kind", "document_id", "version", "configuration"},
        "part reference",
    )
    kind = payload.get("kind", "part")
    if kind != "part":
        raise DocumentError("INVALID_REF", f"expected a part reference, got {kind!r}")
    return PartRef(
        document_id=_required(payload, "document_id", "part reference"),
        version=_required(payload, "version", "part reference"),
        configuration=payload.get("configuration", "default"),
    )


def assembly_ref_to_json(value: AssemblyRef) -> dict[str, Any]:
    return {
        "kind": "assembly",
        "document_id": value.document_id,
        "version": value.version,
    }


def assembly_ref_from_json(payload: Mapping[str, Any]) -> AssemblyRef:
    payload = _require_object(payload, "assembly reference")
    _reject_unknown(payload, {"kind", "document_id", "version"}, "assembly reference")
    kind = payload.get("kind", "assembly")
    if kind != "assembly":
        raise DocumentError(
            "INVALID_REF", f"expected an assembly reference, got {kind!r}"
        )
    return AssemblyRef(
        document_id=_required(payload, "document_id", "assembly reference"),
        version=_required(payload, "version", "assembly reference"),
    )


def reference_to_json(value: PartRef | AssemblyRef) -> dict[str, Any]:
    if isinstance(value, PartRef):
        return part_ref_to_json(value)
    if isinstance(value, AssemblyRef):
        return assembly_ref_to_json(value)
    raise DocumentError("INVALID_REF", "reference must be a part or assembly reference")


def reference_from_json(payload: Mapping[str, Any]) -> PartRef | AssemblyRef:
    payload = _require_object(payload, "reference")
    kind = payload.get("kind")
    if kind == "part":
        return part_ref_from_json(payload)
    if kind == "assembly":
        return assembly_ref_from_json(payload)
    raise DocumentError("INVALID_REF", f"unknown reference kind {kind!r}")


def instance_to_json(value: Instance) -> dict[str, Any]:
    return {
        "id": value.id,
        "ref": reference_to_json(value.ref),
        "placement": transform_to_json(value.placement),
        "overrides": dict(value.overrides),
        "name": value.name,
        "suppressed": value.suppressed,
        "visible": value.visible,
    }


def instance_from_json(payload: Mapping[str, Any]) -> Instance:
    payload = _require_object(payload, "instance")
    _reject_unknown(
        payload,
        {"id", "ref", "placement", "overrides", "name", "suppressed", "visible"},
        "instance",
    )
    return Instance(
        id=_required(payload, "id", "instance"),
        ref=reference_from_json(_required(payload, "ref", "instance")),
        placement=transform_from_json(_required(payload, "placement", "instance")),
        overrides=payload.get("overrides", {}),
        name=payload.get("name", ""),
        suppressed=payload.get("suppressed", False),
        visible=payload.get("visible", True),
    )


def mate_to_json(value: Mate) -> dict[str, Any]:
    return {
        "id": value.id,
        "a_instance": value.a_instance,
        "b_instance": value.b_instance,
        "kind": value.kind,
        "params": dict(value.params),
    }


def mate_from_json(payload: Mapping[str, Any]) -> Mate:
    payload = _require_object(payload, "mate")
    _reject_unknown(
        payload,
        {"id", "a_instance", "b_instance", "kind", "params"},
        "mate",
    )
    return Mate(
        id=_required(payload, "id", "mate"),
        a_instance=_required(payload, "a_instance", "mate"),
        b_instance=_required(payload, "b_instance", "mate"),
        kind=_required(payload, "kind", "mate"),
        params=payload.get("params", {}),
    )


def assembly_document_to_json(value: AssemblyDocument) -> dict[str, Any]:
    payload = {
        "id": value.id,
        "name": value.name,
        "version": value.version,
        "instances": [instance_to_json(item) for item in value.instances],
        "mates": [mate_to_json(item) for item in value.mates],
        "seq": value.seq,
    }
    if value.generation:
        payload["generation"] = dict(value.generation)
    return payload


def assembly_document_from_json(payload: Mapping[str, Any]) -> AssemblyDocument:
    payload = _require_object(payload, "assembly document")
    _reject_unknown(
        payload,
        {"id", "name", "version", "instances", "mates", "seq", "generation"},
        "assembly document",
    )
    instances = _required(payload, "instances", "assembly document")
    if isinstance(instances, (str, bytes)) or not isinstance(instances, (list, tuple)):
        raise DocumentError(
            "INVALID_JSON", "assembly document instances must be a JSON array"
        )
    mates = payload.get("mates", ())
    if isinstance(mates, (str, bytes)) or not isinstance(mates, (list, tuple)):
        raise DocumentError(
            "INVALID_JSON", "assembly document mates must be a JSON array"
        )
    generation = payload.get("generation") or {}
    if not isinstance(generation, Mapping):
        raise DocumentError(
            "INVALID_JSON", "assembly document generation must be an object"
        )
    return AssemblyDocument(
        id=_required(payload, "id", "assembly document"),
        name=payload.get("name", "Untitled"),
        version=_required(payload, "version", "assembly document"),
        instances=tuple(instance_from_json(item) for item in instances),
        mates=tuple(mate_from_json(item) for item in mates),
        seq=payload.get("seq", 0),
        generation=dict(generation),
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DocumentError("DUPLICATE_FIELD", f"duplicate JSON field {key!r}")
        result[key] = value
    return result


def assembly_document_to_json_text(value: AssemblyDocument) -> str:
    """Canonical text: sorted keys, compact separators, no escaping of unicode."""
    return json.dumps(
        assembly_document_to_json(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def assembly_document_from_json_text(text: str) -> AssemblyDocument:
    if not isinstance(text, str):
        raise DocumentError("INVALID_JSON", "assembly document text must be a string")
    try:
        payload = json.loads(text, object_pairs_hook=_unique_object)
    except json.JSONDecodeError as exc:
        raise DocumentError(
            "INVALID_JSON",
            f"invalid JSON at line {exc.lineno}: {exc.msg}",
        ) from exc
    return assembly_document_from_json(payload)
