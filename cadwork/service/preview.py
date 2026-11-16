"""Pack assembly scene geometry into one local mesh per definition and placed rows.

The assembly scene is already the deduplicated projection of placed instances:
each scene definition carries one local mesh and each scene instance carries the
placement that puts that mesh into assembly coordinates. Packing therefore only
offsets every face's triangle indices into a shared position buffer, expands
edge polylines into line-list pairs, and transposes the scene rotation into the
column-major matrix the preview wire format stores.

Packing does not mint content keys or bundle bytes. It keeps the exact scene
definition identity so a later stage can address prototypes by content, and it
drops rows that cannot be rendered: a sub-assembly frame, a suppressed row, a
failed definition, or any instance without a built definition has no mesh to
reference. Those rows remain visible through the scene-level counters so a
caller can still explain why the preview is smaller than the scene.
"""

from __future__ import annotations

import hashlib
import math
import re
import threading
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from cadwork.design.document import canonical_json

from .preview_format import (
    MANIFEST_SCHEMA,
    MANIFEST_SCHEMA_VERSION,
    MANIFEST_UNITS,
    PreviewFormatError,
    align8,
    bundle_key as _format_bundle_key,
    decode_bundle,
    encode_bundle,
    pack_prototype_blob,
    prototype_blob_size,
    prototype_key as _format_prototype_key,
    prototype_mesh_digest,
    validate_manifest,
)

if TYPE_CHECKING:
    from cadwork.service.store import Store

DEFAULT_COLOR = "#b6c9d7"
DEFAULT_OPACITY = 1.0
FACE_KEY_SOURCE = "ordinal"
GENERATOR_VERSION = "1"
TESSELLATION_PROFILE = "assembly-preview-default"
PREVIEW_MEDIA_TYPE = "application/vnd.brepx.assembly-preview"
_PREVIEW_KEY_PATTERN = re.compile(r"[0-9a-f]{64}")
_KERNEL_VERSION: str | None = None

_IDENTITY_ROTATION = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)
_ZERO_TRANSLATION = (0.0, 0.0, 0.0)


