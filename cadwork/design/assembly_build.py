"""Resolve an assembly into placed part instances and a recursive BOM.

The build walks instances in document order. A part pin is built once per
(document, version, configuration) and reused for every instance of that pin;
a sub-assembly pin is resolved recursively. A failure is recorded on the
offending instance path and never aborts its siblings, because one stale pin
must not hide the rest of a large assembly.

The result carries kernel shapes for callers that place geometry, plus a
BOM and bbox summary that is safe to hand to a caller that must not receive
geometry.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

# cadwork.smlib re-exports shape builders, not the placement type; an instance
# placement is an arbitrary 4x4 rigid transform, which Location represents.
from smlibpy import Location

from cadwork.design.assembly import (
    AssemblyDocument,
    AssemblyRef,
    Instance,
    PartRef,
    Transform,
    transform_to_json,
)
from cadwork.design.build import BuildCache, BuildResult, build
from cadwork.design.document import Document, canonical_json


class DocumentSource(Protocol):
    """The read surface a build needs from a version store."""

    def get_version(self, document_id: str, version: int) -> Document: ...

    def get_assembly_version(
        self, assembly_id: str, version: int
    ) -> AssemblyDocument: ...


@dataclass(frozen=True)
class AssemblyInstance:
    """One resolved node: a placed part leaf or a sub-assembly frame."""

    path: str
    instance_id: str
    definition_id: str
    definition_kind: str
    version: int
    configuration: str | None
    placement: Transform
    local_placement: Transform
    name: str
    suppressed: bool
    visible: bool
    overrides: Mapping[str, Any] = field(default_factory=dict)
    part: Any | None = None
    error_code: str | None = None
    error_message: str | None = None

    @property
    def ok(self) -> bool:
        return self.error_code is None

    @property
    def is_part(self) -> bool:
        return self.definition_kind == "part"

    def summary(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "instance_id": self.instance_id,
            "definition_id": self.definition_id,
            "definition_kind": self.definition_kind,
            "version": self.version,
            "configuration": self.configuration,
            "placement": transform_to_json(self.placement),
            "local_placement": transform_to_json(self.local_placement),
            "name": self.name,
            "suppressed": self.suppressed,
            "visible": self.visible,
            "overrides": dict(self.overrides),
            "has_geometry": self.part is not None,
            "error": None
            if self.ok
            else {
                "code": self.error_code,
                "message": self.error_message,
            },
        }


@dataclass(frozen=True)
class BomEntry:
    """Recursive quantity of one pinned part definition."""

    document_id: str
    version: int
    configuration: str
    quantity: int
    paths: tuple[str, ...]

    def summary(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "version": self.version,
            "configuration": self.configuration,
            "quantity": self.quantity,
            "paths": list(self.paths),
        }


@dataclass(frozen=True)
class AssemblyBuildResult:
    document_id: str
    version: int
    instances: tuple[AssemblyInstance, ...]
    bom: tuple[BomEntry, ...]
    bbox_min: tuple[float, float, float] | None
    bbox_max: tuple[float, float, float] | None
    part_builds: int = 0
    seconds: float = 0.0
    placed: bool = True

    @property
    def ok(self) -> bool:
        return all(item.ok for item in self.instances)

    @property
    def failures(self) -> tuple[AssemblyInstance, ...]:
        return tuple(item for item in self.instances if not item.ok)

    @property
    def placed_parts(self) -> tuple[AssemblyInstance, ...]:
        return tuple(item for item in self.instances if item.part is not None)

    def summary(self) -> dict[str, Any]:
        bbox = None
        if self.bbox_min is not None and self.bbox_max is not None:
            bbox = {"min": list(self.bbox_min), "max": list(self.bbox_max)}
        return {
            "document_id": self.document_id,
            "version": self.version,
            "ok": self.ok,
            "bbox": bbox,
            "instances": [item.summary() for item in self.instances],
            "bom": [entry.summary() for entry in self.bom],
            "failures": [
                {
                    "path": item.path,
                    "code": item.error_code,
                    "message": item.error_message,
                }
                for item in self.failures
            ],
            "part_builds": self.part_builds,
            "seconds": round(self.seconds, 4),
            "placed": self.placed,
        }


def _compose(parent: Transform, child: Transform) -> Transform:
    """Absolute placement of a child expressed in its parent's frame."""
    rotation = tuple(
        tuple(
            sum(
                parent.rotation[row][axis] * child.rotation[axis][column]
                for axis in range(3)
            )
            for column in range(3)
        )
        for row in range(3)
    )
    translation = tuple(
        sum(parent.rotation[row][axis] * child.translation[axis] for axis in range(3))
        + parent.translation[row]
        for row in range(3)
    )
    return Transform(rotation=rotation, translation=translation)


