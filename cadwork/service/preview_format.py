"""Container and manifest codec for derived assembly previews.

A preview bundle is display data, never editable document state. Its bytes are
untrusted input: a malformed container is a cache miss, so every decoder here
raises PreviewFormatError instead of returning whatever could be parsed. A
partially accepted bundle would render a wrong model as if it were valid.

Wire encoding is little-endian throughout. The container is:

    0   4  magic b"BPXV"
    4   2  format version
    6   2  flags, zero
    8   4  manifest byte length
    12  4  reserved, zero
    16  N  manifest JSON, UTF-8 without BOM
    ... P  zero padding up to the next 8-byte boundary
    ...    prototype blobs, each starting 8-byte aligned relative to dataBase

A prototype blob concatenates float32 positions, uint32 indices, uint32
per-triangle face ids, and float32 edge points. Alignment padding belongs to the
container, never to an array: digests, keys, and counts cover array bytes only.

Error codes are stable identifiers. Messages are diagnostic text and may change;
callers branch on ``code`` and treat every code as "regenerate the asset".
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
import sys
from array import array
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, NoReturn

MAGIC = b"BPXV"
FORMAT_VERSION = 1
HEADER_SIZE = 16
ALIGNMENT = 8

MANIFEST_SCHEMA = "brepx-assembly-preview"
MANIFEST_SCHEMA_VERSION = 1
MANIFEST_UNITS = "mm"

MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_BUNDLE_BYTES = 512 * 1024 * 1024
MAX_PROTOTYPES = 1024
MAX_INSTANCES = 65_536
MAX_LEAVES = 65_536

_HEADER = struct.Struct("<4sHHII")
_KEY_PATTERN = re.compile(r"[0-9a-f]{64}")
_COLOR_PATTERN = re.compile(r"#[0-9a-fA-F]{6}")

# The wire format fixes element widths. A platform where ``array`` disagrees
# cannot encode the format without silently reinterpreting bytes, so fail loud.
if array("f").itemsize != 4 or array("I").itemsize != 4:
    raise RuntimeError(
        "preview format requires 32-bit float and 32-bit unsigned int arrays"
    )


class PreviewFormatError(Exception):
    """A bundle or manifest failed structural validation.

    ``code`` is stable; ``message`` explains the first violated invariant.
    Validation stops at the first failure because later fields cannot be
    interpreted reliably once an earlier one is wrong.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class BundleHeader:
    version: int
    flags: int
    manifest_length: int
    reserved: int

    @property
    def data_base(self) -> int:
        """File offset of the first prototype blob."""
        return align8(HEADER_SIZE + self.manifest_length)


@dataclass(frozen=True)
class PrototypeArrays:
    positions: array
    indices: array
    face_ids: array
    edges: array


@dataclass(frozen=True)
class PreviewBundle:
    header: BundleHeader
    manifest: dict[str, Any]
    prototypes: dict[str, PrototypeArrays]
    data_base: int


def align8(value: int) -> int:
    """Round ``value`` up to the container's 8-byte alignment unit."""
    if value < 0:
        raise ValueError("cannot align a negative length")
    return (value + ALIGNMENT - 1) & ~(ALIGNMENT - 1)


def encode_header(manifest_length: int) -> bytes:
    """Encode the fixed header for a manifest of this byte length."""
    if not _is_int(manifest_length) or not 0 < manifest_length <= MAX_MANIFEST_BYTES:
        _fail(
            "MANIFEST_LENGTH_INVALID",
            f"manifest length {manifest_length!r} is outside 1..{MAX_MANIFEST_BYTES}",
        )
    return _HEADER.pack(MAGIC, FORMAT_VERSION, 0, int(manifest_length), 0)


