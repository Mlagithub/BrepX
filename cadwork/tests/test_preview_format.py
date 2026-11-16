"""Contract tests for the assembly preview container and manifest codec."""

from __future__ import annotations

import copy
import hashlib
import struct
import unittest
from unittest.mock import patch

from cadwork.service.preview_format import (
    FORMAT_VERSION,
    HEADER_SIZE,
    MAGIC,
    MANIFEST_SCHEMA,
    MANIFEST_SCHEMA_VERSION,
    MAX_INSTANCES,
    MAX_LEAVES,
    MAX_MANIFEST_BYTES,
    MAX_PROTOTYPES,
    PreviewFormatError,
    align8,
    decode_bundle,
    decode_header,
    decode_manifest,
    encode_bundle,
    encode_header,
    encode_manifest,
    pack_prototype_blob,
    prototype_blob_size,
    prototype_key,
    prototype_mesh_digest,
    unpack_prototype_blob,
    validate_manifest,
)

_PROFILE = "tessellation-standard"
_KERNEL = "smlibpy 0.6.2"
_SOURCE_IDENTITY = "d_source@1#default#{}"
_PREVIEW_KEY = "c" * 64
_UNKNOWN_KEY = "d" * 64
_IDENTITY = [
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
]


def _header(
    *,
    magic: bytes = MAGIC,
    version: int = FORMAT_VERSION,
    flags: int = 0,
    manifest_length: int = 8,
    reserved: int = 0,
) -> bytes:
    return struct.pack("<4sHHII", magic, version, flags, manifest_length, reserved)


def _prototype(
    *,
    positions=(0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0),
    indices=(0, 1, 2),
    face_ids=(0,),
    edge_points=(0.0, 0.0, 0.0, 1.0, 0.0, 0.0),
    face_keys=("body:0",),
    key=None,
    record_overrides=None,
    mesh_overrides=None,
):
    blob = pack_prototype_blob(positions, indices, face_ids, edge_points)
    if key is None:
        key = prototype_key(
            schema_version=MANIFEST_SCHEMA_VERSION,
            source_identity=_SOURCE_IDENTITY,
            tessellation_profile=_PROFILE,
            kernel_version=_KERNEL,
            mesh_digest=prototype_mesh_digest(blob),
        )
    if positions:
        bounds = [
            [
                min(positions[0::3]),
                min(positions[1::3]),
                min(positions[2::3]),
            ],
            [
                max(positions[0::3]),
                max(positions[1::3]),
                max(positions[2::3]),
            ],
        ]
    else:
        bounds = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    mesh = {
        "offset": 0,
        "blobLength": align8(len(blob)),
        "positionCount": len(positions) // 3,
        "indexCount": len(indices),
        "faceCount": len(face_keys),
        "edgePointCount": len(edge_points) // 3,
    }
    mesh.update(mesh_overrides or {})
    record = {
        "prototypeKey": key,
        "sourceDocumentId": "d_source",
        "sourceVersion": 1,
        "sourceIdentity": _SOURCE_IDENTITY,
        "faceKeySource": "ordinal",
        "faceKeys": list(face_keys),
        "bounds": bounds,
        "metrics": {"volume": 1.0, "area": 2.0},
        "mesh": mesh,
    }
    record.update(record_overrides or {})
    return record, blob


def _instance(path: str, prototype: str, **overrides):
    parent_path = path.rsplit("/", 1)[0] if "/" in path else ""
    record = {
        "path": path,
        "parentPath": parent_path,
        "instanceId": "i_" + path.replace("/", "_"),
        "prototypeKey": prototype,
        "matrix": list(_IDENTITY),
        "color": "#b6c9d7",
        "opacity": 1.0,
        "visible": True,
        "suppressed": False,
        "module": path.split("/", 1)[0],
    }
    record.update(overrides)
    return record


def _manifest(records, instances, **overrides):
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "previewKey": _PREVIEW_KEY,
        "assembly": {
            "id": "a_test",
            "version": 2,
            "configuration": "default",
            "name": "test assembly",
        },
        "generator": {
            "version": "1",
            "kernel": _KERNEL,
            "tessellationProfile": _PROFILE,
        },
        "units": "mm",
        "rootOffset": [0.0, 0.0, 0.0],
        "prototypeCount": len(records),
        "instanceCount": len(instances),
        "leafCount": len(instances),
        "bom": {
            "rows": len(instances),
            "quantity": len(instances),
            "definitions": len(records),
        },
        "prototypes": records,
        "instances": instances,
    }
    manifest.update(overrides)
    return manifest