def _location(transform: Transform) -> Location:
    matrix = np.eye(4)
    matrix[:3, :3] = np.array(transform.rotation, dtype=float)
    matrix[:3, 3] = np.array(transform.translation, dtype=float)
    return Location(matrix)


def _error(exc: Exception) -> tuple[str, str]:
    code = getattr(exc, "code", None) or exc.__class__.__name__
    message = getattr(exc, "message", None) or str(exc) or exc.__class__.__name__
    return str(code), str(message)


class _AssemblyBuilder:
    def __init__(
        self,
        source: DocumentSource,
        cache: BuildCache,
        place: bool = True,
        parts: bool = True,
    ) -> None:
        self.source = source
        self.cache = cache
        self.place = place
        self.parts = parts
        self.part_results: dict[tuple[str, int, str, str], BuildResult] = {}
        self.instances: list[AssemblyInstance] = []
        self.bom_paths: dict[tuple[str, int, str], list[str]] = {}
        self.bbox_min: list[float] | None = None
        self.bbox_max: list[float] | None = None

    def walk(
        self,
        document: AssemblyDocument,
        parent: Transform,
        prefix: str,
        chain: tuple[str, ...],
    ) -> None:
        for instance in document.instances:
            path = f"{prefix}{instance.id}"
            placement = _compose(parent, instance.placement)
            if instance.suppressed:
                self.instances.append(self._node(instance, path, placement))
                continue
            if isinstance(instance.ref, PartRef):
                self._part(instance, instance.ref, path, placement)
            else:
                self._assembly(instance, instance.ref, path, placement, chain)

    def _node(
        self,
        instance: Instance,
        path: str,
        placement: Transform,
        part: Any | None = None,
        error: tuple[str, str] | None = None,
    ) -> AssemblyInstance:
        ref = instance.ref
        return AssemblyInstance(
            path=path,
            instance_id=instance.id,
            definition_id=ref.document_id,
            definition_kind="part" if isinstance(ref, PartRef) else "assembly",
            version=ref.version,
            configuration=ref.configuration if isinstance(ref, PartRef) else None,
            placement=placement,
            local_placement=instance.placement,
            name=instance.name,
            suppressed=instance.suppressed,
            visible=instance.visible,
            overrides=dict(instance.overrides),
            part=part,
            error_code=error[0] if error else None,
            error_message=error[1] if error else None,
        )

    def _part(
        self, instance: Instance, ref: PartRef, path: str, placement: Transform
    ) -> None:
        key = (
            ref.document_id,
            ref.version,
            ref.configuration,
            canonical_json(dict(instance.overrides)),
        )
        if not self.parts:
            self.bom_paths.setdefault(key, []).append(path)
            self.instances.append(self._node(instance, path, placement))
            return
        try:
            result = self.part_results.get(key)
            if result is None:
                document = self.source.get_version(ref.document_id, ref.version)
                result = build(
                    document,
                    self.cache,
                    configuration=ref.configuration,
                    overrides=instance.overrides,
                )
                self.part_results[key] = result
        except Exception as exc:
            self.instances.append(
                self._node(instance, path, placement, error=_error(exc))
            )
            return
        if result.final is None:
            self.instances.append(
                self._node(
                    instance,
                    path,
                    placement,
                    error=(
                        "EMPTY_PART",
                        f"part {ref.document_id!r} version {ref.version} has no geometry",
                    ),
                )
            )
            return
        part = result.final.moved(_location(placement)) if self.place else result.final
        self._add_bbox(part, None if self.place else placement)
        self.bom_paths.setdefault(key, []).append(path)
        self.instances.append(self._node(instance, path, placement, part=part))

    def _assembly(
        self,
        instance: Instance,
        ref: AssemblyRef,
        path: str,
        placement: Transform,
        chain: tuple[str, ...],
    ) -> None:
        if ref.document_id in chain:
            self.instances.append(
                self._node(
                    instance,
                    path,
                    placement,
                    error=(
                        "REF_CYCLE",
                        f"assembly reference cycle: {' -> '.join((*chain, ref.document_id))}",
                    ),
                )
            )
            return
        try:
            child = self.source.get_assembly_version(ref.document_id, ref.version)
        except Exception as exc:
            self.instances.append(
                self._node(instance, path, placement, error=_error(exc))
            )
            return
        self.instances.append(self._node(instance, path, placement))
        self.walk(child, placement, f"{path}/", (*chain, ref.document_id))

    def _add_bbox(self, part: Any, placement: Transform | None = None) -> None:
        box = part.bbox()
        minimum = [float(value) for value in box.min]
        maximum = [float(value) for value in box.max]
        if placement is not None:
            corners = [
                [x, y, z]
                for x in (minimum[0], maximum[0])
                for y in (minimum[1], maximum[1])
                for z in (minimum[2], maximum[2])
            ]
            moved = [
                [
                    sum(
                        placement.rotation[row][axis] * corner[axis]
                        for axis in range(3)
                    )
                    + placement.translation[row]
                    for row in range(3)
                ]
                for corner in corners
            ]
            minimum = [min(point[axis] for point in moved) for axis in range(3)]
            maximum = [max(point[axis] for point in moved) for axis in range(3)]
        if self.bbox_min is None or self.bbox_max is None:
            self.bbox_min, self.bbox_max = minimum, maximum
            return
        self.bbox_min = [min(old, new) for old, new in zip(self.bbox_min, minimum)]
        self.bbox_max = [max(old, new) for old, new in zip(self.bbox_max, maximum)]

    def result(self, document: AssemblyDocument, seconds: float) -> AssemblyBuildResult:
        bom = tuple(
            BomEntry(
                document_id=key[0],
                version=key[1],
                configuration=key[2],
                quantity=len(paths),
                paths=tuple(paths),
            )
            for key, paths in sorted(self.bom_paths.items())
        )
        return AssemblyBuildResult(
            document_id=document.id,
            version=document.version,
            instances=tuple(self.instances),
            bom=bom,
            bbox_min=tuple(self.bbox_min) if self.bbox_min is not None else None,
            bbox_max=tuple(self.bbox_max) if self.bbox_max is not None else None,
            part_builds=len(self.part_results),
            seconds=seconds,
            placed=self.place,
        )