class PreviewError(Exception):
    """A scene projection cannot be packed without losing identity or shape.

    ``code`` is a stable identifier; the message names the first violated
    invariant. Packing stops at that point because continuing would attach
    vertices, face ids, or instance rows to the wrong prototype.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PrototypeMesh:
    """One local mesh in preview array order.

    Positions and edge points are flat XYZ triples; indices address positions
    by vertex, and ``face_ids`` holds one face-key slot per triangle.
    """

    positions: tuple[float, ...]
    indices: tuple[int, ...]
    face_ids: tuple[int, ...]
    edge_points: tuple[float, ...]

    @property
    def position_count(self) -> int:
        return len(self.positions) // 3

    @property
    def index_count(self) -> int:
        return len(self.indices)

    @property
    def edge_point_count(self) -> int:
        return len(self.edge_points) // 3


@dataclass(frozen=True)
class Prototype:
    """One mesh shared by every instance of the same scene definition."""

    source_definition_key: str
    source_document_id: str
    source_version: int
    source_identity: str
    face_key_source: str
    face_keys: tuple[str, ...]
    bounds: tuple[
        tuple[float, float, float], tuple[float, float, float]
    ]
    metrics: Mapping[str, float | int]
    mesh: PrototypeMesh

    @property
    def face_count(self) -> int:
        return len(self.face_keys)


@dataclass(frozen=True)
class PreviewInstance:
    """One renderable placement of a prototype in assembly coordinates."""

    path: str
    parent_path: str
    instance_id: str
    source_definition_key: str
    matrix: tuple[float, ...]
    color: str
    opacity: float
    visible: bool
    suppressed: bool
    module: str


@dataclass(frozen=True)
class PackedScene:
    """Prototypes, renderable rows, and the scene totals they were selected from.

    The counters are independent flags, not a partition: a suppressed
    sub-assembly is counted by both ``frame_count`` and ``suppressed_count``.
    They exist so a caller can report why ``instances`` is shorter than
    ``scene_instance_count``.
    """

    prototypes: Mapping[str, Prototype]
    instances: tuple[PreviewInstance, ...]
    scene_instance_count: int
    frame_count: int
    failed_count: int
    suppressed_count: int

    @property
    def prototype_count(self) -> int:
        return len(self.prototypes)

    @property
    def instance_count(self) -> int:
        return len(self.instances)


def pack_prototypes(
    definitions: Mapping[str, Mapping[str, Any]],
) -> dict[str, Prototype]:
    """Build one prototype per scene definition in scene order.

    The mapping key and the definition's ``feature`` field are the same
    canonical identity. A disagreement is rejected instead of guessed: the face
    keys would otherwise name one document version while the prototype would be
    addressed by another.
    """
    if not isinstance(definitions, Mapping):
        raise PreviewError("BAD_SCENE", "definitions must be a mapping")
    prototypes: dict[str, Prototype] = {}
    for key, definition in definitions.items():
        prototypes[key] = _pack_prototype(key, definition)
    return prototypes


def pack_instances(
    instances: Sequence[Mapping[str, Any]],
    prototypes: Mapping[str, Prototype],
) -> tuple[PreviewInstance, ...]:
    """Select rows with a built definition and convert their placements.

    A row stays in the result when it has a definition key that resolves to a
    packed prototype and is neither suppressed nor failed; ``visible=False`` is
    kept because visibility is a render-time filter, not a geometry property.
    """
    if isinstance(instances, (str, bytes)) or not isinstance(instances, Sequence):
        raise PreviewError("BAD_SCENE", "instances must be an array")
    if not isinstance(prototypes, Mapping):
        raise PreviewError("BAD_SCENE", "prototypes must be a mapping")
    rows: list[PreviewInstance] = []
    seen_paths: set[str] = set()
    for index, raw in enumerate(instances):
        if not isinstance(raw, Mapping):
            raise PreviewError(
                "BAD_SCENE", f"instances[{index}] must be a mapping"
            )
        if not _is_renderable(raw, prototypes):
            continue
        parts = _path_parts(raw.get("path"))
        path = "/".join(parts)
        if path in seen_paths:
            raise PreviewError(
                "DUPLICATE_INSTANCE_PATH", f"duplicate instance path {path!r}"
            )
        seen_paths.add(path)
        rows.append(
            PreviewInstance(
                path=path,
                parent_path="/".join(parts[:-1]),
                instance_id=_require_text(
                    raw.get("instance_id"), f"instances[{index}].instance_id"
                ),
                source_definition_key=str(raw["definition_key"]),
                matrix=instance_matrix(raw.get("placement")),
                color=DEFAULT_COLOR,
                opacity=DEFAULT_OPACITY,
                visible=_require_bool(
                    raw.get("visible", True), f"instances[{index}].visible"
                ),
                suppressed=False,
                module=parts[0],
            )
        )
    return tuple(rows)


def pack_scene(scene: Mapping[str, Any]) -> PackedScene:
    """Pack every definition and renderable instance of one assembly scene."""
    if not isinstance(scene, Mapping):
        raise PreviewError("BAD_SCENE", "scene must be a mapping")
    definitions = scene.get("definitions", {})
    instances = scene.get("instances", ())
    if not isinstance(definitions, Mapping):
        raise PreviewError("BAD_SCENE", "scene definitions must be a mapping")
    if isinstance(instances, (str, bytes)) or not isinstance(instances, Sequence):
        raise PreviewError("BAD_SCENE", "scene instances must be an array")
    prototypes = pack_prototypes(definitions)
    rows = pack_instances(instances, prototypes)
    return PackedScene(
        prototypes=prototypes,
        instances=rows,
        scene_instance_count=len(instances),
        frame_count=sum(
            1
            for item in instances
            if item.get("definition_kind") == "assembly"
        ),
        failed_count=sum(
            1 for item in instances if item.get("error") is not None
        ),
        suppressed_count=sum(
            1 for item in instances if item.get("suppressed") is True
        ),
    )


def instance_matrix(placement: Mapping[str, Any] | None) -> tuple[float, ...]:
    """Encode a scene placement as a column-major 4x4 matrix.

    Scene rotation is row-major, so ``rotation[row][column]`` multiplies point
    component ``column``. A column-major array stores one matrix column per
    four entries, which puts transposed scene rows into successive columns;
    copying the scene rows directly would mirror every rotation.
    """
    if placement is None:
        rows = _IDENTITY_ROTATION
        translation = _ZERO_TRANSLATION
    else:
        if not isinstance(placement, Mapping):
            raise PreviewError("BAD_PLACEMENT", "placement must be a mapping")
        rows = _rotation(placement.get("rotation", _IDENTITY_ROTATION))
        translation = _translation(
            placement.get("translation", _ZERO_TRANSLATION)
        )
    return (
        rows[0][0],
        rows[1][0],
        rows[2][0],
        0.0,
        rows[0][1],
        rows[1][1],
        rows[2][1],
        0.0,
        rows[0][2],
        rows[1][2],
        rows[2][2],
        0.0,
        translation[0],
        translation[1],
        translation[2],
        1.0,
    )


def _pack_prototype(key: str, definition: Mapping[str, Any]) -> Prototype:
    if not isinstance(key, str) or not key:
        raise PreviewError("BAD_SCENE", "a definition key must be non-empty text")
    if not isinstance(definition, Mapping):
        raise PreviewError("BAD_SCENE", f"definition {key!r} must be a mapping")
    feature = definition.get("feature")
    if not isinstance(feature, str) or not feature:
        raise PreviewError(
            "BAD_DEFINITION", f"definition {key!r} has no feature key"
        )
    if feature != key:
        raise PreviewError(
            "DEFINITION_KEY_MISMATCH",
            f"definition key {key!r} does not match feature {feature!r}",
        )
    document_id = _require_text(
        definition.get("definition_id"),
        f"definition {key!r} document id",
    )
    version = _require_count(
        definition.get("version"), f"definition {key!r} version"
    )
    configuration = _require_text(
        definition.get("configuration"),
        f"definition {key!r} configuration",
    )
    overrides = definition.get("overrides", {})
    if not isinstance(overrides, Mapping):
        raise PreviewError(
            "BAD_DEFINITION", f"definition {key!r} overrides must be a mapping"
        )
    try:
        identity = (
            f"{document_id}@{version}#{configuration}#"
            f"{canonical_json(dict(overrides))}"
        )
    except (TypeError, ValueError) as exc:
        raise PreviewError(
            "BAD_DEFINITION",
            f"definition {key!r} override set is not canonical JSON: {exc}",
        ) from exc
    if identity != key:
        # Older assembly-scene caches omitted the empty override segment:
        # ``doc@version#configuration`` instead of ``doc@version#configuration#{}``.
        # The geometry is identical when overrides are empty, so normalize the
        # identity for prototype addressing instead of rejecting a readable cache.
        legacy_identity = f"{document_id}@{version}#{configuration}"
        if overrides or key != legacy_identity:
            raise PreviewError(
                "DEFINITION_KEY_MISMATCH",
                f"definition key {key!r} does not match identity {identity!r}",
            )

    faces = _require_sequence(definition.get("faces", ()), "definition faces")
    positions: list[float] = []
    indices: list[int] = []
    face_ids: list[int] = []
    face_keys: list[str] = []
    seen_face_keys: set[str] = set()
    for face_index, face in enumerate(faces):
        if not isinstance(face, Mapping):
            raise PreviewError(
                "BAD_DEFINITION", f"definition {key!r} face {face_index} is not a mapping"
            )
        ordinal = face.get("index")
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
            raise PreviewError(
                "BAD_FACE_INDEX",
                f"definition {key!r} face {face_index} has no non-negative index",
            )
        face_key = f"{feature}:{ordinal}"
        # The scene index is the kernel face ordinal, not the emitted-list slot.
        # Keeping it means a face that failed tessellation cannot renumber the
        # keys of the faces that did survive.
        if face_key in seen_face_keys:
            raise PreviewError(
                "DUPLICATE_FACE_KEY",
                f"definition {key!r} repeats face key {face_key!r}",
            )
        seen_face_keys.add(face_key)
        slot = len(face_keys)
        face_keys.append(face_key)

        vertices = _require_sequence(
            face.get("vertices", ()), f"definition {key!r} face {ordinal} vertices"
        )
        points = _points(
            vertices, f"definition {key!r} face {ordinal} vertex"
        )
        base = len(positions) // 3
        positions.extend(points)
        local_count = len(points) // 3

        triangles = _require_sequence(
            face.get("triangles", ()),
            f"definition {key!r} face {ordinal} triangles",
        )
        if len(triangles) % 3:
            raise PreviewError(
                "BAD_INDEX_COUNT",
                f"definition {key!r} face {ordinal} triangles are incomplete",
            )
        for value in triangles:
            if isinstance(value, bool) or not isinstance(value, int):
                raise PreviewError(
                    "BAD_MESH",
                    f"definition {key!r} face {ordinal} triangle index is not an integer",
                )
            if value < 0 or value >= local_count:
                raise PreviewError(
                    "BAD_INDEX",
                    f"definition {key!r} face {ordinal} index {value} "
                    f"is outside its {local_count} vertices",
                )
            indices.append(base + value)
        # faceIds address the faceKeys array, so they stay dense even when the
        # scene face ordinals are sparse.
        face_ids.extend([slot] * (len(triangles) // 3))

    edges = _require_sequence(definition.get("edges", ()), "definition edges")
    edge_points: list[float] = []
    for edge_index, edge in enumerate(edges):
        if not isinstance(edge, Mapping):
            raise PreviewError(
                "BAD_DEFINITION",
                f"definition {key!r} edge {edge_index} is not a mapping",
            )
        points = _require_sequence(
            edge.get("points", ()), f"definition {key!r} edge {edge_index} points"
        )
        coordinates = _points(
            points, f"definition {key!r} edge {edge_index} point"
        )
        point_count = len(coordinates) // 3
        if point_count < 2:
            raise PreviewError(
                "BAD_EDGE_COUNT",
                f"definition {key!r} edge {edge_index} needs at least two points",
            )
        for step in range(point_count - 1):
            start = step * 3
            following = start + 3
            edge_points.extend(coordinates[start:following])
            edge_points.extend(coordinates[following : following + 3])

    position_tuple = tuple(positions)
    mesh = PrototypeMesh(
        positions=position_tuple,
        indices=tuple(indices),
        face_ids=tuple(face_ids),
        edge_points=tuple(edge_points),
    )
    return Prototype(
        source_definition_key=key,
        source_document_id=document_id,
        source_version=version,
        source_identity=identity,
        face_key_source=FACE_KEY_SOURCE,
        face_keys=tuple(face_keys),
        bounds=_bounds(position_tuple),
        metrics=_metrics(definition.get("metrics"), faces, face_keys, edges),
        mesh=mesh,
    )


def _metrics(
    source: Any,
    faces: Sequence[Mapping[str, Any]],
    face_keys: Sequence[str],
    edges: Sequence[Mapping[str, Any]],
) -> dict[str, float | int]:
    if source is None:
        source = {}
    if not isinstance(source, Mapping):
        raise PreviewError("BAD_METRICS", "definition metrics must be a mapping")
    volume = _finite(source.get("volume", 0.0), "definition volume")
    face_count = _require_count(
        source.get("faces", len(face_keys)), "definition face count"
    )
    edge_count = _require_count(
        source.get("edges", len(edges)), "definition edge count"
    )
    area = 0.0
    for face in faces:
        value = face.get("area")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        number = float(value)
        if math.isfinite(number):
            area += number
    if not math.isfinite(area):
        raise PreviewError("BAD_METRICS", "definition face area sum is not finite")
    return {
        "volume": volume,
        "area": area,
        "faces": face_count,
        "edges": edge_count,
    }


def _bounds(
    positions: tuple[float, ...],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if not positions:
        return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    minimum = tuple(min(positions[axis::3]) for axis in range(3))
    maximum = tuple(max(positions[axis::3]) for axis in range(3))
    return (minimum, maximum)


def _is_renderable(
    instance: Mapping[str, Any], prototypes: Mapping[str, Prototype]
) -> bool:
    if instance.get("error") is not None:
        return False
    if instance.get("suppressed") is True:
        return False
    if instance.get("definition_kind", "part") != "part":
        return False
    key = instance.get("definition_key")
    return isinstance(key, str) and key in prototypes


def _path_parts(value: Any) -> tuple[str, ...]:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PreviewError(
            "BAD_INSTANCE_PATH", "instance path must be non-empty text"
        )
    parts = tuple(value.split("/"))
    if any(not part for part in parts):
        raise PreviewError(
            "BAD_INSTANCE_PATH", f"instance path {value!r} has an empty segment"
        )
    return parts


def _rotation(value: Any) -> tuple[tuple[float, float, float], ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise PreviewError("BAD_PLACEMENT", "rotation must be a 3x3 array")
    if len(value) != 3:
        raise PreviewError("BAD_PLACEMENT", "rotation must have exactly 3 rows")
    rows: list[tuple[float, float, float]] = []
    for row_index, row in enumerate(value):
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence):
            raise PreviewError(
                "BAD_PLACEMENT", f"rotation row {row_index} must be an array"
            )
        if len(row) != 3:
            raise PreviewError(
                "BAD_PLACEMENT", f"rotation row {row_index} must hold 3 numbers"
            )
        rows.append(
            tuple(
                _finite(item, f"rotation[{row_index}]") for item in row
            )  # type: ignore[arg-type]
        )
    return tuple(rows)


def _translation(value: Any) -> tuple[float, float, float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise PreviewError("BAD_PLACEMENT", "translation must be an array")
    if len(value) != 3:
        raise PreviewError("BAD_PLACEMENT", "translation must hold 3 numbers")
    return tuple(
        _finite(item, "translation") for item in value
    )  # type: ignore[return-value]


def _points(values: Sequence[Any], label: str) -> list[float]:
    """Flatten a scene point list; the scene stores one XYZ triple per point."""
    flat: list[float] = []
    for point_index, point in enumerate(values):
        if isinstance(point, (str, bytes)) or not isinstance(point, Sequence):
            raise PreviewError(
                "BAD_MESH", f"{label} {point_index} must be an XYZ array"
            )
        if len(point) != 3:
            raise PreviewError(
                "BAD_MESH", f"{label} {point_index} must hold 3 numbers"
            )
        flat.extend(
            _finite(coordinate, f"{label} {point_index}") for coordinate in point
        )
    return flat


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PreviewError("BAD_MESH", f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise PreviewError("BAD_MESH", f"{label} must be finite")
    return number


def _require_sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise PreviewError("BAD_SCENE", f"{label} must be an array")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PreviewError("BAD_SCENE", f"{label} must be non-empty text")
    return value


def _require_count(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PreviewError(
            "BAD_SCENE", f"{label} must be a non-negative integer"
        )
    return value


def _require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise PreviewError("BAD_SCENE", f"{label} must be a boolean")
    return value


def default_kernel_version() -> str:
    """The kernel build that produced the tessellation, resolved once per process."""
    global _KERNEL_VERSION
    if _KERNEL_VERSION is None:
        from cadwork.smlib import VERSION

        _KERNEL_VERSION = f"smlibpy {VERSION}"
    return _KERNEL_VERSION


def is_preview_key(value: Any) -> bool:
    return isinstance(value, str) and _PREVIEW_KEY_PATTERN.fullmatch(value) is not None


def overrides_digest(overrides: Mapping[str, Any] | None = None) -> str:
    """SHA-256 of the canonical override object, including the empty object.

    The digest is part of the preview identity, so an absent override set and an
    explicitly empty one must hash to the same value rather than to no value.
    """
    if overrides is None:
        payload: dict[str, Any] = {}
    elif isinstance(overrides, Mapping):
        payload = dict(overrides)
    else:
        raise PreviewError("BAD_KEY_INPUT", "overrides must be a mapping")
    try:
        text = canonical_json(payload)
    except (TypeError, ValueError) as exc:
        raise PreviewError(
            "BAD_KEY_INPUT", f"overrides are not canonical JSON: {exc}"
        ) from exc
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def preview_key(
    *,
    assembly_id: str,
    assembly_version: int,
    configuration: str,
    overrides: Mapping[str, Any] | None = None,
    generator_version: str = GENERATOR_VERSION,
    kernel_version: str | None = None,
    tessellation_profile: str = TESSELLATION_PROFILE,
    schema_version: int = MANIFEST_SCHEMA_VERSION,
) -> str:
    """Identity of one derived assembly preview.

    Every input that can change the rendered result participates: the pinned
    assembly version and configuration, the assembly-wide overrides, the
    generator, kernel, tessellation profile, and schema version. A change in any
    of them therefore misses every older cache entry instead of aliasing it.
    """
    assembly = _key_text(assembly_id, "assembly id")
    version = _key_count(assembly_version, "assembly version", minimum=1)
    config = _key_text(configuration, "configuration")
    generator = _key_text(generator_version, "generator version")
    kernel = _key_text(
        kernel_version or default_kernel_version(), "kernel version"
    )
    profile = _key_text(tessellation_profile, "tessellation profile")
    schema = _key_count(schema_version, "schema version", minimum=1)
    material = "\n".join(
        (
            "brepx-preview",
            str(schema),
            assembly,
            str(version),
            config,
            overrides_digest(overrides),
            generator,
            kernel,
            profile,
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def prototype_blob(prototype: Prototype) -> bytes:
    """The exact unpadded array bytes of one prototype in wire order."""
    return pack_prototype_blob(
        prototype.mesh.positions,
        prototype.mesh.indices,
        prototype.mesh.face_ids,
        prototype.mesh.edge_points,
    )


def prototype_key_for(
    prototype: Prototype,
    *,
    schema_version: int = MANIFEST_SCHEMA_VERSION,
    tessellation_profile: str = TESSELLATION_PROFILE,
    kernel_version: str | None = None,
    blob: bytes | None = None,
) -> str:
    """Content key of one prototype under the current generator profile.

    ``blob`` lets a caller that already packed the arrays avoid packing them a
    second time; the digest always covers those exact array bytes.
    """
    payload = prototype_blob(prototype) if blob is None else bytes(blob)
    schema = _key_count(schema_version, "schema version", minimum=1)
    profile = _key_text(tessellation_profile, "tessellation profile")
    kernel = _key_text(
        kernel_version or default_kernel_version(), "kernel version"
    )
    return _format_prototype_key(
        schema_version=schema,
        source_identity=prototype.source_identity,
        tessellation_profile=profile,
        kernel_version=kernel,
        mesh_digest=prototype_mesh_digest(payload),
    )


@dataclass(frozen=True)
class PreviewPlan:
    """Everything needed to publish one preview, before any bytes are written."""

    preview_key: str
    bundle_key: str
    manifest: Mapping[str, Any]
    bundle: bytes
    prototype_blobs: Mapping[str, bytes]
    prototype_keys: Mapping[str, str]


@dataclass(frozen=True)
class StoredPreview:
    """A complete preview as it exists in the cache."""

    preview_key: str
    bundle_key: str
    manifest: Mapping[str, Any]
    bundle: bytes


def plan_preview(
    scene: Mapping[str, Any],
    *,
    assembly_id: str,
    assembly_version: int,
    configuration: str = "default",
    name: str = "",
    overrides: Mapping[str, Any] | None = None,
    generator_version: str = GENERATOR_VERSION,
    kernel_version: str | None = None,
    tessellation_profile: str = TESSELLATION_PROFILE,
    schema_version: int = MANIFEST_SCHEMA_VERSION,
) -> PreviewPlan:
    """Derive prototype keys, the manifest, and canonical bundle bytes.

    Nothing is written here, so a caller can validate or reuse a plan before it
    decides to publish it. Prototype keys are assigned even when the blob is
    already cached; the store's content-addressed path makes the write a no-op.
    """
    assembly = _key_text(assembly_id, "assembly id")
    version = _key_count(assembly_version, "assembly version", minimum=1)
    config = _key_text(configuration, "configuration")
    generator = _key_text(generator_version, "generator version")
    kernel = _key_text(
        kernel_version or default_kernel_version(), "kernel version"
    )
    profile = _key_text(tessellation_profile, "tessellation profile")
    schema = _key_count(schema_version, "schema version", minimum=1)
    if not isinstance(name, str):
        raise PreviewError("BAD_KEY_INPUT", "assembly name must be text")
    key = preview_key(
        assembly_id=assembly,
        assembly_version=version,
        configuration=config,
        overrides=overrides,
        generator_version=generator,
        kernel_version=kernel,
        tessellation_profile=profile,
        schema_version=schema,
    )
    packed = pack_scene(scene)
    prototype_records: list[dict[str, Any]] = []
    prototype_blobs: dict[str, bytes] = {}
    prototype_keys: dict[str, str] = {}
    offset = 0
    for definition_key, prototype in packed.prototypes.items():
        blob = prototype_blob(prototype)
        prototype_key_value = prototype_key_for(
            prototype,
            schema_version=schema,
            tessellation_profile=profile,
            kernel_version=kernel,
            blob=blob,
        )
        if prototype_key_value in prototype_blobs:
            raise PreviewError(
                "DUPLICATE_PROTOTYPE_KEY",
                f"two definitions share prototype key {prototype_key_value}",
            )
        size = prototype_blob_size(
            prototype.mesh.position_count,
            prototype.mesh.index_count,
            prototype.mesh.edge_point_count,
        )
        if len(blob) != size:
            raise PreviewError(
                "BAD_PROTOTYPE_BLOB",
                f"prototype {prototype_key_value} packed to {len(blob)} bytes, "
                f"expected {size}",
            )
        allocated = align8(size)
        prototype_records.append(
            {
                "prototypeKey": prototype_key_value,
                "sourceDocumentId": prototype.source_document_id,
                "sourceVersion": prototype.source_version,
                "sourceDefinitionKey": prototype.source_definition_key,
                "sourceIdentity": prototype.source_identity,
                "faceKeySource": prototype.face_key_source,
                "faceKeys": list(prototype.face_keys),
                "bounds": [
                    list(prototype.bounds[0]),
                    list(prototype.bounds[1]),
                ],
                "metrics": dict(prototype.metrics),
                "mesh": {
                    "offset": offset,
                    "blobLength": allocated,
                    "positionCount": prototype.mesh.position_count,
                    "indexCount": prototype.mesh.index_count,
                    "faceCount": prototype.face_count,
                    "edgePointCount": prototype.mesh.edge_point_count,
                },
            }
        )
        prototype_blobs[prototype_key_value] = blob
        prototype_keys[definition_key] = prototype_key_value
        offset += allocated

    instance_records: list[dict[str, Any]] = []
    for row in packed.instances:
        prototype_key_value = prototype_keys.get(row.source_definition_key)
        if prototype_key_value is None:
            raise PreviewError(
                "MISSING_PROTOTYPE",
                f"instance {row.path!r} has no packed prototype",
            )
        instance_records.append(
            {
                "path": row.path,
                "parentPath": row.parent_path,
                "instanceId": row.instance_id,
                "prototypeKey": prototype_key_value,
                "sourceDefinitionKey": row.source_definition_key,
                "matrix": list(row.matrix),
                "color": row.color,
                "opacity": row.opacity,
                "visible": row.visible,
                "suppressed": row.suppressed,
                "module": row.module,
            }
        )

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "schemaVersion": schema,
        "previewKey": key,
        "assembly": {
            "id": assembly,
            "version": version,
            "configuration": config,
            "name": name,
        },
        "generator": {
            "version": generator,
            "kernel": kernel,
            "tessellationProfile": profile,
        },
        "units": MANIFEST_UNITS,
        "rootOffset": [0.0, 0.0, 0.0],
        "prototypeCount": len(prototype_records),
        "instanceCount": len(instance_records),
        "sceneInstanceCount": packed.scene_instance_count,
        "leafCount": len(instance_records),
        "frameCount": packed.frame_count,
        "failedCount": packed.failed_count,
        "suppressedCount": packed.suppressed_count,
        "bom": _preview_bom(scene),
        "prototypes": prototype_records,
        "instances": instance_records,
    }
    validate_manifest(manifest)
    bundle = encode_bundle(manifest, prototype_blobs)
    content_key = _format_bundle_key(bundle)
    return PreviewPlan(
        preview_key=key,
        bundle_key=content_key,
        manifest=manifest,
        bundle=bundle,
        prototype_blobs=prototype_blobs,
        prototype_keys=prototype_keys,
    )


def write_preview(store: "Store", plan: PreviewPlan) -> StoredPreview:
    """Publish prototypes, then the content-addressed bundle, then the lookup.

    The lookup manifest is the completion marker: readers treat a missing or
    invalid lookup as a miss. It carries ``bundleKey`` so a warm read resolves
    the exact bytes without re-tessellating. Writing it last means a failure at
    any earlier step leaves the previous complete lookup in place.
    """
    with store.preview_cache_lock:
        for prototype_key_value, blob in plan.prototype_blobs.items():
            store.put_preview_prototype(prototype_key_value, blob)
        store.put_preview_bundle(plan.bundle_key, plan.bundle)
        lookup = dict(plan.manifest)
        lookup["bundleKey"] = plan.bundle_key
        store.put_preview_manifest(plan.preview_key, lookup)
    return StoredPreview(
        preview_key=plan.preview_key,
        bundle_key=plan.bundle_key,
        manifest=plan.manifest,
        bundle=plan.bundle,
    )


def load_preview(store: "Store", preview_key: str) -> StoredPreview | None:
    """A complete validated preview, or a miss.

    The lookup manifest names one content-addressed bundle; the bundle bytes are
    hashed again and checked against ``bundleKey`` before any array is trusted.
    Validation covers the manifest structure, the bundle container and arrays,
    and agreement between the lookup record and the embedded manifest. A defect
    is ignored rather than repaired, so the caller can regenerate without
    deleting a previous complete preview.
    """
    if not is_preview_key(preview_key):
        return None
    lookup = store.get_preview_manifest(preview_key)
    if lookup is None:
        return None
    content_key = lookup.get("bundleKey")
    if not is_preview_key(content_key):
        return None
    bundle = store.get_preview_bundle(content_key)
    if bundle is None:
        return None
    if _format_bundle_key(bundle) != content_key:
        return None
    try:
        decoded = decode_bundle(bundle)
    except (PreviewFormatError, ValueError, TypeError):
        return None
    embedded = {key: value for key, value in lookup.items() if key != "bundleKey"}
    if decoded.manifest != embedded:
        return None
    return StoredPreview(
        preview_key=preview_key,
        bundle_key=content_key,
        manifest=decoded.manifest,
        bundle=bundle,
    )


def ensure_preview(
    store: "Store",
    scene: Mapping[str, Any],
    *,
    assembly_id: str,
    assembly_version: int,
    configuration: str = "default",
    name: str = "",
    overrides: Mapping[str, Any] | None = None,
    generator_version: str = GENERATOR_VERSION,
    kernel_version: str | None = None,
    tessellation_profile: str = TESSELLATION_PROFILE,
    schema_version: int = MANIFEST_SCHEMA_VERSION,
    cancelled: Callable[[], bool] | None = None,
) -> StoredPreview:
    """Return a cached preview or derive and publish a new one.

    The key is computed from the requested identity before the scene is packed,
    so a warm hit does not rebuild geometry that the cache already describes.
    ``cancelled`` is checked before the expensive pack and again before the
    publish; a cancellation that arrives during that final write is not
    reported as a rollback because the bytes are already complete.
    """
    if cancelled is not None and cancelled():
        raise PreviewBuildCancelled()
    kernel = _key_text(
        kernel_version or default_kernel_version(), "kernel version"
    )
    key = preview_key(
        assembly_id=assembly_id,
        assembly_version=assembly_version,
        configuration=configuration,
        overrides=overrides,
        generator_version=generator_version,
        kernel_version=kernel,
        tessellation_profile=tessellation_profile,
        schema_version=schema_version,
    )
    lock = store.preview_build_lock(key)
    with lock:
        # The second read is what turns concurrent callers into one build:
        # waiters block here and then observe the first writer's complete lookup.
        cached = load_preview(store, key)
        if cached is not None:
            return cached
        if cancelled is not None and cancelled():
            raise PreviewBuildCancelled()
        plan = plan_preview(
            scene,
            assembly_id=assembly_id,
            assembly_version=assembly_version,
            configuration=configuration,
            name=name,
            overrides=overrides,
            generator_version=generator_version,
            kernel_version=kernel,
            tessellation_profile=tessellation_profile,
            schema_version=schema_version,
        )
        if cancelled is not None and cancelled():
            raise PreviewBuildCancelled()
        return write_preview(store, plan)


def gc_previews(
    store: "Store",
    *,
    max_bytes: int | None = None,
    max_age_seconds: float | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Collect unreferenced or expired preview cache entries.

    A complete lookup pins its bundle and every prototype it names. Per
    assembly, the highest valid assembly version is the current lookup and is
    never evicted, even when it alone exceeds ``max_bytes``. Older lookups are
    removed when they exceed ``max_age_seconds`` or when the size cap cannot be
    met otherwise, oldest first. Unreferenced manifests, bundles, and prototype
    bins are removed without asking; they cannot be reached by a warm lookup.

    The manifest is unlinked before its bundle and prototypes, so readers see a
    miss rather than a lookup pointing at missing bytes. The whole pass holds the
    store's cache lock, which is also held by publication, so a concurrent build
    cannot be collected between writing its bundle and its lookup.
    """
    if max_bytes is not None and (
        isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 0
    ):
        raise PreviewError("BAD_GC_LIMIT", "max_bytes must be a non-negative integer")
    if max_age_seconds is not None and (
        isinstance(max_age_seconds, bool)
        or not isinstance(max_age_seconds, (int, float))
        or max_age_seconds < 0
    ):
        raise PreviewError(
            "BAD_GC_LIMIT", "max_age_seconds must be a non-negative number"
        )
    timestamp = time.time() if now is None else float(now)
    with store.preview_cache_lock:
        manifest_paths = store.preview_manifest_paths()
        bundle_paths = store.preview_bundle_paths()
        prototype_paths = store.preview_prototype_paths()
        before_files = [*manifest_paths, *bundle_paths, *prototype_paths]
        before_bytes = sum(_file_size(path) for path in before_files)

        lookups: dict[str, dict[str, Any]] = {}
        invalid_manifests: list[Path] = []
        for path in manifest_paths:
            key = path.stem
            manifest = (
                store.get_preview_manifest(key) if is_preview_key(key) else None
            )
            if (
                manifest is None
                or not is_preview_key(manifest.get("bundleKey"))
            ):
                invalid_manifests.append(path)
                continue
            assembly = manifest.get("assembly") or {}
            prototypes = {
                str(record.get("prototypeKey"))
                for record in manifest.get("prototypes") or []
                if is_preview_key(record.get("prototypeKey"))
            }
            lookups[key] = {
                "path": path,
                "manifest": manifest,
                "assembly_id": str(assembly.get("id") or ""),
                "assembly_version": int(assembly.get("version") or 0),
                "bundle_key": str(manifest["bundleKey"]),
                "prototype_keys": prototypes,
                "mtime": path.stat().st_mtime,
                "bytes": _file_size(path),
            }

        current_by_assembly: dict[str, int] = {}
        for entry in lookups.values():
            assembly_id = entry["assembly_id"]
            version = entry["assembly_version"]
            if assembly_id and version > current_by_assembly.get(assembly_id, -1):
                current_by_assembly[assembly_id] = version
        current_keys: set[str] = set()
        old_keys: set[str] = set()
        for key, entry in lookups.items():
            assembly_id = entry["assembly_id"]
            if not assembly_id:
                current_keys.add(key)
            elif entry["assembly_version"] >= current_by_assembly.get(
                assembly_id, -1
            ):
                current_keys.add(key)
            else:
                old_keys.add(key)

        expired_keys: set[str] = set()
        if max_age_seconds is not None:
            for key in old_keys:
                entry = lookups[key]
                if timestamp - entry["mtime"] > max_age_seconds:
                    expired_keys.add(key)

        retained_keys = (current_keys | old_keys) - expired_keys
        deleted_manifest_keys = expired_keys
        evicted_keys: set[str] = set()

        def referenced(keys: set[str]) -> tuple[set[str], set[str]]:
            bundles = {lookups[key]["bundle_key"] for key in keys}
            prototypes: set[str] = set()
            for key in keys:
                prototypes.update(lookups[key]["prototype_keys"])
            return bundles, prototypes

        def live_bytes(keys: set[str]) -> int:
            bundles, prototypes = referenced(keys)
            manifest_bytes = sum(lookups[key]["bytes"] for key in keys)
            bundle_bytes = sum(_file_size(path) for path in bundle_paths if path.stem in bundles)
            prototype_bytes = sum(
                _file_size(path)
                for path in prototype_paths
                if path.stem in prototypes
            )
            return manifest_bytes + bundle_bytes + prototype_bytes

        if max_bytes is not None:
            old_by_age = sorted(
                (
                    key
                    for key in retained_keys
                    if key not in current_keys
                ),
                key=lambda key: lookups[key]["mtime"],
            )
            while (
                max_bytes is not None
                and live_bytes(retained_keys) > max_bytes
                and old_by_age
            ):
                key = old_by_age.pop(0)
                retained_keys.discard(key)
                evicted_keys.add(key)
            over_budget = max(0, live_bytes(retained_keys) - max_bytes)
        else:
            over_budget = 0

        bundle_files = {path.stem: path for path in bundle_paths}
        prototype_files = {path.stem: path for path in prototype_paths}
        retained_bundles, retained_prototypes = referenced(retained_keys)

        deleted_manifests: list[str] = []
        deleted_bundles: list[str] = []
        deleted_prototypes: list[str] = []
        deleted_files = 0
        deleted_bytes = 0
        errors: list[str] = []

        def remove(path: Path, label: str) -> None:
            nonlocal deleted_files, deleted_bytes
            size = _file_size(path)
            try:
                existed = store.remove_preview_file(path)
            except Exception as exc:
                errors.append(f"{label}:{path.name}:{type(exc).__name__}: {exc}")
                return
            if existed:
                deleted_files += 1
                deleted_bytes += size

        for path in invalid_manifests:
            remove(path, "manifest")
            deleted_manifests.append(path.stem)
        for key in sorted(deleted_manifest_keys):
            remove(lookups[key]["path"], "manifest")
            deleted_manifests.append(key)
        for key in sorted(evicted_keys):
            remove(lookups[key]["path"], "manifest")
            deleted_manifests.append(key)

        for key, path in bundle_files.items():
            if key in retained_bundles:
                continue
            remove(path, "bundle")
            deleted_bundles.append(key)
        for key, path in prototype_files.items():
            if key in retained_prototypes:
                continue
            remove(path, "prototype")
            deleted_prototypes.append(key)

        after_paths = [
            *store.preview_manifest_paths(),
            *store.preview_bundle_paths(),
            *store.preview_prototype_paths(),
        ]
        after_bytes = sum(_file_size(path) for path in after_paths)
        retained_lookup_bytes = sum(
            lookups[key]["bytes"] for key in retained_keys
        )
        retained_bundle_bytes = sum(
            _file_size(bundle_files[key])
            for key in retained_bundles
            if key in bundle_files
        )
        retained_prototype_bytes = sum(
            _file_size(prototype_files[key])
            for key in retained_prototypes
            if key in prototype_files
        )
        return {
            "maxBytes": max_bytes,
            "maxAgeSeconds": max_age_seconds,
            "before": {"files": len(before_files), "bytes": before_bytes},
            "after": {"files": len(after_paths), "bytes": after_bytes},
            "entries": {
                "manifests": len(manifest_paths),
                "validLookups": len(lookups),
                "currentLookups": len(current_keys),
                "oldLookups": len(old_keys),
                "bundles": len(bundle_paths),
                "prototypes": len(prototype_paths),
            },
            "retained": {
                "lookups": len(retained_keys),
                "bundles": len(retained_bundles),
                "prototypes": len(retained_prototypes),
                "bytes": retained_lookup_bytes
                + retained_bundle_bytes
                + retained_prototype_bytes,
            },
            "deleted": {
                "manifests": deleted_manifests,
                "bundles": deleted_bundles,
                "prototypes": deleted_prototypes,
                "files": deleted_files,
                "bytes": deleted_bytes,
            },
            "expiredLookups": sorted(deleted_manifest_keys - set(evicted_keys)),
            "evictedForSize": sorted(evicted_keys),
            "invalidManifests": len(invalid_manifests),
            "overBudgetBytes": over_budget,
            "errors": errors,
        }


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _preview_bom(scene: Mapping[str, Any]) -> dict[str, int]:
    rows = scene.get("bom") or ()
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        raise PreviewError("BAD_SCENE", "scene bom must be an array")
    quantity = 0
    definitions: set[tuple[Any, int, Any]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise PreviewError("BAD_SCENE", f"bom row {index} must be a mapping")
        quantity += _require_count(
            row.get("quantity"), f"bom row {index} quantity"
        )
        definitions.add(
            (
                row.get("document_id"),
                _require_count(
                    row.get("version"), f"bom row {index} version"
                ),
                row.get("configuration") or "default",
            )
        )
    return {
        "rows": len(rows),
        "quantity": quantity,
        "definitions": len(definitions),
    }


def _key_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PreviewError("BAD_KEY_INPUT", f"{label} must be non-empty text")
    return value


def _key_count(value: Any, label: str, *, minimum: int = 0) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
    ):
        raise PreviewError(
            "BAD_KEY_INPUT", f"{label} must be an integer >= {minimum}"
        )
    return value