def _bundle_inputs(prototypes, instances, **overrides):
    records = [record for record, _ in prototypes]
    manifest = _manifest(records, instances, **overrides)
    blobs = {record["prototypeKey"]: blob for record, blob in prototypes}
    return manifest, blobs


def _raw_bundle_bytes(
    manifest_bytes: bytes,
    payload: bytes = b"",
    *,
    magic: bytes = MAGIC,
    version: int = FORMAT_VERSION,
    flags: int = 0,
    reserved: int = 0,
    manifest_length: int | None = None,
    padding: bytes | None = None,
) -> bytes:
    length = len(manifest_bytes) if manifest_length is None else manifest_length
    header = struct.pack("<4sHHII", magic, version, flags, length, reserved)
    data_base = align8(HEADER_SIZE + len(manifest_bytes))
    pad_length = data_base - HEADER_SIZE - len(manifest_bytes)
    if padding is None:
        padding = b"\x00" * pad_length
    return header + manifest_bytes + padding + payload


def _raw_bundle(manifest, payload: bytes = b"", **overrides) -> bytes:
    return _raw_bundle_bytes(encode_manifest(manifest), payload, **overrides)


def _padded(record, blob: bytes) -> bytes:
    return blob + b"\x00" * (record["mesh"]["blobLength"] - len(blob))


