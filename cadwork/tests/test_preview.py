"""Packing tests for assembly scene preview prototypes and instance rows."""

from __future__ import annotations

import hashlib
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from cadwork.design.assembly import PartRef, Transform
from cadwork.design.assembly_plan import (
    AssemblyPlan,
    Pattern,
    PlanInstance,
    compile_assembly_plan,
)
from cadwork.design.document import apply_ops
from cadwork.service import create_app
from cadwork.service.preview import (
    DEFAULT_COLOR,
    DEFAULT_OPACITY,
    PreviewError,
    ensure_preview,
    instance_matrix,
    is_preview_key,
    load_preview,
    overrides_digest,
    pack_scene,
    plan_preview,
    preview_key,
    prototype_key_for,
    write_preview,
)
from cadwork.service.preview_format import (
    MANIFEST_SCHEMA,
    MANIFEST_SCHEMA_VERSION,
    MANIFEST_UNITS,
    bundle_key,
    decode_bundle,
    encode_bundle,
    pack_prototype_blob,
    prototype_key,
    prototype_mesh_digest,
    validate_manifest,
)
from cadwork.service.service import (
    CADService,
    PREVIEW_DISABLED_ENV,
    ServiceError,
    assembly_preview_enabled,
)
from cadwork.service.store import Store

_IDENTITY_PLACEMENT = {
    "rotation": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    "translation": [0.0, 0.0, 0.0],
}
_DEFINITION_KEY = "d_source@1#default#{}"
_PROFILE = "test-profile"
_KERNEL = "smlibpy test"


def _face(index, vertices, triangles, area=0.5):
    return {
        "index": index,
        "vertices": vertices,
        "triangles": triangles,
        "area": area,
    }


def _edge(index, points):
    return {"index": index, "points": points}


def _definition(
    feature,
    *,
    faces,
    edges,
    metrics,
    document_id="d_source",
    version=1,
    configuration="default",
    overrides=None,
):
    return {
        "definition_id": document_id,
        "version": version,
        "configuration": configuration,
        "overrides": dict(overrides or {}),
        "feature": feature,
        "faces": faces,
        "edges": edges,
        "metrics": metrics,
    }


def _instance(
    path,
    *,
    definition_key=None,
    placement=None,
    suppressed=False,
    visible=True,
    kind="part",
    error=None,
):
    row = {
        "path": path,
        "instance_id": "i_" + path.replace("/", "_"),
        "definition_id": "d_source",
        "definition_kind": kind,
        "version": 1,
        "configuration": "default",
        "placement": placement or _IDENTITY_PLACEMENT,
        "suppressed": suppressed,
        "visible": visible,
        "error": error,
    }
    if definition_key is not None:
        row["definition_key"] = definition_key
    return row