def decode_header(data: bytes | bytearray | memoryview) -> BundleHeader:
    """Decode and validate only the fixed header.

    Bundle length is not checked here because a caller validating an upload may
    inspect the header before buffering the body. Use :func:`decode_bundle` for
    whole-bundle validation.
    """
    view = memoryview(data)
    if len(view) < HEADER_SIZE:
        _fail("HEADER_TRUNCATED", f"need {HEADER_SIZE} header bytes, got {len(view)}")
    magic, version, flags, manifest_length, reserved = _HEADER.unpack_from(view)
    if magic != MAGIC:
        _fail("BAD_MAGIC", f"expected magic {MAGIC!r}, got {magic!r}")
    if version != FORMAT_VERSION:
        _fail(
            "UNSUPPORTED_FORMAT_VERSION",
            f"unsupported format version {version}, expected {FORMAT_VERSION}",
        )
    if flags != 0:
        _fail("UNKNOWN_FLAGS", f"unknown header flags 0x{flags:04x}")
    if reserved != 0:
        _fail("RESERVED_NONZERO", f"reserved header word is {reserved}, expected 0")
    if not 0 < manifest_length <= MAX_MANIFEST_BYTES:
        _fail(
            "MANIFEST_LENGTH_INVALID",
            f"manifest length {manifest_length} is outside 1..{MAX_MANIFEST_BYTES}",
        )
    return BundleHeader(
        version=version,
        flags=flags,
        manifest_length=manifest_length,
        reserved=reserved,
    )


def encode_manifest(manifest: Mapping[str, Any]) -> bytes:
    """Serialize a manifest as canonical UTF-8 JSON without a BOM.

    Keys are sorted so equal manifests produce identical bytes; otherwise the
    same content would churn a content-addressed cache. Non-finite numbers are
    rejected because JSON cannot represent them portably and the browser decoder
    would reject the resulting text.
    """
    try:
        text = json.dumps(
            manifest,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        _fail("MANIFEST_NOT_JSON", f"manifest cannot be serialized: {exc}")
    return text.encode("utf-8")


def decode_manifest(data: bytes | bytearray | memoryview) -> dict[str, Any]:
    """Parse and structurally validate one manifest.

    Duplicate JSON member names are rejected: parsers disagree on which value
    wins, so accepting either would make the decoded bundle parser-dependent.
    """
    raw = bytes(data)
    if raw.startswith(b"\xef\xbb\xbf"):
        _fail("MANIFEST_BOM", "manifest must not start with a byte-order mark")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail("MANIFEST_NOT_UTF8", f"manifest is not valid UTF-8: {exc}")
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_manifest_object,
            parse_constant=_reject_json_constant,
        )
    except PreviewFormatError:
        raise
    except (ValueError, RecursionError) as exc:
        # CPython raises RecursionError for deeply nested input and ValueError
        # for integer literals above its conversion limit. Neither state is
        # representable in the format, and both must be a cache miss rather than
        # a request failure.
        _fail("MANIFEST_NOT_JSON", f"manifest is not valid JSON: {exc}")
    if not isinstance(parsed, dict):
        _fail("MANIFEST_NOT_OBJECT", "manifest must be a JSON object")
    validate_manifest(parsed)
    return parsed