class _CodecTestCase(unittest.TestCase):
    def assert_code(self, code, function, *args, **kwargs) -> PreviewFormatError:
        with self.assertRaises(PreviewFormatError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        return caught.exception


class AlignmentAndHeaderTests(_CodecTestCase):
    def test_align8_rounds_up_to_the_alignment_unit(self) -> None:
        for value, expected in ((0, 0), (1, 8), (7, 8), (8, 8), (9, 16), (16, 16)):
            self.assertEqual(align8(value), expected)

    def test_align8_rejects_negative_lengths(self) -> None:
        with self.assertRaises(ValueError):
            align8(-1)

    def test_header_round_trip(self) -> None:
        header = decode_header(encode_header(123))
        self.assertEqual(header.version, FORMAT_VERSION)
        self.assertEqual(header.flags, 0)
        self.assertEqual(header.reserved, 0)
        self.assertEqual(header.manifest_length, 123)
        self.assertEqual(header.data_base, align8(HEADER_SIZE + 123))

    def test_header_truncated(self) -> None:
        self.assert_code("HEADER_TRUNCATED", decode_header, b"BPXV")

    def test_bad_magic(self) -> None:
        self.assert_code("BAD_MAGIC", decode_header, _header(magic=b"BPXW"))

    def test_unsupported_format_version(self) -> None:
        self.assert_code(
            "UNSUPPORTED_FORMAT_VERSION", decode_header, _header(version=2)
        )

    def test_unknown_flags(self) -> None:
        self.assert_code("UNKNOWN_FLAGS", decode_header, _header(flags=1))

    def test_reserved_word_must_be_zero(self) -> None:
        self.assert_code("RESERVED_NONZERO", decode_header, _header(reserved=1))

    def test_manifest_length_must_be_positive(self) -> None:
        self.assert_code(
            "MANIFEST_LENGTH_INVALID", decode_header, _header(manifest_length=0)
        )

    def test_manifest_length_above_limit(self) -> None:
        self.assert_code(
            "MANIFEST_LENGTH_INVALID",
            decode_header,
            _header(manifest_length=MAX_MANIFEST_BYTES + 1),
        )

    def test_encode_header_rejects_out_of_range_lengths(self) -> None:
        for length in (0, -1, MAX_MANIFEST_BYTES + 1):
            self.assert_code("MANIFEST_LENGTH_INVALID", encode_header, length)


class ManifestCodecTests(_CodecTestCase):
    def test_manifest_is_canonical_utf8_without_bom(self) -> None:
        encoded = encode_manifest({"b": 1, "a": "名称"})
        self.assertEqual(encoded, '{"a":"名称","b":1}'.encode("utf-8"))
        self.assertFalse(encoded.startswith(b"\xef\xbb\xbf"))

    def test_manifest_round_trip(self) -> None:
        manifest = _manifest([], [])
        self.assertEqual(decode_manifest(encode_manifest(manifest)), manifest)

    def test_manifest_rejects_non_finite_numbers(self) -> None:
        self.assert_code(
            "MANIFEST_NOT_JSON", encode_manifest, {"value": float("nan")}
        )

    def test_manifest_rejects_duplicate_json_members(self) -> None:
        self.assert_code(
            "MANIFEST_DUPLICATE_MEMBER", decode_manifest, b'{"a":1,"a":2}'
        )

    def test_manifest_rejects_non_standard_json_constants(self) -> None:
        self.assert_code("MANIFEST_NOT_JSON", decode_manifest, b'{"a":NaN}')

    def test_manifest_rejects_byte_order_mark(self) -> None:
        self.assert_code("MANIFEST_BOM", decode_manifest, b'\xef\xbb\xbf{"a":1}')

    def test_manifest_rejects_invalid_utf8(self) -> None:
        self.assert_code("MANIFEST_NOT_UTF8", decode_manifest, b'{"a":"\xff"}')

    def test_manifest_rejects_non_object_json(self) -> None:
        self.assert_code("MANIFEST_NOT_OBJECT", decode_manifest, b"[]")


class ManifestValidationTests(_CodecTestCase):
    def test_valid_manifest_passes(self) -> None:
        record, _ = _prototype()
        instance = _instance("case/part", record["prototypeKey"])
        validate_manifest(_manifest([record], [instance]))

    def test_unknown_top_level_fields_are_ignored(self) -> None:
        manifest = _manifest([], [], future={"lod": []})
        validate_manifest(manifest)
        self.assertEqual(decode_manifest(encode_manifest(manifest))["future"], {"lod": []})

    def test_unknown_schema_is_rejected(self) -> None:
        self.assert_code(
            "UNKNOWN_SCHEMA", validate_manifest, _manifest([], [], schema="other")
        )

    def test_unsupported_schema_version_is_rejected(self) -> None:
        self.assert_code(
            "UNSUPPORTED_SCHEMA_VERSION",
            validate_manifest,
            _manifest([], [], schemaVersion=2),
        )

    def test_bad_preview_key_is_rejected(self) -> None:
        self.assert_code(
            "BAD_KEY", validate_manifest, _manifest([], [], previewKey="not-a-key")
        )

    def test_units_must_be_millimetres(self) -> None:
        self.assert_code(
            "BAD_MANIFEST_FIELD", validate_manifest, _manifest([], [], units="cm")
        )

    def test_prototype_count_limit(self) -> None:
        self.assert_code(
            "COUNT_LIMIT",
            validate_manifest,
            _manifest([], [], prototypeCount=MAX_PROTOTYPES + 1),
        )

    def test_instance_count_limit(self) -> None:
        self.assert_code(
            "COUNT_LIMIT",
            validate_manifest,
            _manifest([], [], instanceCount=MAX_INSTANCES + 1),
        )

    def test_leaf_count_limit(self) -> None:
        self.assert_code(
            "COUNT_LIMIT",
            validate_manifest,
            _manifest([], [], leafCount=MAX_LEAVES + 1),
        )

    def test_count_must_match_array_length(self) -> None:
        self.assert_code(
            "BAD_MANIFEST_FIELD",
            validate_manifest,
            _manifest([], [], prototypeCount=1),
        )

    def test_duplicate_prototype_keys_are_rejected(self) -> None:
        record, _ = _prototype()
        self.assert_code(
            "DUPLICATE_PROTOTYPE_KEY", validate_manifest, _manifest([record, record], [])
        )

    def test_duplicate_face_keys_are_rejected(self) -> None:
        record, _ = _prototype(
            positions=(0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0),
            indices=(0, 1, 2, 1, 3, 2),
            face_ids=(0, 1),
            face_keys=("body:0", "body:0"),
        )
        self.assert_code(
            "DUPLICATE_FACE_KEY", validate_manifest, _manifest([record], [])
        )

    def test_bad_bounds_are_rejected(self) -> None:
        record, _ = _prototype(
            record_overrides={"bounds": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]}
        )
        self.assert_code("BAD_BOUNDS", validate_manifest, _manifest([record], []))

    def test_bad_face_count_is_rejected(self) -> None:
        record, _ = _prototype(mesh_overrides={"faceCount": 2})
        self.assert_code("BAD_FACE_COUNT", validate_manifest, _manifest([record], []))

    def test_bad_index_count_is_rejected(self) -> None:
        record, _ = _prototype(mesh_overrides={"indexCount": 4})
        self.assert_code("BAD_INDEX_COUNT", validate_manifest, _manifest([record], []))

    def test_bad_edge_point_count_is_rejected(self) -> None:
        record, _ = _prototype(mesh_overrides={"edgePointCount": 3})
        self.assert_code("BAD_EDGE_COUNT", validate_manifest, _manifest([record], []))

    def test_bad_blob_length_is_rejected(self) -> None:
        record, blob = _prototype()
        record["mesh"]["blobLength"] = align8(len(blob)) + 8
        self.assert_code("BAD_BLOB_LENGTH", validate_manifest, _manifest([record], []))

    def test_bad_blob_alignment_is_rejected(self) -> None:
        record, _ = _prototype(mesh_overrides={"offset": 1})
        self.assert_code(
            "BAD_BLOB_ALIGNMENT", validate_manifest, _manifest([record], [])
        )

    def test_layout_can_be_deferred_to_the_encoder(self) -> None:
        record, _ = _prototype(mesh_overrides={"offset": 3, "blobLength": 0})
        validate_manifest(_manifest([record], []), require_layout=False)

    def test_duplicate_instance_paths_are_rejected(self) -> None:
        record, _ = _prototype()
        instance = _instance("case/part", record["prototypeKey"])
        self.assert_code(
            "DUPLICATE_INSTANCE_PATH",
            validate_manifest,
            _manifest([record], [instance, dict(instance)]),
        )

    def test_instance_must_resolve_its_prototype(self) -> None:
        instance = _instance("case/part", _UNKNOWN_KEY)
        self.assert_code(
            "MISSING_PROTOTYPE", validate_manifest, _manifest([], [instance])
        )

    def test_bad_matrix_is_rejected(self) -> None:
        record, _ = _prototype()
        instance = _instance("case/part", record["prototypeKey"], matrix=[0.0] * 15)
        self.assert_code("BAD_MATRIX", validate_manifest, _manifest([record], [instance]))

    def test_bad_color_is_rejected(self) -> None:
        record, _ = _prototype()
        instance = _instance("case/part", record["prototypeKey"], color="blue")
        self.assert_code("BAD_COLOR", validate_manifest, _manifest([record], [instance]))

    def test_bad_opacity_is_rejected(self) -> None:
        record, _ = _prototype()
        instance = _instance("case/part", record["prototypeKey"], opacity=1.5)
        self.assert_code(
            "BAD_OPACITY", validate_manifest, _manifest([record], [instance])
        )

    def test_parent_path_must_follow_from_path(self) -> None:
        record, _ = _prototype()
        instance = _instance(
            "case/part", record["prototypeKey"], parentPath="elsewhere"
        )
        self.assert_code(
            "BAD_INSTANCE_FIELD", validate_manifest, _manifest([record], [instance])
        )