def _base_definition():
    return _definition(
        _DEFINITION_KEY,
        faces=[
            _face(
                0,
                [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                [0, 1, 2],
            ),
            _face(
                1,
                [[2.0, 0.0, 0.0], [3.0, 0.0, 0.0], [2.0, 1.0, 0.0]],
                [0, 1, 2],
            ),
        ],
        edges=[
            _edge(0, [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
            _edge(
                1,
                [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0]],
            ),
        ],
        metrics={"volume": 1.0, "faces": 2, "edges": 2},
    )


def _scene(instances=None):
    return {
        "assembly": "a_test",
        "version": 1,
        "definitions": {_DEFINITION_KEY: _base_definition()},
        "instances": instances
        if instances is not None
        else [
            _instance("module/part_a", definition_key=_DEFINITION_KEY),
            _instance("module/part_b", definition_key=_DEFINITION_KEY),
        ],
        "bom": [],
        "bbox": None,
        "metrics": {},
    }


def _apply(matrix, point):
    return tuple(
        matrix[row] * point[0]
        + matrix[4 + row] * point[1]
        + matrix[8 + row] * point[2]
        + matrix[12 + row]
        for row in range(3)
    )


def _build_fixture(store):
    service = CADService(store)

    def part(name, height):
        document = store.create(name)
        document = apply_ops(
            document,
            [
                {
                    "op": "add",
                    "feature": {
                        "id": "base",
                        "type": "k_box",
                        "params": {
                            "length": 10.0,
                            "width": 6.0,
                            "height": height,
                        },
                    },
                }
            ],
        )
        return store.save(document)

    blade = part("blade", 4.0)
    disk = part("disk", 6.0)
    plan = AssemblyPlan(
        "assembly_preview_fixture",
        "assembly_preview_fixture",
        (
            PlanInstance("disk", PartRef(disk.id, 1), Transform()),
            PlanInstance(
                "blade",
                PartRef(blade.id, 1),
                placement=Transform(translation=(0.0, 0.0, 3.0)),
                pattern=Pattern("polar", 6, radius=30.0),
            ),
        ),
    )
    assembly = compile_assembly_plan(plan)
    store.save_assembly(assembly)
    return service.assembly_scene(assembly.id), assembly, service


def _plan_metadata():
    return {
        "assembly_id": "a_test",
        "assembly_version": 1,
        "configuration": "default",
        "name": "fixture",
        "overrides": {},
        "generator_version": "test-generator",
        "kernel_version": _KERNEL,
        "tessellation_profile": _PROFILE,
    }


def _two_definition_scene(second_vertex):
    first_key = "d_a@1#default#{}"
    second_key = "d_b@1#default#{}"
    definitions = {
        first_key: _definition(
            first_key,
            document_id="d_a",
            faces=[
                _face(
                    0,
                    [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                    [0, 1, 2],
                )
            ],
            edges=[],
            metrics={"volume": 1.0, "faces": 1, "edges": 0},
        ),
        second_key: _definition(
            second_key,
            document_id="d_b",
            faces=[
                _face(
                    0,
                    [
                        [0.0, 0.0, 0.0],
                        [second_vertex, 0.0, 0.0],
                        [0.0, 1.0, 0.0],
                    ],
                    [0, 1, 2],
                )
            ],
            edges=[],
            metrics={"volume": 1.0, "faces": 1, "edges": 0},
        ),
    }
    return {
        "assembly": "a_test",
        "version": 1,
        "definitions": definitions,
        "instances": [
            _instance("first", definition_key=first_key),
            _instance("second", definition_key=second_key),
        ],
        "bom": [],
        "bbox": None,
        "metrics": {},
    }


class _PackingTestCase(unittest.TestCase):
    def assert_code(self, code, function, *args, **kwargs):
        with self.assertRaises(PreviewError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        return caught.exception


class PrototypePackingTests(_PackingTestCase):
    def test_faces_edges_bounds_and_metrics_are_flattened(self) -> None:
        packed = pack_scene(_scene())
        prototype = packed.prototypes[_DEFINITION_KEY]

        self.assertEqual(
            prototype.mesh.positions,
            (0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0,
             2.0, 0.0, 0.0, 3.0, 0.0, 0.0, 2.0, 1.0, 0.0),
        )
        self.assertEqual(prototype.mesh.indices, (0, 1, 2, 3, 4, 5))
        self.assertEqual(prototype.mesh.face_ids, (0, 1))
        self.assertEqual(
            prototype.face_keys, (f"{_DEFINITION_KEY}:0", f"{_DEFINITION_KEY}:1")
        )
        self.assertEqual(
            prototype.mesh.edge_points,
            (
                0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                1.0, 0.0, 0.0, 1.0, 1.0, 0.0,
            ),
        )
        self.assertEqual(prototype.mesh.position_count, 6)
        self.assertEqual(prototype.mesh.index_count, 6)
        self.assertEqual(prototype.face_count, 2)
        self.assertEqual(prototype.mesh.edge_point_count, 6)
        self.assertEqual(prototype.bounds, ((0.0, 0.0, 0.0), (3.0, 1.0, 0.0)))
        self.assertEqual(dict(prototype.metrics), {
            "volume": 1.0,
            "area": 1.0,
            "faces": 2,
            "edges": 2,
        })
        self.assertEqual(prototype.source_document_id, "d_source")
        self.assertEqual(prototype.source_version, 1)
        self.assertEqual(prototype.source_identity, _DEFINITION_KEY)
        self.assertEqual(prototype.face_key_source, "ordinal")

    def test_instances_share_one_prototype(self) -> None:
        packed = pack_scene(_scene())
        self.assertEqual(packed.prototype_count, 1)
        self.assertEqual(packed.instance_count, 2)
        self.assertEqual(
            [row.path for row in packed.instances],
            ["module/part_a", "module/part_b"],
        )

    def test_empty_definition_has_zero_bounds_and_counts(self) -> None:
        key = _DEFINITION_KEY
        definition = _definition(
            key,
            faces=[],
            edges=[],
            metrics={"volume": 0.0, "faces": 0, "edges": 0},
        )
        packed = pack_scene(
            {
                "assembly": "a_test",
                "version": 1,
                "definitions": {key: definition},
                "instances": [],
                "bom": [],
            }
        )
        prototype = packed.prototypes[key]
        self.assertEqual(prototype.mesh.positions, ())
        self.assertEqual(prototype.mesh.indices, ())
        self.assertEqual(prototype.mesh.face_ids, ())
        self.assertEqual(prototype.mesh.edge_points, ())
        self.assertEqual(prototype.bounds, ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
        self.assertEqual(prototype.metrics["area"], 0.0)

    def test_out_of_range_local_index_is_rejected(self) -> None:
        key = _DEFINITION_KEY
        definition = _definition(
            key,
            faces=[
                _face(
                    0,
                    [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
                    [0, 1, 2],
                )
            ],
            edges=[],
            metrics={"volume": 0.0, "faces": 1, "edges": 0},
        )
        scene = {
            "assembly": "a_test",
            "version": 1,
            "definitions": {key: definition},
            "instances": [],
            "bom": [],
        }
        self.assert_code("BAD_INDEX", pack_scene, scene)

    def test_definition_key_must_match_its_identity(self) -> None:
        key = _DEFINITION_KEY
        scene = {
            "assembly": "a_test",
            "version": 1,
            "definitions": {"other": _definition(
                key,
                faces=[],
                edges=[],
                metrics={"volume": 0.0, "faces": 0, "edges": 0},
            )},
            "instances": [],
            "bom": [],
        }
        self.assert_code("DEFINITION_KEY_MISMATCH", pack_scene, scene)

    def test_legacy_empty_override_key_is_normalized(self) -> None:
        legacy = "d_source@1#default"
        scene = {
            "assembly": "a_test",
            "version": 1,
            "definitions": {legacy: _definition(
                legacy,
                faces=[],
                edges=[],
                metrics={"volume": 0.0, "faces": 0, "edges": 0},
            )},
            "instances": [],
            "bom": [],
        }
        packed = pack_scene(scene)
        self.assertEqual(
            packed.prototypes[legacy].source_identity,
            "d_source@1#default#{}",
        )


class InstancePackingTests(_PackingTestCase):
    def test_column_major_matrix_matches_the_scene_rotation(self) -> None:
        placement = {
            "rotation": [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
            "translation": [10.0, 20.0, 30.0],
        }
        matrix = instance_matrix(placement)
        self.assertEqual(
            matrix,
            (0.0, 1.0, 0.0, 0.0,
             -1.0, 0.0, 0.0, 0.0,
             0.0, 0.0, 1.0, 0.0,
             10.0, 20.0, 30.0, 1.0),
        )
        point = (1.0, 0.0, 0.0)
        expected = (
            placement["rotation"][0][0] * point[0]
            + placement["rotation"][0][1] * point[1]
            + placement["rotation"][0][2] * point[2]
            + placement["translation"][0],
            placement["rotation"][1][0] * point[0]
            + placement["rotation"][1][1] * point[1]
            + placement["rotation"][1][2] * point[2]
            + placement["translation"][1],
            placement["rotation"][2][0] * point[0]
            + placement["rotation"][2][1] * point[1]
            + placement["rotation"][2][2] * point[2]
            + placement["translation"][2],
        )
        for actual, wanted in zip(_apply(matrix, point), expected):
            self.assertAlmostEqual(actual, wanted, places=12)

    def test_parent_path_and_module_follow_the_instance_path(self) -> None:
        packed = pack_scene(
            _scene(
                [
                    _instance("outer/module/part", definition_key=_DEFINITION_KEY),
                    _instance("root_part", definition_key=_DEFINITION_KEY),
                ]
            )
        )
        first, second = packed.instances
        self.assertEqual(first.parent_path, "outer/module")
        self.assertEqual(first.module, "outer")
        self.assertEqual(second.parent_path, "")
        self.assertEqual(second.module, "root_part")

    def test_defaults_and_visibility_are_carried(self) -> None:
        packed = pack_scene(
            _scene(
                [
                    _instance(
                        "hidden",
                        definition_key=_DEFINITION_KEY,
                        visible=False,
                    )
                ]
            )
        )
        row = packed.instances[0]
        self.assertEqual(row.color, DEFAULT_COLOR)
        self.assertEqual(row.opacity, DEFAULT_OPACITY)
        self.assertFalse(row.visible)
        self.assertFalse(row.suppressed)

    def test_duplicate_instance_paths_are_rejected(self) -> None:
        scene = _scene(
            [
                _instance("same/path", definition_key=_DEFINITION_KEY),
                _instance("same/path", definition_key=_DEFINITION_KEY),
            ]
        )
        self.assert_code("DUPLICATE_INSTANCE_PATH", pack_scene, scene)

    def test_non_renderable_rows_are_counted_not_packed(self) -> None:
        scene = _scene(
            [
                _instance("good", definition_key=_DEFINITION_KEY),
                _instance(
                    "hidden", definition_key=_DEFINITION_KEY, visible=False
                ),
                _instance("frame", kind="assembly"),
                _instance("suppressed", suppressed=True),
                _instance("failed", error={"code": "DEFINITION_FAILED"}),
                _instance("unresolved"),
            ]
        )
        packed = pack_scene(scene)
        self.assertEqual(packed.scene_instance_count, 6)
        self.assertEqual(packed.frame_count, 1)
        self.assertEqual(packed.failed_count, 1)
        self.assertEqual(packed.suppressed_count, 1)
        self.assertEqual(packed.instance_count, 2)
        self.assertEqual(
            [row.path for row in packed.instances], ["good", "hidden"]
        )
        self.assertEqual(
            {row.source_definition_key for row in packed.instances},
            {_DEFINITION_KEY},
        )


class SevenInstanceFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.folder = tempfile.TemporaryDirectory()
        cls.store = Store(cls.folder.name)
        cls.scene, cls.assembly, cls.service = _build_fixture(cls.store)
        cls.packed = pack_scene(cls.scene)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.folder.cleanup()

    def test_counts_match_the_built_scene(self) -> None:
        self.assertEqual(self.scene["metrics"]["definitions"], 2)
        self.assertEqual(self.scene["metrics"]["instances"], 7)
        self.assertEqual(self.scene["metrics"]["failures"], 0)
        self.assertEqual(self.packed.prototype_count, 2)
        self.assertEqual(self.packed.instance_count, 7)
        self.assertEqual(self.packed.scene_instance_count, 7)
        self.assertEqual(self.packed.frame_count, 0)
        self.assertEqual(self.packed.failed_count, 0)
        self.assertEqual(self.packed.suppressed_count, 0)

    def test_every_index_and_face_id_is_in_range(self) -> None:
        self.assertEqual(len(self.packed.prototypes), 2)
        for prototype in self.packed.prototypes.values():
            mesh = prototype.mesh
            self.assertEqual(prototype.face_count, len(prototype.face_keys))
            self.assertEqual(prototype.face_count, 6)
            self.assertEqual(len(mesh.face_ids), mesh.index_count // 3)
            self.assertEqual(mesh.edge_point_count % 2, 0)
            for index in mesh.indices:
                self.assertGreaterEqual(index, 0)
                self.assertLess(index, mesh.position_count)
            for face_id in mesh.face_ids:
                self.assertGreaterEqual(face_id, 0)
                self.assertLess(face_id, len(prototype.face_keys))
            for face_key in prototype.face_keys:
                self.assertTrue(
                    face_key.startswith(prototype.source_definition_key + ":")
                )

    def test_prototype_bounds_match_the_local_boxes(self) -> None:
        by_volume = {
            round(float(prototype.metrics["volume"])): prototype
            for prototype in self.packed.prototypes.values()
        }
        self.assertEqual(set(by_volume), {240, 360})
        blade = by_volume[240]
        disk = by_volume[360]
        self.assertEqual(
            blade.bounds, ((-5.0, -3.0, -2.0), (5.0, 3.0, 2.0))
        )
        self.assertEqual(
            disk.bounds, ((-5.0, -3.0, -3.0), (5.0, 3.0, 3.0))
        )

    def test_instance_matrices_match_scene_placements(self) -> None:
        raw_rows = {row["path"]: row for row in self.scene["instances"]}
        self.assertEqual(
            [row.path for row in self.packed.instances],
            [row["path"] for row in self.scene["instances"]],
        )
        for row in self.packed.instances:
            raw = raw_rows[row.path]
            self.assertEqual(row.matrix, instance_matrix(raw["placement"]))
            self.assertEqual(row.source_definition_key, raw["definition_key"])
            self.assertEqual(row.instance_id, raw["instance_id"])
            self.assertEqual(row.parent_path, "")
            self.assertEqual(row.module, row.path)
            self.assertTrue(row.visible)
            self.assertFalse(row.suppressed)
            self.assertEqual(row.color, DEFAULT_COLOR)
            self.assertEqual(row.opacity, DEFAULT_OPACITY)
            translation = raw["placement"]["translation"]
            for actual, wanted in zip(
                _apply(row.matrix, (0.0, 0.0, 0.0)), translation
            ):
                self.assertAlmostEqual(actual, wanted, places=12)

    def test_packed_arrays_round_trip_through_the_codec(self) -> None:
        manifest, blobs, keys = self._codec_inputs()
        validate_manifest(manifest, require_layout=False)
        bundle = decode_bundle(encode_bundle(manifest, blobs))
        self.assertEqual(bundle.manifest["prototypeCount"], 2)
        self.assertEqual(bundle.manifest["instanceCount"], 7)
        self.assertEqual(len(bundle.prototypes), 2)
        for definition_key, prototype in self.packed.prototypes.items():
            key = keys[definition_key]
            arrays = bundle.prototypes[key]
            self.assertEqual(
                pack_prototype_blob(
                    arrays.positions,
                    arrays.indices,
                    arrays.face_ids,
                    arrays.edges,
                ),
                blobs[key],
            )
            self.assertEqual(
                bundle.manifest["prototypes"][
                    [record["prototypeKey"] for record in bundle.manifest["prototypes"]].index(key)
                ]["sourceDefinitionKey"],
                definition_key,
            )
            self.assertEqual(prototype.mesh.position_count, len(arrays.positions) // 3)

    def _codec_inputs(self):
        manifest_prototypes = []
        blobs: dict[str, bytes] = {}
        keys: dict[str, str] = {}
        for definition_key, prototype in self.packed.prototypes.items():
            blob = pack_prototype_blob(
                prototype.mesh.positions,
                prototype.mesh.indices,
                prototype.mesh.face_ids,
                prototype.mesh.edge_points,
            )
            key = prototype_key(
                schema_version=MANIFEST_SCHEMA_VERSION,
                source_identity=prototype.source_identity,
                tessellation_profile=_PROFILE,
                kernel_version=_KERNEL,
                mesh_digest=prototype_mesh_digest(blob),
            )
            blobs[key] = blob
            keys[definition_key] = key
            manifest_prototypes.append(
                {
                    "prototypeKey": key,
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
                        "positionCount": prototype.mesh.position_count,
                        "indexCount": prototype.mesh.index_count,
                        "faceCount": prototype.face_count,
                        "edgePointCount": prototype.mesh.edge_point_count,
                    },
                }
            )
        manifest_instances = [
            {
                "path": row.path,
                "parentPath": row.parent_path,
                "instanceId": row.instance_id,
                "prototypeKey": keys[row.source_definition_key],
                "sourceDefinitionKey": row.source_definition_key,
                "matrix": list(row.matrix),
                "color": row.color,
                "opacity": row.opacity,
                "visible": row.visible,
                "suppressed": row.suppressed,
                "module": row.module,
            }
            for row in self.packed.instances
        ]
        bom_rows = self.scene["bom"]
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "schemaVersion": MANIFEST_SCHEMA_VERSION,
            "previewKey": "a" * 64,
            "assembly": {
                "id": self.scene["assembly"],
                "version": self.scene["version"],
                "configuration": "default",
                "name": "fixture",
            },
            "generator": {
                "version": "test",
                "kernel": _KERNEL,
                "tessellationProfile": _PROFILE,
            },
            "units": MANIFEST_UNITS,
            "rootOffset": [0.0, 0.0, 0.0],
            "prototypeCount": len(manifest_prototypes),
            "instanceCount": len(manifest_instances),
            "leafCount": len(manifest_instances),
            "sceneInstanceCount": self.packed.scene_instance_count,
            "frameCount": self.packed.frame_count,
            "failedCount": self.packed.failed_count,
            "suppressedCount": self.packed.suppressed_count,
            "bom": {
                "rows": len(bom_rows),
                "quantity": sum(int(row["quantity"]) for row in bom_rows),
                "definitions": len(
                    {
                        f"{row['document_id']}@{row['version']}#"
                        f"{row['configuration']}"
                        for row in bom_rows
                    }
                ),
            },
            "prototypes": manifest_prototypes,
            "instances": manifest_instances,
        }
        return manifest, blobs, keys


def _key_inputs(**overrides):
    inputs = {
        "assembly_id": "a_test",
        "assembly_version": 3,
        "configuration": "default",
        "overrides": {},
        "generator_version": "generator-a",
        "kernel_version": "kernel-a",
        "tessellation_profile": "profile-a",
        "schema_version": MANIFEST_SCHEMA_VERSION,
    }
    inputs.update(overrides)
    return inputs


class PreviewKeyTests(_PackingTestCase):
    def test_preview_key_material_matches_the_identity_contract(self) -> None:
        digest = hashlib.sha256(b"{}").hexdigest()
        material = "\n".join(
            (
                "brepx-preview",
                str(MANIFEST_SCHEMA_VERSION),
                "a_test",
                "3",
                "default",
                digest,
                "generator-a",
                "kernel-a",
                "profile-a",
            )
        )
        self.assertEqual(
            preview_key(**_key_inputs()),
            hashlib.sha256(material.encode("utf-8")).hexdigest(),
        )

    def test_each_identity_input_changes_the_preview_key(self) -> None:
        seen = {preview_key(**_key_inputs())}
        variants = [
            {"assembly_id": "a_other"},
            {"assembly_version": 4},
            {"configuration": "oversize"},
            {"overrides": {"length": 20.0}},
            {"generator_version": "generator-b"},
            {"kernel_version": "kernel-b"},
            {"tessellation_profile": "profile-b"},
            {"schema_version": 2},
        ]
        for variant in variants:
            key = preview_key(**_key_inputs(**variant))
            self.assertNotIn(key, seen, variant)
            seen.add(key)

    def test_absent_overrides_hash_the_empty_object(self) -> None:
        self.assertEqual(overrides_digest(None), overrides_digest({}))
        self.assertEqual(overrides_digest(None), hashlib.sha256(b"{}").hexdigest())
        self.assertEqual(
            overrides_digest({"b": 2.0, "a": 1.0}),
            overrides_digest({"a": 1.0, "b": 2.0}),
        )
        self.assertEqual(
            preview_key(**_key_inputs(overrides=None)),
            preview_key(**_key_inputs(overrides={})),
        )

    def test_invalid_key_inputs_are_rejected(self) -> None:
        self.assert_code(
            "BAD_KEY_INPUT", preview_key, **_key_inputs(assembly_id="")
        )
        self.assert_code(
            "BAD_KEY_INPUT", preview_key, **_key_inputs(assembly_version=0)
        )
        self.assert_code(
            "BAD_KEY_INPUT", preview_key, **_key_inputs(tessellation_profile="")
        )
        self.assert_code(
            "BAD_KEY_INPUT", preview_key, **_key_inputs(overrides=["bad"])
        )


class PrototypeIdentityTests(_PackingTestCase):
    def test_only_the_changed_definition_gets_a_new_prototype_key(self) -> None:
        metadata = _plan_metadata()
        first = plan_preview(_two_definition_scene(1.0), **metadata)
        second = plan_preview(_two_definition_scene(2.0), **metadata)
        self.assertEqual(first.preview_key, second.preview_key)
        changed = [
            key
            for key in first.prototype_keys
            if first.prototype_keys[key] != second.prototype_keys[key]
        ]
        self.assertEqual(changed, ["d_b@1#default#{}"])
        self.assertEqual(len(set(first.prototype_keys.values())), 2)

    def test_prototype_key_matches_the_codec_material(self) -> None:
        plan = plan_preview(_two_definition_scene(1.0), **_plan_metadata())
        generator = plan.manifest["generator"]
        for record in plan.manifest["prototypes"]:
            blob = plan.prototype_blobs[record["prototypeKey"]]
            expected = prototype_key(
                schema_version=plan.manifest["schemaVersion"],
                source_identity=record["sourceIdentity"],
                tessellation_profile=generator["tessellationProfile"],
                kernel_version=generator["kernel"],
                mesh_digest=prototype_mesh_digest(blob),
            )
            self.assertEqual(record["prototypeKey"], expected)

    def test_prototype_key_helper_uses_the_packed_bytes(self) -> None:
        packed = pack_scene(_two_definition_scene(1.0))
        metadata = _plan_metadata()
        for prototype in packed.prototypes.values():
            self.assertEqual(
                prototype_key_for(
                    prototype,
                    kernel_version=metadata["kernel_version"],
                    tessellation_profile=metadata["tessellation_profile"],
                ),
                prototype_key_for(
                    prototype,
                    kernel_version=metadata["kernel_version"],
                    tessellation_profile=metadata["tessellation_profile"],
                    blob=pack_prototype_blob(
                        prototype.mesh.positions,
                        prototype.mesh.indices,
                        prototype.mesh.face_ids,
                        prototype.mesh.edge_points,
                    ),
                ),
            )


class PreviewCacheTests(_PackingTestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)
        self.scene, self.assembly, self.service = _build_fixture(self.store)
        self.metadata = {
            "assembly_id": self.assembly.id,
            "assembly_version": self.assembly.version,
            "configuration": "default",
            "name": self.assembly.name,
            "overrides": {},
            "generator_version": "test-generator",
            "kernel_version": _KERNEL,
            "tessellation_profile": _PROFILE,
        }

    def _next_metadata(self):
        metadata = dict(self.metadata)
        metadata["assembly_version"] += 1
        return metadata

    @staticmethod
    def _key_for(metadata):
        return preview_key(
            assembly_id=metadata["assembly_id"],
            assembly_version=metadata["assembly_version"],
            configuration=metadata["configuration"],
            overrides=metadata["overrides"],
            generator_version=metadata["generator_version"],
            kernel_version=metadata["kernel_version"],
            tessellation_profile=metadata["tessellation_profile"],
        )

    def test_write_publishes_prototypes_bundle_and_manifest(self) -> None:
        plan = plan_preview(self.scene, **self.metadata)
        stored = write_preview(self.store, plan)
        self.assertTrue(is_preview_key(stored.preview_key))
        self.assertEqual(stored.preview_key, plan.preview_key)
        self.assertTrue(
            self.store.preview_manifest_path(plan.preview_key).is_file()
        )
        self.assertTrue(
            self.store.preview_bundle_path(plan.bundle_key).is_file()
        )
        self.assertEqual(
            self.store.preview_manifest_path(plan.preview_key).parent.name,
            "manifests",
        )
        self.assertEqual(
            self.store.preview_bundle_path(plan.bundle_key).parent.name,
            "bundles",
        )
        self.assertEqual(stored.bundle_key, plan.bundle_key)
        self.assertEqual(bundle_key(stored.bundle), stored.bundle_key)
        for prototype_key_value in plan.prototype_blobs:
            self.assertTrue(
                self.store.preview_prototype_path(prototype_key_value).is_file()
            )
            self.assertEqual(
                self.store.preview_prototype_path(prototype_key_value).parent.name,
                "prototypes",
            )
        self.assertEqual(stored.bundle, plan.bundle)
        loaded = load_preview(self.store, plan.preview_key)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.bundle, plan.bundle)
        self.assertEqual(loaded.manifest, plan.manifest)
        self.assertEqual(
            list((self.store.root / "previews").rglob("*.tmp")), []
        )

    def test_manifest_is_written_after_prototypes_and_bundle(self) -> None:
        plan = plan_preview(self.scene, **self.metadata)
        observed = {}
        original = self.store.put_preview_manifest

        def check(preview_key_value, manifest):
            observed["bundle"] = self.store.preview_bundle_path(
                plan.bundle_key
            ).is_file()
            observed["prototypes"] = all(
                self.store.preview_prototype_path(key).is_file()
                for key in plan.prototype_blobs
            )
            return original(preview_key_value, manifest)

        with patch.object(
            self.store, "put_preview_manifest", side_effect=check
        ):
            write_preview(self.store, plan)
        self.assertTrue(observed["bundle"])
        self.assertTrue(observed["prototypes"])

    def test_manifest_counts_and_bom_match_the_scene(self) -> None:
        stored = ensure_preview(self.store, self.scene, **self.metadata)
        manifest = stored.manifest
        self.assertEqual(manifest["prototypeCount"], 2)
        self.assertEqual(manifest["instanceCount"], 7)
        self.assertEqual(manifest["leafCount"], 7)
        self.assertEqual(manifest["sceneInstanceCount"], 7)
        self.assertEqual(manifest["frameCount"], 0)
        self.assertEqual(manifest["failedCount"], 0)
        self.assertEqual(manifest["suppressedCount"], 0)
        self.assertEqual(
            dict(manifest["bom"]),
            {"rows": 2, "quantity": 7, "definitions": 2},
        )
        prototype_keys = {
            record["prototypeKey"] for record in manifest["prototypes"]
        }
        self.assertEqual(len(prototype_keys), 2)
        packed = pack_scene(self.scene)
        self.assertEqual(
            [row["path"] for row in manifest["instances"]],
            [row.path for row in packed.instances],
        )
        for record, row in zip(manifest["instances"], packed.instances):
            self.assertIn(record["prototypeKey"], prototype_keys)
            self.assertEqual(record["sourceDefinitionKey"], row.source_definition_key)
            self.assertEqual(record["matrix"], list(row.matrix))

    def test_warm_read_returns_the_same_bytes_without_packing(self) -> None:
        first = ensure_preview(self.store, self.scene, **self.metadata)
        second = ensure_preview(
            self.store, {"definitions": "not-a-mapping"}, **self.metadata
        )
        self.assertEqual(second.preview_key, first.preview_key)
        self.assertEqual(second.bundle, first.bundle)
        self.assertEqual(second.manifest, first.manifest)

    def test_invalid_key_is_a_miss_without_touching_the_cache(self) -> None:
        self.assertFalse((self.store.root / "previews").exists())
        self.assertIsNone(load_preview(self.store, "short"))
        self.assertIsNone(load_preview(self.store, "A" * 64))
        self.assertFalse((self.store.root / "previews").exists())

    def test_truncated_manifest_is_a_miss_and_keeps_the_previous_preview(self) -> None:
        first = ensure_preview(self.store, self.scene, **self.metadata)
        other = self._next_metadata()
        other_key = self._key_for(other)
        manifest_path = self.store.preview_manifest_path(other_key)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_bytes(b"{")
        self.assertIsNone(load_preview(self.store, other_key))
        self.assertIsNotNone(load_preview(self.store, first.preview_key))
        self.assertTrue(manifest_path.is_file())

    def test_manifest_key_mismatch_is_a_miss_and_keeps_the_previous_preview(self) -> None:
        first = ensure_preview(self.store, self.scene, **self.metadata)
        other_key = self._key_for(self._next_metadata())
        other_path = self.store.preview_manifest_path(other_key)
        other_path.parent.mkdir(parents=True, exist_ok=True)
        other_path.write_bytes(
            self.store.preview_manifest_path(first.preview_key).read_bytes()
        )
        self.assertIsNone(load_preview(self.store, other_key))
        self.assertIsNotNone(load_preview(self.store, first.preview_key))

    def test_failed_manifest_write_keeps_the_previous_complete_preview(self) -> None:
        first = ensure_preview(self.store, self.scene, **self.metadata)
        other = self._next_metadata()
        other_key = self._key_for(other)
        with patch.object(
            self.store,
            "put_preview_manifest",
            side_effect=OSError("disk full"),
        ):
            with self.assertRaises(OSError):
                ensure_preview(self.store, self.scene, **other)
        self.assertIsNotNone(load_preview(self.store, first.preview_key))
        self.assertFalse(self.store.preview_manifest_path(other_key).is_file())

    def test_build_state_is_stored_under_previews_builds(self) -> None:
        path = self.store.put_preview_build(
            "build_1", {"state": "building", "progress": 0.5}
        )
        self.assertEqual(path.parent.name, "builds")
        self.assertEqual(
            self.store.get_preview_build("build_1"),
            {"state": "building", "progress": 0.5},
        )
        self.assertIsNone(self.store.get_preview_build("bad/id"))
        self.assertEqual(
            list((self.store.root / "previews").rglob("*.tmp")), []
        )

    def test_unchanged_prototypes_are_reused_for_a_new_preview_key(self) -> None:
        first = ensure_preview(self.store, self.scene, **self.metadata)
        prototype_paths = {
            record["prototypeKey"]: self.store.preview_prototype_path(
                record["prototypeKey"]
            )
            for record in first.manifest["prototypes"]
        }
        stamps = {
            key: path.stat().st_mtime_ns
            for key, path in prototype_paths.items()
        }
        second = ensure_preview(
            self.store, self.scene, **self._next_metadata()
        )
        self.assertNotEqual(second.preview_key, first.preview_key)
        self.assertEqual(
            sorted(
                record["prototypeKey"]
                for record in first.manifest["prototypes"]
            ),
            sorted(
                record["prototypeKey"]
                for record in second.manifest["prototypes"]
            ),
        )
        for key, path in prototype_paths.items():
            self.assertEqual(path.stat().st_mtime_ns, stamps[key])

    def test_assembly_revision_rewrites_manifest_and_bundle_without_rekeying(self) -> None:
        first = ensure_preview(self.store, self.scene, **self.metadata)
        first_manifest = self.store.preview_manifest_path(first.preview_key).read_bytes()
        first_bundle = self.store.preview_bundle_path(first.bundle_key).read_bytes()
        prototype_paths = {
            record["prototypeKey"]: self.store.preview_prototype_path(
                record["prototypeKey"]
            )
            for record in first.manifest["prototypes"]
        }
        stamps = {key: path.stat().st_mtime_ns for key, path in prototype_paths.items()}

        second = ensure_preview(self.store, self.scene, **self._next_metadata())

        self.assertNotEqual(second.preview_key, first.preview_key)
        self.assertNotEqual(
            self.store.preview_manifest_path(second.preview_key).read_bytes(),
            first_manifest,
        )
        self.assertNotEqual(
            self.store.preview_bundle_path(second.bundle_key).read_bytes(),
            first_bundle,
        )
        for key, path in prototype_paths.items():
            self.assertEqual(path.stat().st_mtime_ns, stamps[key])
        self.assertIsNotNone(load_preview(self.store, first.preview_key))
        self.assertIsNotNone(load_preview(self.store, second.preview_key))

    def test_removed_bundle_is_a_miss_for_only_its_preview(self) -> None:
        first = ensure_preview(self.store, self.scene, **self.metadata)
        second = ensure_preview(self.store, self.scene, **self._next_metadata())
        bundle_path = self.store.preview_bundle_path(second.bundle_key)
        original_bundle = bundle_path.read_bytes()
        bundle_path.unlink()

        self.assertIsNone(load_preview(self.store, second.preview_key))
        self.assertIsNotNone(load_preview(self.store, first.preview_key))
        self.assertTrue(
            self.store.preview_manifest_path(second.preview_key).is_file()
        )

        rebuilt = ensure_preview(self.store, self.scene, **self._next_metadata())
        self.assertEqual(rebuilt.preview_key, second.preview_key)
        self.assertEqual(rebuilt.bundle, original_bundle)
        self.assertIsNotNone(load_preview(self.store, second.preview_key))

    def test_changed_child_revision_rekeys_only_its_definition(self) -> None:
        first = ensure_preview(self.store, self.scene, **self.metadata)
        first_keys = {
            record["sourceDefinitionKey"]: record["prototypeKey"]
            for record in first.manifest["prototypes"]
        }
        first_paths = {
            key: self.store.preview_prototype_path(key) for key in first_keys.values()
        }
        first_stamps = {key: path.stat().st_mtime_ns for key, path in first_paths.items()}

        # The fixture's two definitions are one box of volume 240 and one of 360.
        blade_definition = next(
            definition
            for definition in self.scene["definitions"].values()
            if round(float(definition["metrics"]["volume"])) == 240
        )
        blade_id = blade_definition["definition_id"]
        blade_first = self.store.get_version(blade_id, 1)
        blade_second = apply_ops(
            blade_first,
            [{"op": "update", "id": "base", "params": {"height": 5.0}}],
        )
        self.store.save(blade_second)

        document = self.service.read_assembly(self.assembly.id)
        pins = [
            {"op": "update_pin", "id": instance.id, "version": 2}
            for instance in document.instances
            if isinstance(instance.ref, PartRef)
            and instance.ref.document_id == blade_id
        ]
        self.assertEqual(len(pins), 6)
        edited = self.service.edit_assembly(
            self.assembly.id, document.version, pins
        )
        version = edited["assembly"]["version"]
        updated = ensure_preview(
            self.store,
            self.service.assembly_scene(self.assembly.id, version),
            **{**self.metadata, "assembly_version": version},
        )
        updated_keys = {
            record["sourceDefinitionKey"]: record["prototypeKey"]
            for record in updated.manifest["prototypes"]
        }
        old_blade = next(
            definition
            for definition in first_keys
            if definition.startswith(blade_id + "@")
        )
        new_blade = next(
            definition
            for definition in updated_keys
            if definition.startswith(blade_id + "@2#")
        )
        disk_definition = next(
            definition
            for definition in first_keys
            if definition != old_blade
        )

        self.assertNotEqual(updated.preview_key, first.preview_key)
        self.assertEqual(updated_keys[disk_definition], first_keys[disk_definition])
        self.assertEqual(
            first_paths[first_keys[disk_definition]].stat().st_mtime_ns,
            first_stamps[first_keys[disk_definition]],
        )
        self.assertNotEqual(updated_keys[new_blade], first_keys[old_blade])
        self.assertTrue(
            self.store.preview_prototype_path(updated_keys[new_blade]).is_file()
        )
        self.assertTrue(
            self.store.preview_prototype_path(first_keys[old_blade]).is_file()
        )
        self.assertIsNotNone(load_preview(self.store, first.preview_key))
        self.assertEqual(dict(updated.manifest["bom"])["quantity"], 7)


def _wait_for_service_preview(service, assembly_id, version=None, timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = service.assembly_preview(assembly_id, version)
        if result["state"] == "ready":
            return result
        time.sleep(0.01)
    raise AssertionError("preview build did not become ready")


class PreviewFeatureFlagTests(unittest.TestCase):
    def _enabled(self, value):
        environment = dict(os.environ)
        if value is None:
            environment.pop(PREVIEW_DISABLED_ENV, None)
        else:
            environment[PREVIEW_DISABLED_ENV] = value
        with patch.dict(os.environ, environment, clear=True):
            return assembly_preview_enabled()

    def test_default_and_non_disabling_values_enable_preview(self) -> None:
        for value in (None, "", "1", "true", "on", "yes"):
            self.assertTrue(self._enabled(value), value)

    def test_zero_false_off_disable_preview(self) -> None:
        for value in ("0", "false", "off", " FALSE ", "Off"):
            self.assertFalse(self._enabled(value), value)


class PreviewServiceTests(_PackingTestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)
        self.scene, self.assembly, self.service = _build_fixture(self.store)

    def test_cold_request_builds_and_polling_reaches_ready(self) -> None:
        first = self.service.assembly_preview(self.assembly.id)
        self.assertEqual(first["state"], "building")
        self.assertTrue(first["buildId"])
        self.assertTrue(is_preview_key(first["previewKey"]))
        self.assertGreaterEqual(first["progress"], 0.0)
        self.assertLessEqual(first["progress"], 1.0)

        ready = _wait_for_service_preview(
            self.service, self.assembly.id, self.assembly.version
        )
        self.assertIsInstance(ready["bundle"], bytes)
        self.assertEqual(ready["manifest"]["instanceCount"], 7)
        self.assertEqual(
            self.service.preview_asset(ready["bundleKey"]),
            ready["bundle"],
        )

        warm = self.service.assembly_preview(self.assembly.id)
        self.assertEqual(warm["state"], "ready")
        self.assertEqual(warm["bundle"], ready["bundle"])
        self.assertEqual(warm["previewKey"], ready["previewKey"])

    def test_failed_build_reports_a_stable_code_and_keeps_the_old_preview(self) -> None:
        old = _wait_for_service_preview(
            self.service, self.assembly.id, self.assembly.version
        )
        edited = self.service.edit_assembly(
            self.assembly.id,
            self.assembly.version,
            [
                {
                    "op": "transform",
                    "id": "disk",
                    "placement": {
                        "rotation": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                        "translation": [5.0, 0.0, 0.0],
                    },
                }
            ],
        )
        new_version = edited["assembly"]["version"]
        failure = None
        with patch.object(
            self.service,
            "assembly_scene",
            side_effect=RuntimeError("scene failed"),
        ):
            started = self.service.assembly_preview(self.assembly.id, new_version)
            self.assertEqual(started["state"], "building")
            deadline = time.time() + 20.0
            while time.time() < deadline:
                try:
                    self.service.assembly_preview(self.assembly.id, new_version)
                except ServiceError as exc:
                    failure = exc
                    break
                time.sleep(0.01)
            self.assertIsNotNone(failure)
            self.assertEqual(failure.status, 500)
            self.assertEqual(failure.code, "PREVIEW_FAILED")
            self.assertEqual(
                failure.detail["fallback"]["previewKey"], old["previewKey"]
            )
            self.assertEqual(
                failure.detail["fallback"]["bundleKey"], old["bundleKey"]
            )
            self.assertEqual(
                failure.detail["fallback"]["bundleUrl"],
                f"/api/preview/{old['bundleKey']}.bpx",
            )
            self.assertEqual(
                failure.detail["fallback"]["assemblyVersion"],
                self.assembly.version,
            )
        preserved = self.service.assembly_preview(
            self.assembly.id, self.assembly.version
        )
        self.assertEqual(preserved["state"], "ready")
        self.assertEqual(preserved["bundle"], old["bundle"])

    def test_cancel_stops_before_preview_publish(self) -> None:
        scene = self.service.assembly_scene(self.assembly.id)

        def slow_scene(*args, **kwargs):
            time.sleep(0.3)
            return scene

        with patch.object(
            self.service, "assembly_scene", side_effect=slow_scene
        ):
            started = self.service.assembly_preview(self.assembly.id)
            self.assertEqual(started["state"], "building")
            cancel = self.service.cancel_preview_build(started["buildId"])
            self.assertIn(cancel["status"], {"cancelled", "cancelling"})
            job = self.service.preview_jobs.get(started["buildId"])
            deadline = time.time() + 20.0
            while job is not None and job.status == "cancelling":
                if time.time() >= deadline:
                    self.fail("preview build did not reach cancelled")
                time.sleep(0.01)
                job = self.service.preview_jobs.get(started["buildId"])
            self.assertIsNotNone(job)
            self.assertEqual(job.status, "cancelled")
            self.assertIsNone(load_preview(self.service.store, started["previewKey"]))
            self.assertFalse(
                self.service.store.preview_manifest_path(
                    started["previewKey"]
                ).exists()
            )
            bundle_dir = self.service.store.root / "previews" / "bundles"
            self.assertEqual(list(bundle_dir.glob("*.bpx")), [])
        ready = _wait_for_service_preview(
            self.service, self.assembly.id, self.assembly.version
        )
        self.assertEqual(ready["state"], "ready")

    def test_disabled_flag_rejects_preview_endpoints(self) -> None:
        ready = _wait_for_service_preview(
            self.service, self.assembly.id, self.assembly.version
        )
        with patch.dict(os.environ, {PREVIEW_DISABLED_ENV: "off"}):
            with self.assertRaises(ServiceError) as disabled:
                self.service.assembly_preview(self.assembly.id)
            self.assertEqual(disabled.exception.status, 503)
            self.assertEqual(disabled.exception.code, "PREVIEW_DISABLED")
            with self.assertRaises(ServiceError) as asset:
                self.service.preview_asset(ready["bundleKey"])
            self.assertEqual(asset.exception.status, 503)
            self.assertEqual(asset.exception.code, "PREVIEW_DISABLED")
        enabled = self.service.assembly_preview(self.assembly.id)
        self.assertEqual(enabled["state"], "ready")
        self.assertEqual(enabled["bundle"], ready["bundle"])

    def test_unknown_cancel_build_is_not_found(self) -> None:
        with self.assertRaises(ServiceError) as missing:
            self.service.cancel_preview_build("preview_missing")
        self.assertEqual(missing.exception.status, 404)

    def test_last_preview_fallback_survives_a_new_service(self) -> None:
        old = _wait_for_service_preview(
            self.service, self.assembly.id, self.assembly.version
        )
        edited = self.service.edit_assembly(
            self.assembly.id,
            self.assembly.version,
            [
                {
                    "op": "transform",
                    "id": "disk",
                    "placement": {
                        "rotation": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                        "translation": [5.0, 0.0, 0.0],
                    },
                }
            ],
        )
        fresh = CADService(self.store)
        failure = None
        with patch.object(
            fresh, "assembly_scene", side_effect=RuntimeError("scene failed")
        ):
            fresh.assembly_preview(
                self.assembly.id, edited["assembly"]["version"]
            )
            deadline = time.time() + 20.0
            while time.time() < deadline:
                try:
                    fresh.assembly_preview(
                        self.assembly.id, edited["assembly"]["version"]
                    )
                except ServiceError as exc:
                    failure = exc
                    break
                time.sleep(0.01)
        self.assertIsNotNone(failure)
        self.assertEqual(
            failure.detail["fallback"]["bundleKey"], old["bundleKey"]
        )

    def test_missing_assembly_and_version_are_not_found(self) -> None:
        with self.assertRaises(ServiceError) as missing:
            self.service.assembly_preview("a_missing")
        self.assertEqual(missing.exception.status, 404)
        with self.assertRaises(ServiceError) as missing_version:
            self.service.assembly_preview(self.assembly.id, 99)
        self.assertEqual(missing_version.exception.status, 404)


class PreviewHttpTests(_PackingTestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.app = create_app(self.folder.name)
        self.service = self.app.state.service
        _scene, self.assembly, _service = _build_fixture(self.service.store)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def _url(self, version=None):
        url = f"/api/assemblies/{self.assembly.id}/preview"
        if version is not None:
            url += f"?version={version}"
        return url

    def _wait_for_ready(self, version=None, timeout=20.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            response = self.client.get(self._url(version))
            if response.status_code == 200:
                return response
            self.assertEqual(response.status_code, 202, response.text)
            time.sleep(0.01)
        self.fail("preview build did not become ready")

    def test_cold_preview_polls_to_ready_and_serves_immutable_bytes(self) -> None:
        first = self.client.get(self._url())
        self.assertEqual(first.status_code, 202, first.text)
        body = first.json()
        self.assertEqual(body["state"], "building")
        self.assertTrue(body["buildId"])
        self.assertGreaterEqual(body["progress"], 0.0)
        self.assertLessEqual(body["progress"], 1.0)
        key = body["previewKey"]
        ready = self._wait_for_ready()
        self.assertEqual(
            ready.headers["content-type"],
            "application/vnd.brepx.assembly-preview",
        )
        self.assertEqual(ready.headers["cache-control"], "no-cache")
        bundle = ready.content
        bundle_key_value = ready.headers["x-bundle-key"]
        self.assertEqual(bundle_key(bundle), bundle_key_value)
        self.assertEqual(ready.headers["x-preview-key"], key)

        warm = self.client.get(self._url())
        self.assertEqual(warm.status_code, 200)
        self.assertEqual(warm.content, bundle)

        asset = self.client.get(f"/api/preview/{bundle_key_value}.bpx")
        self.assertEqual(asset.status_code, 200, asset.text)
        self.assertEqual(
            asset.headers["content-type"],
            "application/vnd.brepx.assembly-preview",
        )
        self.assertEqual(asset.headers["etag"], f'"{bundle_key_value}"')
        self.assertEqual(
            asset.headers["cache-control"],
            "public, max-age=31536000, immutable",
        )
        self.assertEqual(asset.content, bundle)

    def test_cors_exposes_preview_identity_headers(self) -> None:
        ready = self._wait_for_ready()
        self.assertEqual(ready.status_code, 200)
        response = self.client.get(
            self._url(),
            headers={"Origin": "http://127.0.0.1:3081"},
        )
        self.assertEqual(response.status_code, 200)
        exposed = response.headers.get("access-control-expose-headers", "").lower()
        self.assertIn("x-preview-key", exposed)
        self.assertIn("x-bundle-key", exposed)
        self.assertTrue(response.headers.get("x-preview-key"))
        self.assertTrue(response.headers.get("x-bundle-key"))

    def test_invalid_and_missing_keys_are_not_found(self) -> None:
        self.assertFalse((self.service.store.root / "previews").exists())
        for key in ("not-a-key", "A" * 64, "0" * 63):
            response = self.client.get(f"/api/preview/{key}.bpx")
            self.assertEqual(response.status_code, 404, key)
            self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")
        self.assertFalse((self.service.store.root / "previews").exists())
        missing = self.client.get(f"/api/preview/{'0' * 64}.bpx")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(
            self.client.get("/api/assemblies/a_missing/preview").status_code,
            404,
        )
        self.assertEqual(
            self.client.get(self._url(99)).status_code,
            404,
        )

    def test_disabled_flag_returns_a_stable_code(self) -> None:
        ready = self._wait_for_ready()
        bundle_key_value = ready.headers["x-bundle-key"]
        with patch.dict(os.environ, {PREVIEW_DISABLED_ENV: "false"}):
            response = self.client.get(self._url())
            self.assertEqual(response.status_code, 503, response.text)
            self.assertEqual(
                response.json()["error"]["code"], "PREVIEW_DISABLED"
            )
            asset = self.client.get(f"/api/preview/{bundle_key_value}.bpx")
            self.assertEqual(asset.status_code, 503, asset.text)
            self.assertEqual(
                asset.json()["error"]["code"], "PREVIEW_DISABLED"
            )
            invalid = self.client.get("/api/preview/not-a-key.bpx")
            self.assertEqual(invalid.status_code, 503)
        enabled = self.client.get(self._url())
        self.assertEqual(enabled.status_code, 200)
        self.assertEqual(enabled.content, ready.content)

    def test_failed_http_build_returns_500_and_keeps_the_previous_bundle(self) -> None:
        ready = self._wait_for_ready()
        old_bundle = ready.content
        old_version = self.assembly.version
        edited = self.service.edit_assembly(
            self.assembly.id,
            old_version,
            [
                {
                    "op": "transform",
                    "id": "disk",
                    "placement": {
                        "rotation": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                        "translation": [5.0, 0.0, 0.0],
                    },
                }
            ],
        )
        new_version = edited["assembly"]["version"]
        failure = None
        with patch.object(
            self.service,
            "assembly_scene",
            side_effect=RuntimeError("scene failed"),
        ):
            started = self.client.get(self._url(new_version))
            self.assertEqual(started.status_code, 202, started.text)
            deadline = time.time() + 20.0
            while time.time() < deadline:
                response = self.client.get(self._url(new_version))
                if response.status_code == 500:
                    failure = response
                    break
                self.assertEqual(response.status_code, 202, response.text)
                time.sleep(0.01)
            self.assertIsNotNone(failure)
            payload = failure.json()["error"]
            self.assertEqual(payload["code"], "PREVIEW_FAILED")
            fallback = payload["fallback"]
            self.assertEqual(
                fallback["previewKey"], ready.headers["x-preview-key"]
            )
            self.assertEqual(
                fallback["bundleKey"], ready.headers["x-bundle-key"]
            )
            self.assertEqual(
                fallback["bundleUrl"],
                f"/api/preview/{ready.headers['x-bundle-key']}.bpx",
            )
            self.assertEqual(fallback["assemblyVersion"], old_version)
        preserved = self.client.get(self._url(old_version))
        self.assertEqual(preserved.status_code, 200)
        self.assertEqual(preserved.content, old_bundle)

    def test_preview_cancel_endpoint_stops_the_worker(self) -> None:
        scene = self.service.assembly_scene(self.assembly.id)

        def slow_scene(*args, **kwargs):
            time.sleep(0.3)
            return scene

        with patch.object(
            self.service, "assembly_scene", side_effect=slow_scene
        ):
            first = self.client.get(self._url())
            self.assertEqual(first.status_code, 202, first.text)
            body = first.json()
            build_id = body["buildId"]
            preview_key = body["previewKey"]
            cancel = self.client.post(
                f"/api/preview/builds/{build_id}/cancel"
            )
            self.assertEqual(cancel.status_code, 200, cancel.text)
            self.assertIn(
                cancel.json()["status"], {"cancelled", "cancelling"}
            )
            job = self.service.preview_jobs.get(build_id)
            deadline = time.time() + 20.0
            while job is not None and job.status == "cancelling":
                if time.time() >= deadline:
                    self.fail("preview build did not reach cancelled")
                time.sleep(0.01)
                job = self.service.preview_jobs.get(build_id)
            self.assertIsNotNone(job)
            self.assertEqual(job.status, "cancelled")
            self.assertFalse(
                self.service.store.preview_manifest_path(preview_key).exists()
            )
        missing = self.client.post("/api/preview/builds/preview_missing/cancel")
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
