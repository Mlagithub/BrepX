"""Atomic edit operations on an immutable assembly document.

Each operation returns a new version; the input document is never mutated. Edits
that would leave a mate pointing at a removed instance fail before a new version
is produced.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from cadwork.design.assembly import (
    AssemblyDocument,
    AssemblyRef,
    Instance,
    PartRef,
    Transform,
)
from cadwork.design.document import DocumentError


def _find(document: AssemblyDocument, instance_id: str) -> tuple[int, Instance]:
    for index, instance in enumerate(document.instances):
        if instance.id == instance_id:
            return index, instance
    raise DocumentError("UNKNOWN_INSTANCE", f"no instance {instance_id!r}")


def _replace_instance(
    document: AssemblyDocument,
    index: int,
    instance: Instance,
    expected_version: int | None,
) -> AssemblyDocument:
    if expected_version is not None and document.version != expected_version:
        raise DocumentError(
            "STALE_VERSION",
            f"assembly is at version {document.version}, edit expected {expected_version}",
        )
    instances = list(document.instances)
    instances[index] = instance
    return AssemblyDocument(
        id=document.id,
        name=document.name,
        version=document.version + 1,
        instances=tuple(instances),
        mates=document.mates,
        seq=document.seq,
    )


def _commit(
    document: AssemblyDocument, instances: list[Instance], expected_version: int | None
) -> AssemblyDocument:
    if expected_version is not None and document.version != expected_version:
        raise DocumentError(
            "STALE_VERSION",
            f"assembly is at version {document.version}, edit expected {expected_version}",
        )
    return AssemblyDocument(
        id=document.id,
        name=document.name,
        version=document.version + 1,
        instances=tuple(instances),
        mates=document.mates,
        seq=document.seq,
    )


def add_instance(
    document: AssemblyDocument, instance: Instance, expected_version: int | None = None
) -> AssemblyDocument:
    if any(item.id == instance.id for item in document.instances):
        raise DocumentError("DUPLICATE_ID", f"instance {instance.id!r} already exists")
    return _commit(document, [*document.instances, instance], expected_version)


def remove_instance(
    document: AssemblyDocument, instance_id: str, expected_version: int | None = None
) -> AssemblyDocument:
    _find(document, instance_id)
    for mate in document.mates:
        if instance_id in (mate.a_instance, mate.b_instance):
            raise DocumentError(
                "MATE_REFERENCES_INSTANCE",
                f"cannot remove {instance_id!r}: mate {mate.id!r} still references it",
            )
    instances = [item for item in document.instances if item.id != instance_id]
    return _commit(document, instances, expected_version)


def transform_instance(
    document: AssemblyDocument,
    instance_id: str,
    placement: Transform,
    expected_version: int | None = None,
) -> AssemblyDocument:
    index, instance = _find(document, instance_id)
    if not isinstance(placement, Transform):
        raise DocumentError("INVALID_PLACEMENT", "placement must be a Transform")
    return _replace_instance(
        document, index, replace(instance, placement=placement), expected_version
    )


def override_instance(
    document: AssemblyDocument,
    instance_id: str,
    overrides: Mapping[str, Any],
    expected_version: int | None = None,
) -> AssemblyDocument:
    index, instance = _find(document, instance_id)
    merged = dict(instance.overrides)
    merged.update(dict(overrides))
    return _replace_instance(
        document, index, replace(instance, overrides=merged), expected_version
    )


def suppress_instance(
    document: AssemblyDocument,
    instance_id: str,
    suppressed: bool = True,
    expected_version: int | None = None,
) -> AssemblyDocument:
    index, instance = _find(document, instance_id)
    return _replace_instance(
        document, index, replace(instance, suppressed=suppressed), expected_version
    )


def replace_instance(
    document: AssemblyDocument,
    instance_id: str,
    ref: PartRef | AssemblyRef,
    expected_version: int | None = None,
) -> AssemblyDocument:
    index, instance = _find(document, instance_id)
    if not isinstance(ref, (PartRef, AssemblyRef)):
        raise DocumentError("INVALID_REF", "replacement ref must be a pin")
    return _replace_instance(
        document, index, replace(instance, ref=ref), expected_version
    )


def update_pin(
    document: AssemblyDocument,
    instance_id: str,
    *,
    version: int | None = None,
    configuration: str | None = None,
    expected_version: int | None = None,
) -> AssemblyDocument:
    index, instance = _find(document, instance_id)
    ref = instance.ref
    if isinstance(ref, PartRef):
        next_ref = PartRef(
            ref.document_id,
            ref.version if version is None else version,
            ref.configuration if configuration is None else configuration,
        )
    else:
        next_ref = AssemblyRef(
            ref.document_id, ref.version if version is None else version
        )
    return _replace_instance(
        document, index, replace(instance, ref=next_ref), expected_version
    )


def apply_ops(
    document: AssemblyDocument,
    ops: list[Mapping[str, Any]],
    expected_version: int | None = None,
) -> AssemblyDocument:
    """Apply a batch atomically; a failed op leaves the input untouched.

    The batch produces one new version. Intermediate operations are folded back
    to the input version so only the final result carries the version bump.
    """
    if expected_version is not None and document.version != expected_version:
        raise DocumentError(
            "STALE_VERSION",
            f"assembly is at version {document.version}, edit expected {expected_version}",
        )
    current = document
    for index, op in enumerate(ops):
        name = str(op.get("op", ""))
        if name == "add":
            from cadwork.design.assembly import instance_from_json

            current = add_instance(current, instance_from_json(op.get("instance")))
        elif name == "remove":
            current = remove_instance(current, str(op.get("id", "")))
        elif name == "transform":
            from cadwork.design.assembly import transform_from_json

            current = transform_instance(
                current, str(op.get("id", "")), transform_from_json(op.get("placement"))
            )
        elif name == "override":
            current = override_instance(
                current, str(op.get("id", "")), dict(op.get("overrides") or {})
            )
        elif name == "suppress":
            current = suppress_instance(
                current, str(op.get("id", "")), bool(op.get("suppressed", True))
            )
        elif name == "replace":
            from cadwork.design.assembly import reference_from_json

            current = replace_instance(
                current, str(op.get("id", "")), reference_from_json(op.get("ref"))
            )
        elif name == "update_pin":
            current = update_pin(
                current,
                str(op.get("id", "")),
                version=op.get("version"),
                configuration=op.get("configuration"),
            )
        else:
            raise DocumentError("INVALID_OP", f"unknown assembly op {name!r}")
        if index < len(ops) - 1:
            current = replace(current, version=document.version)
    return current


__all__ = [
    "add_instance",
    "apply_ops",
    "override_instance",
    "remove_instance",
    "replace_instance",
    "suppress_instance",
    "transform_instance",
    "update_pin",
]
