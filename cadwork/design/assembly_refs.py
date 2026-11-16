"""Reference status, explicit pin updates and BOM projection for assemblies."""

from __future__ import annotations

from collections import Counter
from typing import Any

from cadwork.design.assembly import AssemblyDocument, AssemblyRef, PartRef
from cadwork.design.document import DocumentError


def _part_current(store: Any, document_id: str) -> int:
    return store.get(document_id).version


def _assembly_current(store: Any, document_id: str) -> int:
    return store.get_assembly(document_id).version


def reference_status(document: AssemblyDocument, store: Any) -> list[dict[str, Any]]:
    """Describe every pin against the store without modifying anything."""
    rows: list[dict[str, Any]] = []
    for instance in document.instances:
        ref = instance.ref
        kind = "part" if isinstance(ref, PartRef) else "assembly"
        try:
            current = (
                _part_current(store, ref.document_id)
                if kind == "part"
                else _assembly_current(store, ref.document_id)
            )
            available = True
            configuration_ok = True
            if (
                kind == "part"
                and isinstance(ref, PartRef)
                and ref.configuration != "default"
            ):
                configuration_ok = (
                    ref.configuration in store.get(ref.document_id).configurations
                )
        except Exception:
            current = None
            available = False
            configuration_ok = False
        rows.append(
            {
                "instance_id": instance.id,
                "name": instance.name or instance.id,
                "kind": kind,
                "document_id": ref.document_id,
                "pinned_version": ref.version,
                "current_version": current,
                "configuration": getattr(ref, "configuration", None),
                "available": available,
                "configuration_ok": configuration_ok,
                "outdated": available
                and current is not None
                and current != ref.version,
            }
        )
    return rows


def reference_diff(document: AssemblyDocument, store: Any) -> list[dict[str, Any]]:
    return [row for row in reference_status(document, store) if row["outdated"]]


def update_references(
    document: AssemblyDocument,
    store: Any,
    instance_ids: set[str] | None = None,
    expected_version: int | None = None,
) -> AssemblyDocument:
    """Pin selected instances to the store's current versions in one new version."""
    if expected_version is not None and document.version != expected_version:
        raise DocumentError(
            "STALE_VERSION",
            f"assembly is at version {document.version}, edit expected {expected_version}",
        )
    selected = set(instance_ids) if instance_ids is not None else None
    updated = []
    changed = 0
    for instance in document.instances:
        if selected is not None and instance.id not in selected:
            updated.append(instance)
            continue
        ref = instance.ref
        if isinstance(ref, PartRef):
            current = store.get(ref.document_id)
            if (
                ref.configuration != "default"
                and ref.configuration not in current.configurations
            ):
                raise DocumentError(
                    "REF_CONFIG_NOT_FOUND",
                    f"instance {instance.id!r} keeps missing configuration "
                    f"{ref.configuration!r}",
                )
            next_ref = PartRef(ref.document_id, current.version, ref.configuration)
        else:
            next_ref = AssemblyRef(
                ref.document_id, store.get_assembly(ref.document_id).version
            )
        if next_ref != ref:
            changed += 1
        updated.append(
            type(instance)(
                id=instance.id,
                ref=next_ref,
                placement=instance.placement,
                overrides=instance.overrides,
                name=instance.name,
                suppressed=instance.suppressed,
                visible=instance.visible,
            )
        )
    if changed == 0:
        return document
    candidate = AssemblyDocument(
        id=document.id,
        name=document.name,
        version=document.version + 1,
        instances=tuple(updated),
        mates=document.mates,
        seq=document.seq,
    )
    store.validate_assembly_references(candidate)
    return candidate


def bom_rows(
    document: AssemblyDocument, store: Any, prefix: str = ""
) -> list[dict[str, Any]]:
    """Flatten the tree into one row per instance, including subassemblies."""
    rows: list[dict[str, Any]] = []
    for instance in document.instances:
        path = f"{prefix}/{instance.name or instance.id}".lstrip("/")
        ref = instance.ref
        row = {
            "path": path,
            "instance_id": instance.id,
            "name": instance.name or instance.id,
            "suppressed": instance.suppressed,
            "document_id": ref.document_id,
            "version": ref.version,
            "configuration": getattr(ref, "configuration", None),
            "kind": "part" if isinstance(ref, PartRef) else "assembly",
        }
        rows.append(row)
        if isinstance(ref, AssemblyRef) and not instance.suppressed:
            child = store.get_assembly_version(ref.document_id, ref.version)
            rows.extend(bom_rows(child, store, path))
    return rows


def bom_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(
        (row["document_id"], row["version"], row["configuration"], row["kind"])
        for row in rows
        if row["kind"] == "part" and not row["suppressed"]
    )
    return [
        {
            "document_id": key[0],
            "version": key[1],
            "configuration": key[2],
            "kind": key[3],
            "quantity": count,
        }
        for key, count in sorted(counts.items())
    ]


__all__ = [
    "bom_rows",
    "bom_summary",
    "reference_diff",
    "reference_status",
    "update_references",
]