def validate_manifest(
    manifest: Mapping[str, Any], *, require_layout: bool = True
) -> None:
    """Validate every manifest field that does not require blob bytes.

    ``require_layout`` is false when a producer has not assigned blob offsets
    yet; :func:`encode_bundle` assigns them. Blob contents and prototype key
    digests are checked only when the bundle or blobs are available.
    """
    if not isinstance(manifest, Mapping):
        _fail("MANIFEST_NOT_OBJECT", "manifest must be a mapping")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        _fail(
            "UNKNOWN_SCHEMA",
            f"unsupported manifest schema {manifest.get('schema')!r}",
        )
    schema_version = manifest.get("schemaVersion")
    if not _is_int(schema_version):
        _fail("BAD_MANIFEST_FIELD", "schemaVersion must be an integer")
    if schema_version != MANIFEST_SCHEMA_VERSION:
        _fail(
            "UNSUPPORTED_SCHEMA_VERSION",
            f"unsupported schema version {schema_version}, "
            f"expected {MANIFEST_SCHEMA_VERSION}",
        )
    _require_key(manifest.get("previewKey"), "previewKey")
    if "bundleKey" in manifest:
        # bundleKey is a lookup-record field: the bundle's embedded manifest
        # cannot contain a hash of bytes that include itself.
        _require_key(manifest.get("bundleKey"), "bundleKey")

    assembly = _require_mapping(manifest.get("assembly"), "assembly")
    _require_text(assembly.get("id"), "assembly.id")
    _require_count(assembly.get("version"), "assembly.version")
    _require_text(assembly.get("configuration"), "assembly.configuration")
    if not isinstance(assembly.get("name"), str):
        _fail("BAD_MANIFEST_FIELD", "assembly.name must be a string")

    generator = _require_mapping(manifest.get("generator"), "generator")
    _require_text(generator.get("version"), "generator.version")
    _require_text(generator.get("kernel"), "generator.kernel")
    _require_text(
        generator.get("tessellationProfile"), "generator.tessellationProfile"
    )

    if manifest.get("units") != MANIFEST_UNITS:
        _fail(
            "BAD_MANIFEST_FIELD",
            f"units must be {MANIFEST_UNITS!r}, got {manifest.get('units')!r}",
        )
    _require_vector3(manifest.get("rootOffset"), "rootOffset")

    prototypes = _require_sequence(manifest.get("prototypes"), "prototypes")
    prototype_count = _require_count(
        manifest.get("prototypeCount"), "prototypeCount", limit=MAX_PROTOTYPES
    )
    if prototype_count != len(prototypes):
        _fail(
            "BAD_MANIFEST_FIELD",
            f"prototypeCount is {prototype_count}, "
            f"but prototypes has {len(prototypes)} entries",
        )

    instances = _require_sequence(manifest.get("instances"), "instances")
    instance_count = _require_count(
        manifest.get("instanceCount"), "instanceCount", limit=MAX_INSTANCES
    )
    if instance_count != len(instances):
        _fail(
            "BAD_MANIFEST_FIELD",
            f"instanceCount is {instance_count}, "
            f"but instances has {len(instances)} entries",
        )
    _require_count(manifest.get("leafCount"), "leafCount", limit=MAX_LEAVES)

    bom = _require_mapping(manifest.get("bom"), "bom")
    for field in ("rows", "quantity", "definitions"):
        _require_count(bom.get(field), f"bom.{field}")

    seen_keys: set[str] = set()
    for index, record in enumerate(prototypes):
        _validate_prototype_record(
            record, index, seen_keys, require_layout=require_layout
        )

    seen_paths: set[str] = set()
    for index, record in enumerate(instances):
        _validate_instance_record(record, index, seen_keys, seen_paths)