def build_assembly(
    document: AssemblyDocument,
    source: DocumentSource,
    cache: BuildCache | None = None,
    place: bool = True,
    parts: bool = True,
) -> AssemblyBuildResult:
    """Resolve every pin of ``document``; per-instance failures become result errors.

    ``place=False`` keeps each built part local and records the absolute placement;
    a large assembly can then render definitions once instead of copying every B-rep.
    ``parts=False`` skips geometry builds for a fast instance/BOM tree.
    """
    started = time.perf_counter()
    builder = _AssemblyBuilder(
        source, cache if cache is not None else BuildCache(), place=place, parts=parts
    )
    builder.walk(document, Transform(), "", (document.id,))
    return builder.result(document, time.perf_counter() - started)


def count_assembly_instances(
    document: AssemblyDocument, source: DocumentSource, limit: int = 600
) -> int:
    """Count expanded occurrences without building geometry; stop above ``limit``."""
    total = 0
    stack = [(document, (document.id,))]
    while stack:
        current, chain = stack.pop()
        for instance in current.instances:
            total += 1
            if total > limit:
                return total
            if isinstance(instance.ref, AssemblyRef):
                if instance.ref.document_id in chain:
                    continue
                try:
                    child = source.get_assembly_version(
                        instance.ref.document_id, instance.ref.version
                    )
                except Exception:
                    continue
                stack.append((child, (*chain, instance.ref.document_id)))
    return total