class BundleRoundTripTests(_CodecTestCase):
    def _two_prototypes(self):
        record_a, blob_a = _prototype(positions=(1.5, 0.0, 0.0, 0.0, 2.25, 0.0, 0.0, 0.0, 3.75))
        record_b, blob_b = _prototype(
            positions=(0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0),
            indices=(0, 1, 2, 1, 3, 2),
            face_ids=(0, 1),
            edge_points=(0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0),
            face_keys=("body:0", "body:1"),
        )
        return (record_a, blob_a), (record_b, blob_b)

    def test_round_trip_preserves_manifest_and_arrays(self) -> None:
        (record_a, blob_a), (record_b, blob_b) = self._two_prototypes()
        instances = [
            _instance("case/part_a", record_a["prototypeKey"]),
            _instance(
                "case/part_b",
                record_b["prototypeKey"],
                matrix=[float(value) for value in range(16)],
            ),
        ]
        manifest, blobs = _bundle_inputs(
            [(record_a, blob_a), (record_b, blob_b)], instances
        )
        original = copy.deepcopy(manifest)

        data = encode_bundle(manifest, blobs)
        self.assertEqual(manifest, original)

        bundle = decode_bundle(data)
        self.assertEqual(
            bundle.header.manifest_length, len(encode_manifest(bundle.manifest))
        )
        self.assertEqual(
            bundle.data_base, align8(HEADER_SIZE + bundle.header.manifest_length)
        )
        self.assertEqual(
            bundle.manifest["instances"][1]["matrix"],
            [float(value) for value in range(16)],
        )
        self.assertEqual(
            bundle.manifest["prototypes"][0]["mesh"]["offset"],
            0,
        )
        self.assertEqual(
            bundle.manifest["prototypes"][1]["mesh"]["offset"],
            align8(len(blob_a)),
        )
        arrays_a = bundle.prototypes[record_a["prototypeKey"]]
        self.assertEqual(
            list(arrays_a.positions), [1.5, 0.0, 0.0, 0.0, 2.25, 0.0, 0.0, 0.0, 3.75]
        )
        self.assertEqual(list(arrays_a.indices), [0, 1, 2])
        self.assertEqual(list(arrays_a.face_ids), [0])
        arrays_b = bundle.prototypes[record_b["prototypeKey"]]
        self.assertEqual(list(arrays_b.face_ids), [0, 1])
        self.assertEqual(list(arrays_b.indices), [0, 1, 2, 1, 3, 2])

    def test_bundle_offsets_are_relative_to_data_base_and_little_endian(self) -> None:
        (record_a, blob_a), (record_b, blob_b) = self._two_prototypes()
        manifest, blobs = _bundle_inputs(
            [(record_a, blob_a), (record_b, blob_b)], []
        )
        data = encode_bundle(manifest, blobs)
        bundle = decode_bundle(data)
        first = bundle.manifest["prototypes"][0]["mesh"]
        second = bundle.manifest["prototypes"][1]["mesh"]
        self.assertEqual(
            data[bundle.data_base : bundle.data_base + len(blob_a)], blob_a
        )
        self.assertEqual(
            data[
                bundle.data_base
                + second["offset"] : bundle.data_base
                + second["offset"]
                + len(blob_b)
            ],
            blob_b,
        )
        self.assertEqual(
            data[bundle.data_base : bundle.data_base + 4], struct.pack("<f", 1.5)
        )
        self.assertEqual(first["offset"], 0)

    def test_empty_bundle_has_no_prototypes(self) -> None:
        manifest = _manifest([], [])
        data = encode_bundle(manifest, {})
        bundle = decode_bundle(data)
        self.assertEqual(bundle.prototypes, {})
        self.assertEqual(len(data), bundle.data_base)

    def test_empty_prototype_arrays_round_trip(self) -> None:
        record, blob = _prototype(
            positions=(), indices=(), face_ids=(), edge_points=(), face_keys=()
        )
        manifest, blobs = _bundle_inputs([(record, blob)], [])
        bundle = decode_bundle(encode_bundle(manifest, blobs))
        arrays = bundle.prototypes[record["prototypeKey"]]
        self.assertEqual(len(arrays.positions), 0)
        self.assertEqual(len(arrays.indices), 0)
        self.assertEqual(len(arrays.face_ids), 0)
        self.assertEqual(len(arrays.edges), 0)
        self.assertEqual(bundle.manifest["prototypes"][0]["mesh"]["blobLength"], 0)

    def test_unknown_manifest_fields_survive_round_trip(self) -> None:
        manifest = _manifest([], [], future={"lod": []})
        bundle = decode_bundle(encode_bundle(manifest, {}))
        self.assertEqual(bundle.manifest["future"], {"lod": []})

    def test_pack_and_unpack_arrays(self) -> None:
        blob = pack_prototype_blob(
            [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            [0, 1, 2],
            [7],
            [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
        )
        arrays = unpack_prototype_blob(
            blob, position_count=3, index_count=3, edge_point_count=2
        )
        self.assertEqual(
            list(arrays.positions), [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        )
        self.assertEqual(list(arrays.indices), [0, 1, 2])
        self.assertEqual(list(arrays.face_ids), [7])
        self.assertEqual(list(arrays.edges), [0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
        self.assertEqual(prototype_blob_size(3, 3, 2), len(blob))


class BundleRejectionTests(_CodecTestCase):
    def test_bad_magic(self) -> None:
        manifest = _manifest([], [])
        self.assert_code(
            "BAD_MAGIC", decode_bundle, _raw_bundle(manifest, magic=b"BPXW")
        )

    def test_unsupported_format_version(self) -> None:
        manifest = _manifest([], [])
        self.assert_code(
            "UNSUPPORTED_FORMAT_VERSION", decode_bundle, _raw_bundle(manifest, version=2)
        )

    def test_unknown_flags(self) -> None:
        manifest = _manifest([], [])
        self.assert_code("UNKNOWN_FLAGS", decode_bundle, _raw_bundle(manifest, flags=1))

    def test_reserved_word_must_be_zero(self) -> None:
        manifest = _manifest([], [])
        self.assert_code(
            "RESERVED_NONZERO", decode_bundle, _raw_bundle(manifest, reserved=1)
        )

    def test_header_only_bundle_is_truncated(self) -> None:
        self.assert_code(
            "BUNDLE_TRUNCATED", decode_bundle, _header(manifest_length=8)
        )

    def test_truncated_bundle_without_prototypes(self) -> None:
        data = encode_bundle(_manifest([], []), {})
        self.assert_code("BUNDLE_TRUNCATED", decode_bundle, data[:-1])

    def test_truncated_prototype_blob(self) -> None:
        record, blob = _prototype()
        manifest, blobs = _bundle_inputs([(record, blob)], [])
        data = encode_bundle(manifest, blobs)
        self.assert_code("BAD_BLOB_RANGE", decode_bundle, data[:-1])

    def test_header_padding_must_be_zero(self) -> None:
        self.assert_code(
            "PADDING_NONZERO",
            decode_bundle,
            _raw_bundle_bytes(b'{"x":1}', padding=b"\x01"),
        )

    def test_prototype_padding_must_be_zero(self) -> None:
        record, blob = _prototype()
        allocated = align8(len(blob))
        self.assertGreater(allocated, len(blob))
        payload = blob + b"\x01" * (allocated - len(blob))
        data = _raw_bundle(_manifest([record], []), payload)
        self.assert_code("PADDING_NONZERO", decode_bundle, data)

    def test_blob_offset_must_be_aligned(self) -> None:
        record, blob = _prototype()
        record["mesh"]["offset"] = 1
        data = _raw_bundle(_manifest([record], []), payload=blob)
        self.assert_code("BAD_BLOB_ALIGNMENT", decode_bundle, data)

    def test_blob_offset_must_stay_inside_the_bundle(self) -> None:
        record, blob = _prototype()
        record["mesh"]["offset"] = 8192
        data = _raw_bundle(_manifest([record], []), payload=blob)
        self.assert_code("BAD_BLOB_RANGE", decode_bundle, data)

    def test_overlapping_blobs_are_rejected(self) -> None:
        record_a, blob_a = _prototype()
        record_b, blob_b = _prototype(
            positions=(1.0, 0.0, 0.0, 2.0, 0.0, 0.0, 1.0, 1.0, 0.0)
        )
        record_a["mesh"]["offset"] = 0
        record_b["mesh"]["offset"] = 0
        payload = _padded(record_a, blob_a) + _padded(record_b, blob_b)
        data = _raw_bundle(_manifest([record_a, record_b], []), payload)
        self.assert_code("BAD_BLOB_OVERLAP", decode_bundle, data)

    def test_nonzero_gap_between_blobs_is_rejected(self) -> None:
        record_a, blob_a = _prototype()
        record_b, blob_b = _prototype(
            positions=(1.0, 0.0, 0.0, 2.0, 0.0, 0.0, 1.0, 1.0, 0.0)
        )
        allocated_a = align8(len(blob_a))
        record_b["mesh"]["offset"] = allocated_a + 8
        payload = (
            _padded(record_a, blob_a)
            + b"\x01" * 8
            + _padded(record_b, blob_b)
        )
        data = _raw_bundle(_manifest([record_a, record_b], []), payload)
        self.assert_code("PADDING_NONZERO", decode_bundle, data)

    def test_trailing_bytes_are_rejected(self) -> None:
        data = _raw_bundle(_manifest([], []), payload=b"\x00")
        self.assert_code("BUNDLE_TRAILING_BYTES", decode_bundle, data)

    def test_out_of_range_index_is_rejected(self) -> None:
        record, blob = _prototype()
        tampered = bytearray(blob)
        struct.pack_into("<I", tampered, 36, 99)
        data = _raw_bundle(_manifest([record], []), _padded(record, bytes(tampered)))
        self.assert_code("BAD_INDEX", decode_bundle, data)

    def test_out_of_range_face_id_is_rejected(self) -> None:
        record, blob = _prototype()
        tampered = bytearray(blob)
        struct.pack_into("<I", tampered, 48, 1)
        data = _raw_bundle(_manifest([record], []), _padded(record, bytes(tampered)))
        self.assert_code("BAD_FACE_ID", decode_bundle, data)

    def test_prototype_key_must_match_mesh_bytes(self) -> None:
        record, blob = _prototype()
        tampered = bytearray(blob)
        struct.pack_into("<f", tampered, 0, 9.0)
        data = _raw_bundle(_manifest([record], []), _padded(record, bytes(tampered)))
        self.assert_code("PROTOTYPE_KEY_MISMATCH", decode_bundle, data)

    def test_bundle_size_limit(self) -> None:
        data = encode_bundle(_manifest([], []), {})
        with patch("cadwork.service.preview_format.MAX_BUNDLE_BYTES", 32):
            self.assert_code("BUNDLE_TOO_LARGE", decode_bundle, data)


class BundleEncodingTests(_CodecTestCase):
    def test_missing_blob_is_rejected(self) -> None:
        record, _ = _prototype()
        manifest = _manifest([record], [])
        self.assert_code("MISSING_PROTOTYPE", encode_bundle, manifest, {})

    def test_unknown_blob_is_rejected(self) -> None:
        record, blob = _prototype()
        manifest = _manifest([record], [])
        self.assert_code(
            "UNUSED_PROTOTYPE",
            encode_bundle,
            manifest,
            {record["prototypeKey"]: blob, _UNKNOWN_KEY: b""},
        )

    def test_short_blob_is_rejected(self) -> None:
        record, blob = _prototype()
        manifest = _manifest([record], [])
        self.assert_code(
            "BAD_BLOB_LENGTH",
            encode_bundle,
            manifest,
            {record["prototypeKey"]: blob[:-4]},
        )

    def test_invalid_face_id_is_rejected(self) -> None:
        record, blob = _prototype(face_ids=(1,))
        manifest = _manifest([record], [])
        self.assert_code(
            "BAD_FACE_ID",
            encode_bundle,
            manifest,
            {record["prototypeKey"]: blob},
        )

    def test_invalid_manifest_is_rejected(self) -> None:
        manifest = _manifest([], [], schema="other")
        self.assert_code("UNKNOWN_SCHEMA", encode_bundle, manifest, {})

    def test_encoder_assigns_layout_and_leaves_manifest_untouched(self) -> None:
        record_a, blob_a = _prototype()
        record_b, blob_b = _prototype(
            positions=(1.0, 0.0, 0.0, 2.0, 0.0, 0.0, 1.0, 1.0, 0.0)
        )
        record_a["mesh"]["offset"] = 999
        record_b["mesh"]["offset"] = 1024
        record_b["mesh"]["blobLength"] = 0
        manifest = _manifest([record_a, record_b], [])
        snapshot = copy.deepcopy(manifest)

        bundle = decode_bundle(
            encode_bundle(
                manifest,
                {
                    record_a["prototypeKey"]: blob_a,
                    record_b["prototypeKey"]: blob_b,
                },
            )
        )
        self.assertEqual(manifest, snapshot)
        self.assertEqual(bundle.manifest["prototypes"][0]["mesh"]["offset"], 0)
        self.assertEqual(
            bundle.manifest["prototypes"][1]["mesh"]["offset"], align8(len(blob_a))
        )


class DigestAndKeyTests(_CodecTestCase):
    def test_mesh_digest_covers_exact_array_bytes(self) -> None:
        blob = pack_prototype_blob(
            [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            [0, 1, 2],
            [0],
            [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
        )
        self.assertEqual(prototype_mesh_digest(blob), hashlib.sha256(blob).hexdigest())

    def test_prototype_key_uses_the_documented_material(self) -> None:
        digest = "e" * 64
        expected = hashlib.sha256(
            (
                "brepx-prototype\n"
                f"{MANIFEST_SCHEMA_VERSION}\n"
                f"{_SOURCE_IDENTITY}\n"
                f"{_PROFILE}\n"
                f"{_KERNEL}\n"
                f"{digest}"
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(
            prototype_key(
                schema_version=MANIFEST_SCHEMA_VERSION,
                source_identity=_SOURCE_IDENTITY,
                tessellation_profile=_PROFILE,
                kernel_version=_KERNEL,
                mesh_digest=digest,
            ),
            expected,
        )


if __name__ == "__main__":
    unittest.main()