def prototype_blob_size(
    position_count: int, index_count: int, edge_point_count: int
) -> int:
    """Byte size of the unpadded arrays for these counts.

    Counts are validated here because every caller derives an allocation or a
    slice from this number; a wrong count must fail before it reaches memory
    arithmetic.
    """
    position_count = _require_count(position_count, "positionCount")
    index_count = _require_count(index_count, "indexCount")
    edge_point_count = _require_count(edge_point_count, "edgePointCount")
    if index_count % 3:
        _fail("BAD_INDEX_COUNT", f"indexCount {index_count} is not divisible by 3")
    if edge_point_count % 2:
        _fail("BAD_EDGE_COUNT", f"edgePointCount {edge_point_count} is odd")
    return (
        position_count * 3 * 4
        + index_count * 4
        + (index_count // 3) * 4
        + edge_point_count * 3 * 4
    )


def pack_prototype_blob(
    positions: Sequence[float],
    indices: Sequence[int],
    face_ids: Sequence[int],
    edge_points: Sequence[float],
) -> bytes:
    """Concatenate prototype arrays in wire order with no padding.

    Array lengths must already agree: positions and edge points are XYZ triples,
    indices form whole triangles, and each triangle owns exactly one face id.
    """
    if len(positions) % 3:
        _fail("BAD_MESH", "positions length is not a multiple of 3")
    if len(indices) % 3:
        _fail("BAD_INDEX_COUNT", "indices length is not a multiple of 3")
    if len(face_ids) * 3 != len(indices):
        _fail("BAD_FACE_COUNT", "face id count is not one per triangle")
    if len(edge_points) % 3:
        _fail("BAD_EDGE_COUNT", "edge points length is not a multiple of 3")
    if (len(edge_points) // 3) % 2:
        _fail("BAD_EDGE_COUNT", "edge point count is odd")
    position_count = len(positions) // 3
    for value in positions:
        _require_finite(value, "positions")
    for value in edge_points:
        _require_finite(value, "edge points")
    for value in indices:
        _require_uint32(value, "index")
        if value >= position_count:
            _fail(
                "BAD_INDEX",
                f"index {value} is outside positionCount {position_count}",
            )
    for value in face_ids:
        _require_uint32(value, "face id")
    try:
        return b"".join(
            (
                struct.pack(f"<{len(positions)}f", *positions),
                struct.pack(f"<{len(indices)}I", *indices),
                struct.pack(f"<{len(face_ids)}I", *face_ids),
                struct.pack(f"<{len(edge_points)}f", *edge_points),
            )
        )
    except struct.error as exc:
        _fail("BAD_MESH", f"prototype arrays cannot be encoded: {exc}")


def unpack_prototype_blob(
    blob: bytes | bytearray | memoryview,
    *,
    position_count: int,
    index_count: int,
    edge_point_count: int,
) -> PrototypeArrays:
    """Split one input-free prototype blob into typed arrays.

    The blob length must equal the unpadded size derived from the counts; extra
    bytes are alignment padding, which callers must strip before this call.
    """
    expected = prototype_blob_size(position_count, index_count, edge_point_count)
    raw = bytes(blob)
    if len(raw) != expected:
        _fail(
            "BAD_BLOB_LENGTH",
            f"prototype arrays need {expected} bytes, got {len(raw)}",
        )
    position_bytes = position_count * 3 * 4
    index_bytes = index_count * 4
    face_bytes = (index_count // 3) * 4
    offset = 0
    positions = _float_array(raw[offset : offset + position_bytes])
    offset += position_bytes
    indices = _uint_array(raw[offset : offset + index_bytes])
    offset += index_bytes
    face_ids = _uint_array(raw[offset : offset + face_bytes])
    offset += face_bytes
    edges = _float_array(raw[offset:])
    return PrototypeArrays(
        positions=positions, indices=indices, face_ids=face_ids, edges=edges
    )


def prototype_mesh_digest(blob: bytes | bytearray | memoryview) -> str:
    """SHA-256 over array bytes in positions, indices, face ids, edges order.

    ``blob`` must be the exact array bytes. Including alignment padding would
    make one mesh hash differently depending on where its blob was placed.
    """
    return hashlib.sha256(bytes(blob)).hexdigest()


def bundle_key(data: bytes | bytearray | memoryview) -> str:
    """SHA-256 of the exact canonical bundle bytes.

    The immutable asset URL names these bytes, so any change in a prototype,
    manifest field, or layout produces a different key instead of replacing
    content behind an old URL.
    """
    return hashlib.sha256(bytes(data)).hexdigest()


def prototype_key(
    *,
    schema_version: int,
    source_identity: str,
    tessellation_profile: str,
    kernel_version: str,
    mesh_digest: str,
) -> str:
    """Derive the content key that names one local prototype mesh."""
    material = "\n".join(
        (
            "brepx-prototype",
            str(schema_version),
            source_identity,
            tessellation_profile,
            kernel_version,
            mesh_digest,
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def encode_bundle(
    manifest: dict[str, Any], prototype_blobs: Mapping[str, bytes]
) -> bytes:
    """Pack a manifest and its prototype arrays into one bundle.

    Blob offsets and allocated lengths are assigned from the given order; any
    ``mesh.offset`` and ``mesh.blobLength`` already in ``manifest`` are ignored
    and the caller's object is not mutated. ``prototype_blobs`` maps each
    prototype key to unpadded array bytes exactly as packed by
    :func:`pack_prototype_blob`.
    """
    validate_manifest(manifest, require_layout=False)
    if "bundleKey" in manifest:
        _fail(
            "BUNDLE_KEY_IN_BUNDLE",
            "bundleKey belongs to the lookup record, not the embedded manifest",
        )
    records = list(manifest["prototypes"])
    keys = [record["prototypeKey"] for record in records]
    missing = [key for key in keys if key not in prototype_blobs]
    if missing:
        _fail("MISSING_PROTOTYPE", f"no blob for prototype {missing[0]}")
    extra = sorted(set(prototype_blobs).difference(keys))
    if extra:
        _fail("UNUSED_PROTOTYPE", f"blob for unknown prototype {extra[0]}")

    schema_version = manifest["schemaVersion"]
    generator = manifest["generator"]
    offset = 0
    payload = bytearray()
    built_records: list[dict[str, Any]] = []
    for record in records:
        key = record["prototypeKey"]
        blob = bytes(prototype_blobs[key])
        mesh = record["mesh"]
        size = prototype_blob_size(
            int(mesh["positionCount"]),
            int(mesh["indexCount"]),
            int(mesh["edgePointCount"]),
        )
        if len(blob) != size:
            _fail(
                "BAD_BLOB_LENGTH",
                f"prototype {key} needs {size} array bytes, got {len(blob)}",
            )
        _validate_prototype_arrays(record, blob, schema_version, generator)
        allocated = align8(size)
        built_mesh = dict(mesh)
        built_mesh["offset"] = offset
        built_mesh["blobLength"] = allocated
        built_record = dict(record)
        built_record["mesh"] = built_mesh
        built_records.append(built_record)
        payload.extend(blob)
        payload.extend(b"\x00" * (allocated - size))
        offset += allocated

    built_manifest = dict(manifest)
    built_manifest["prototypes"] = built_records
    manifest_bytes = encode_manifest(built_manifest)
    if len(manifest_bytes) > MAX_MANIFEST_BYTES:
        _fail(
            "MANIFEST_LENGTH_INVALID",
            f"manifest is {len(manifest_bytes)} bytes, "
            f"limit is {MAX_MANIFEST_BYTES}",
        )
    data_base = align8(HEADER_SIZE + len(manifest_bytes))
    total = data_base + len(payload)
    if total > MAX_BUNDLE_BYTES:
        _fail(
            "BUNDLE_TOO_LARGE",
            f"bundle would be {total} bytes, limit is {MAX_BUNDLE_BYTES}",
        )
    header = encode_header(len(manifest_bytes))
    padding = b"\x00" * (data_base - HEADER_SIZE - len(manifest_bytes))
    return b"".join((header, manifest_bytes, padding, bytes(payload)))


def decode_bundle(data: bytes | bytearray | memoryview) -> PreviewBundle:
    """Validate and decode one complete bundle.

    Decoding checks the header, manifest, every prototype blob, alignment,
    zero padding, array contents, prototype keys, and instance references.
    Any failure raises PreviewFormatError; no partial bundle is returned.
    """
    view = memoryview(data)
    header = decode_header(view)
    if len(view) > MAX_BUNDLE_BYTES:
        _fail(
            "BUNDLE_TOO_LARGE",
            f"bundle is {len(view)} bytes, limit is {MAX_BUNDLE_BYTES}",
        )
    manifest_end = HEADER_SIZE + header.manifest_length
    if manifest_end > len(view):
        _fail(
            "BUNDLE_TRUNCATED",
            f"manifest ends at {manifest_end}, bundle is {len(view)}",
        )
    data_base = header.data_base
    if data_base > len(view):
        _fail(
            "BUNDLE_TRUNCATED",
            f"dataBase {data_base} is past bundle end {len(view)}",
        )
    if any(view[manifest_end:data_base]):
        _fail("PADDING_NONZERO", "header padding must be zero")

    manifest = decode_manifest(view[HEADER_SIZE:manifest_end])
    if "bundleKey" in manifest:
        _fail(
            "BUNDLE_KEY_IN_BUNDLE",
            "embedded manifest must not carry a lookup bundleKey",
        )
    schema_version = manifest["schemaVersion"]
    generator = manifest["generator"]
    layout: list[tuple[dict[str, Any], int, int, int]] = []
    for record in manifest["prototypes"]:
        key = record["prototypeKey"]
        mesh = record["mesh"]
        exact = prototype_blob_size(
            mesh["positionCount"], mesh["indexCount"], mesh["edgePointCount"]
        )
        start = data_base + mesh["offset"]
        end = start + mesh["blobLength"]
        if start < data_base or end > len(view):
            _fail(
                "BAD_BLOB_RANGE",
                f"prototype {key} range {start}..{end} is outside the bundle",
            )
        layout.append((record, start, start + exact, end))

    # Layout is checked before array contents: an overlapping or truncated range
    # would make every later byte attribution ambiguous, so report it first.
    cursor = data_base
    for start, end in sorted((start, end) for _, start, _, end in layout if end > start):
        if start < cursor:
            _fail("BAD_BLOB_OVERLAP", "prototype blob ranges overlap")
        if any(view[cursor:start]):
            _fail("PADDING_NONZERO", "gap between prototype blobs must be zero")
        cursor = end
    if cursor < len(view):
        _fail(
            "BUNDLE_TRAILING_BYTES",
            f"{len(view) - cursor} bytes follow the last prototype blob",
        )

    prototypes: dict[str, PrototypeArrays] = {}
    for record, start, exact_end, end in layout:
        key = record["prototypeKey"]
        if any(view[exact_end:end]):
            _fail("PADDING_NONZERO", f"prototype {key} blob padding must be zero")
        arrays = _validate_prototype_arrays(
            record, view[start:exact_end].tobytes(), schema_version, generator
        )
        prototypes[key] = arrays
    return PreviewBundle(
        header=header, manifest=manifest, prototypes=prototypes, data_base=data_base
    )


def _validate_prototype_record(
    record: Any,
    index: int,
    seen_keys: set[str],
    *,
    require_layout: bool,
) -> None:
    if not isinstance(record, Mapping):
        _fail("BAD_MANIFEST_FIELD", f"prototypes[{index}] must be an object")
    key = _require_key(record.get("prototypeKey"), f"prototypes[{index}].prototypeKey")
    if key in seen_keys:
        _fail("DUPLICATE_PROTOTYPE_KEY", f"duplicate prototype key {key}")
    seen_keys.add(key)
    _require_text(record.get("sourceDocumentId"), f"prototypes[{index}].sourceDocumentId")
    _require_count(record.get("sourceVersion"), f"prototypes[{index}].sourceVersion")
    _require_text(record.get("sourceIdentity"), f"prototypes[{index}].sourceIdentity")
    _require_text(record.get("faceKeySource"), f"prototypes[{index}].faceKeySource")

    face_keys = _require_sequence(record.get("faceKeys"), f"prototypes[{index}].faceKeys")
    seen_face_keys: set[str] = set()
    for face_index, face_key in enumerate(face_keys):
        _require_text(
            face_key, f"prototypes[{index}].faceKeys[{face_index}]"
        )
        if face_key in seen_face_keys:
            _fail(
                "DUPLICATE_FACE_KEY",
                f"prototype {key} repeats face key {face_key!r}",
            )
        seen_face_keys.add(face_key)

    bounds = record.get("bounds")
    if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
        _fail("BAD_BOUNDS", f"prototypes[{index}].bounds must be [min, max]")
    minimum = _require_vector3(bounds[0], f"prototypes[{index}].bounds[0]")
    maximum = _require_vector3(bounds[1], f"prototypes[{index}].bounds[1]")
    if any(low > high for low, high in zip(minimum, maximum)):
        _fail("BAD_BOUNDS", f"prototype {key} bounds min exceeds max")

    _require_mapping(record.get("metrics"), f"prototypes[{index}].metrics")
    mesh = _require_mapping(record.get("mesh"), f"prototypes[{index}].mesh")
    position_count = _require_count(
        mesh.get("positionCount"), f"prototypes[{index}].mesh.positionCount"
    )
    index_count = _require_count(
        mesh.get("indexCount"), f"prototypes[{index}].mesh.indexCount"
    )
    face_count = _require_count(
        mesh.get("faceCount"), f"prototypes[{index}].mesh.faceCount"
    )
    edge_point_count = _require_count(
        mesh.get("edgePointCount"), f"prototypes[{index}].mesh.edgePointCount"
    )
    if index_count % 3:
        _fail(
            "BAD_INDEX_COUNT",
            f"prototype {key} indexCount {index_count} is not divisible by 3",
        )
    if edge_point_count % 2:
        _fail(
            "BAD_EDGE_COUNT",
            f"prototype {key} edgePointCount {edge_point_count} is odd",
        )
    if face_count != len(face_keys):
        _fail(
            "BAD_FACE_COUNT",
            f"prototype {key} faceCount {face_count} "
            f"does not match {len(face_keys)} face keys",
        )
    if not require_layout:
        return
    blob_offset = _require_count(
        mesh.get("offset"), f"prototypes[{index}].mesh.offset"
    )
    if blob_offset % ALIGNMENT:
        _fail(
            "BAD_BLOB_ALIGNMENT",
            f"prototype {key} offset {blob_offset} is not 8-byte aligned",
        )
    blob_length = _require_count(
        mesh.get("blobLength"), f"prototypes[{index}].mesh.blobLength"
    )
    if blob_length != align8(
        prototype_blob_size(position_count, index_count, edge_point_count)
    ):
        _fail(
            "BAD_BLOB_LENGTH",
            f"prototype {key} blobLength {blob_length} does not match its counts",
        )


def _validate_instance_record(
    record: Any, index: int, prototype_keys: set[str], seen_paths: set[str]
) -> None:
    if not isinstance(record, Mapping):
        _fail("BAD_MANIFEST_FIELD", f"instances[{index}] must be an object")
    path = _require_text(record.get("path"), f"instances[{index}].path")
    if path in seen_paths:
        _fail("DUPLICATE_INSTANCE_PATH", f"duplicate instance path {path!r}")
    seen_paths.add(path)
    parent_path = _require_text(
        record.get("parentPath"), f"instances[{index}].parentPath", allow_empty=True
    )
    expected_parent = path.rsplit("/", 1)[0] if "/" in path else ""
    if parent_path != expected_parent:
        _fail(
            "BAD_INSTANCE_FIELD",
            f"instance {path!r} parentPath must be {expected_parent!r}",
        )
    _require_text(record.get("instanceId"), f"instances[{index}].instanceId")
    key = _require_key(
        record.get("prototypeKey"), f"instances[{index}].prototypeKey"
    )
    if key not in prototype_keys:
        _fail("MISSING_PROTOTYPE", f"instance {path!r} references unknown prototype")
    matrix = record.get("matrix")
    if not isinstance(matrix, (list, tuple)) or len(matrix) != 16:
        _fail("BAD_MATRIX", f"instances[{index}].matrix must have 16 entries")
    for position, value in enumerate(matrix):
        _require_finite(value, f"instances[{index}].matrix[{position}]")
    color = record.get("color")
    if not isinstance(color, str) or _COLOR_PATTERN.fullmatch(color) is None:
        _fail("BAD_COLOR", f"instances[{index}].color must be #rrggbb")
    opacity = record.get("opacity")
    if (
        isinstance(opacity, bool)
        or not isinstance(opacity, (int, float))
        or not 0.0 <= float(opacity) <= 1.0
    ):
        _fail("BAD_OPACITY", f"instances[{index}].opacity must be within 0..1")
    for field in ("visible", "suppressed"):
        if not isinstance(record.get(field), bool):
            _fail(
                "BAD_INSTANCE_FIELD",
                f"instances[{index}].{field} must be a boolean",
            )
    _require_text(
        record.get("module"), f"instances[{index}].module", allow_empty=True
    )


def _validate_prototype_arrays(
    record: Mapping[str, Any],
    blob: bytes,
    schema_version: int,
    generator: Mapping[str, Any],
) -> PrototypeArrays:
    mesh = record["mesh"]
    arrays = unpack_prototype_blob(
        blob,
        position_count=mesh["positionCount"],
        index_count=mesh["indexCount"],
        edge_point_count=mesh["edgePointCount"],
    )
    if arrays.indices and max(arrays.indices) >= mesh["positionCount"]:
        _fail("BAD_INDEX", f"prototype {record['prototypeKey']} has an out-of-range index")
    if arrays.face_ids and max(arrays.face_ids) >= mesh["faceCount"]:
        _fail(
            "BAD_FACE_ID",
            f"prototype {record['prototypeKey']} has an out-of-range face id",
        )
    if arrays.positions and not all(math.isfinite(value) for value in arrays.positions):
        _fail("BAD_COORDINATE", "prototype positions contain a non-finite value")
    if arrays.edges and not all(math.isfinite(value) for value in arrays.edges):
        _fail("BAD_COORDINATE", "prototype edge points contain a non-finite value")
    expected = prototype_key(
        schema_version=schema_version,
        source_identity=record["sourceIdentity"],
        tessellation_profile=generator["tessellationProfile"],
        kernel_version=generator["kernel"],
        mesh_digest=prototype_mesh_digest(blob),
    )
    if expected != record["prototypeKey"]:
        _fail(
            "PROTOTYPE_KEY_MISMATCH",
            f"prototype {record['prototypeKey']} does not match its mesh bytes",
        )
    return arrays


def _manifest_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("MANIFEST_DUPLICATE_MEMBER", f"duplicate JSON member {key!r}")
        result[key] = value
    return result


def _reject_json_constant(token: str) -> NoReturn:
    _fail("MANIFEST_NOT_JSON", f"non-standard JSON constant {token!r}")


def _float_array(data: bytes) -> array:
    values = array("f")
    values.frombytes(data)
    if sys.byteorder != "little":
        values.byteswap()
    return values


def _uint_array(data: bytes) -> array:
    values = array("I")
    values.frombytes(data)
    if sys.byteorder != "little":
        values.byteswap()
    return values


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("BAD_MANIFEST_FIELD", f"{field} must be an object")
    return value


def _require_sequence(value: Any, field: str) -> list[Any] | tuple[Any, ...]:
    if not isinstance(value, (list, tuple)):
        _fail("BAD_MANIFEST_FIELD", f"{field} must be an array")
    return value


def _require_text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        qualifier = "" if allow_empty else "non-empty "
        _fail("BAD_MANIFEST_FIELD", f"{field} must be a {qualifier}string")
    return value


def _require_count(value: Any, field: str, *, limit: int | None = None) -> int:
    if not _is_int(value) or value < 0:
        _fail("BAD_MANIFEST_FIELD", f"{field} must be a non-negative integer")
    if limit is not None and value > limit:
        _fail("COUNT_LIMIT", f"{field} is {value}, limit is {limit}")
    return int(value)


def _require_key(value: Any, field: str) -> str:
    if not isinstance(value, str) or _KEY_PATTERN.fullmatch(value) is None:
        _fail(
            "BAD_KEY",
            f"{field} must be 64 lowercase hexadecimal characters",
        )
    return value


def _require_vector3(value: Any, field: str) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        _fail("BAD_MANIFEST_FIELD", f"{field} must have 3 components")
    return (
        _require_finite(value[0], f"{field}[0]"),
        _require_finite(value[1], f"{field}[1]"),
        _require_finite(value[2], f"{field}[2]"),
    )


def _require_finite(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail("BAD_MANIFEST_FIELD", f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        _fail("BAD_MANIFEST_FIELD", f"{field} must be a finite number")
    return number


def _require_uint32(value: Any, field: str) -> int:
    if not _is_int(value) or not 0 <= value <= 0xFFFFFFFF:
        _fail("BAD_MESH", f"{field} {value!r} is not an unsigned 32-bit integer")
    return int(value)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _fail(code: str, message: str) -> NoReturn:
    raise PreviewFormatError(code, message)