class PreviewBuildCancelled(Exception):
    """The build stopped at a cancellation checkpoint before publishing."""


PreviewBuilder = Callable[[Callable[[float], None], threading.Event], None]


@dataclass
class PreviewBuildJob:
    """One in-flight or finished preview build, deduplicated by preview key."""

    build_id: str
    preview_key: str
    status: str = "queued"
    progress: float = 0.0
    error_code: str | None = None
    error_message: str | None = None
    started: float | None = None
    finished: float | None = None
    failure_reported: bool = False
    cancel_requested: bool = False
    cancel: threading.Event = field(default_factory=threading.Event)

    def to_json(self) -> dict[str, Any]:
        return {
            "buildId": self.build_id,
            "previewKey": self.preview_key,
            "status": self.status,
            "progress": self.progress,
            "cancelRequested": self.cancel_requested,
            "error": None
            if self.error_code is None
            else {"code": self.error_code, "message": self.error_message},
        }


class PreviewJobRegistry:
    """Build previews in daemon threads, one live job per preview key.

    A second request for the same key joins the existing job instead of packing
    the same geometry twice. Finished and failed jobs stay addressable so a
    caller can read the outcome without racing the worker. A failure is reported
    to one caller before a later request may start a fresh attempt, so a
    transient failure does not pin the key to an error forever.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_key: dict[str, PreviewBuildJob] = {}
        self._by_id: dict[str, PreviewBuildJob] = {}

    def get(self, build_id: str) -> PreviewBuildJob | None:
        with self._lock:
            return self._by_id.get(build_id)

    def for_key(self, preview_key: str) -> PreviewBuildJob | None:
        with self._lock:
            return self._by_key.get(preview_key)

    def mark_failure_reported(self, job: PreviewBuildJob) -> bool:
        """Record that a caller received this failure; true on a later call.

        Reporting once keeps a deterministic build error visible instead of
        hiding it behind an endless series of fresh attempts, while still
        letting a transient failure recover.
        """
        with self._lock:
            if job.status != "failed":
                return False
            if job.failure_reported:
                return True
            job.failure_reported = True
            return False

    def cancel(self, build_id: str) -> PreviewBuildJob | None:
        """Ask one build to stop at its next safe checkpoint.

        A queued job becomes cancelled immediately. A running job becomes
        cancelling until the worker reaches a checkpoint or finishes; a build
        that has already published a complete preview stays done rather than
        lying about a cancellation.
        """
        with self._lock:
            job = self._by_id.get(build_id)
            if job is None:
                return None
            if job.status in {"done", "failed", "cancelled"}:
                return job
            job.cancel_requested = True
            job.cancel.set()
            if job.status == "queued":
                job.status = "cancelled"
                job.finished = time.time()
            elif job.status == "running":
                job.status = "cancelling"
            return job

    def start(self, preview_key: str, builder: PreviewBuilder) -> PreviewBuildJob:
        with self._lock:
            existing = self._by_key.get(preview_key)
            if existing is not None and existing.status in {
                "queued",
                "running",
                "cancelling",
            }:
                return existing
            job = PreviewBuildJob(
                build_id=f"preview_{uuid.uuid4().hex[:12]}",
                preview_key=preview_key,
            )
            self._by_key[preview_key] = job
            self._by_id[job.build_id] = job
        thread = threading.Thread(
            target=self._run,
            args=(job, builder),
            name=f"preview-{job.build_id}",
            daemon=True,
        )
        thread.start()
        return job

    def _run(self, job: PreviewBuildJob, builder: PreviewBuilder) -> None:
        with self._lock:
            if job.status != "queued":
                return
            if job.cancel.is_set():
                job.status = "cancelled"
                job.finished = time.time()
                return
            job.status = "running"
            job.started = time.time()

        def progress(value: float) -> None:
            with self._lock:
                if job.status != "running" or job.cancel.is_set():
                    return
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    return
                job.progress = min(1.0, max(0.0, number))

        try:
            builder(progress, job.cancel)
        except PreviewBuildCancelled:
            with self._lock:
                job.status = "cancelled"
                job.error_code = "CANCELLED"
                job.error_message = "preview build cancelled"
        except Exception as exc:
            with self._lock:
                if job.cancel.is_set():
                    job.status = "cancelled"
                    job.error_code = "CANCELLED"
                    job.error_message = "preview build cancelled"
                else:
                    job.status = "failed"
                    job.progress = 1.0
                    job.error_code = str(
                        getattr(exc, "code", None) or "PREVIEW_FAILED"
                    )
                    job.error_message = str(
                        getattr(exc, "message", None)
                        or exc
                        or type(exc).__name__
                    )
        else:
            with self._lock:
                job.status = "done"
                job.progress = 1.0
        finally:
            with self._lock:
                job.finished = time.time()


