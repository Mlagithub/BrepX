"""Content identity tests for preview lookups and immutable bundle bytes.

A preview lookup names an input identity; the bundle URL names exact bytes. These
tests drive the two identities apart deliberately: a repeated build either keeps
the same content key or produces a new one, and an old content URL keeps serving
the old bytes even after the lookup points elsewhere.
"""

from __future__ import annotations

import hashlib
import tempfile
import time
import unittest
from dataclasses import replace
from unittest.mock import patch

from fastapi.testclient import TestClient

import cadwork.service.preview as preview_module
from cadwork.design.assembly import (
    Instance,
    PartRef,
    Transform,
    new_assembly_document,
)
from cadwork.design.document import apply_ops
from cadwork.service import create_app
from cadwork.service.preview import (
    ensure_preview,
    load_preview,
    plan_preview,
    preview_key,
    write_preview,
)
from cadwork.service.preview_format import (
    PreviewFormatError,
    bundle_key,
    encode_bundle,
    validate_manifest,
)
from cadwork.service.service import CADService
from cadwork.service.store import Store, StoreError

_METADATA = {
    "assembly_id": "a_test",
    "assembly_version": 1,
    "configuration": "default",
    "name": "identity fixture",
    "overrides": {},
    "generator_version": "test-generator",
    "kernel_version": "kernel-a",
    "tessellation_profile": "profile-a",
}


def _scene(vertex: float = 1.0) -> dict:
    definition_key = "d_a@1#default#{}"
    return {
        "assembly": "a_test",
        "version": 1,
        "definitions": {
            definition_key: {
                "definition_id": "d_a",
                "version": 1,
                "configuration": "default",
                "overrides": {},
                "feature": definition_key,
                "faces": [
                    {
                        "index": 0,
                        "area": 0.5,
                        "vertices": [
                            [0.0, 0.0, 0.0],
                            [vertex, 0.0, 0.0],
                            [0.0, 1.0, 0.0],
                        ],
                        "triangles": [0, 1, 2],
                    }
                ],
                "edges": [
                    {
                        "index": 0,
                        "points": [[0.0, 0.0, 0.0], [vertex, 0.0, 0.0]],
                    }
                ],
                "metrics": {"volume": 1.0, "faces": 1, "edges": 1},
            }
        },
        "instances": [
            {
                "path": "part",
                "instance_id": "i_part",
                "definition_id": "d_a",
                "definition_kind": "part",
                "version": 1,
                "configuration": "default",
                "placement": {
                    "rotation": [
                        [1.0, 0.0, 0.0],
                        [0.0, 1.0, 0.0],
                        [0.0, 0.0, 1.0],
                    ],
                    "translation": [0.0, 0.0, 0.0],
                },
                "suppressed": False,
                "visible": True,
                "error": None,
                "definition_key": definition_key,
            }
        ],
        "bom": [
            {
                "document_id": "d_a",
                "version": 1,
                "configuration": "default",
                "quantity": 1,
                "paths": ["part"],
            }
        ],
        "bbox": None,
        "metrics": {},
    }


def _fixture_store(folder: str):
    store = Store(folder)
    service = CADService(store)
    part = store.create("blade")
    part = apply_ops(
        part,
        [
            {
                "op": "add",
                "feature": {
                    "id": "base",
                    "type": "k_box",
                    "params": {"length": 10.0, "width": 6.0, "height": 4.0},
                },
            }
        ],
    )
    part = store.save(part)
    assembly = new_assembly_document("identity", seq=2)
    assembly = replace(
        assembly,
        instances=(Instance("blade", PartRef(part.id, 1), Transform()),),
    )
    store.save_assembly(assembly)
    return store, service, assembly


class _IdentityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)

    def assert_code(self, code, function, *args, **kwargs):
        with self.assertRaises(Exception) as caught:
            function(*args, **kwargs)
        self.assertEqual(getattr(caught.exception, "code", None), code)


class BundleIdentityTests(_IdentityTestCase):
    def test_consecutive_identical_plans_share_content_key(self) -> None:
        first = plan_preview(_scene(), **_METADATA)
        second = plan_preview(_scene(), **_METADATA)
        self.assertEqual(first.preview_key, second.preview_key)
        self.assertEqual(first.bundle_key, second.bundle_key)
        self.assertEqual(first.bundle, second.bundle)
        self.assertEqual(first.prototype_keys, second.prototype_keys)
        self.assertEqual(first.bundle_key, bundle_key(first.bundle))
        self.assertEqual(
            len(first.bundle_key), 64
        )

    def test_changed_mesh_keeps_lookup_key_and_changes_content_key(self) -> None:
        first = plan_preview(_scene(1.0), **_METADATA)
        second = plan_preview(_scene(1.5), **_METADATA)
        self.assertEqual(first.preview_key, second.preview_key)
        self.assertNotEqual(first.bundle_key, second.bundle_key)
        self.assertNotEqual(first.prototype_keys, second.prototype_keys)

    def test_lookup_switch_leaves_old_content_url_immutable(self) -> None:
        first = plan_preview(_scene(1.0), **_METADATA)
        stored_first = write_preview(self.store, first)
        loaded_first = load_preview(self.store, first.preview_key)
        self.assertIsNotNone(loaded_first)
        self.assertEqual(loaded_first.bundle_key, first.bundle_key)
        self.assertEqual(loaded_first.bundle, first.bundle)

        second = plan_preview(_scene(1.5), **_METADATA)
        stored_second = write_preview(self.store, second)
        loaded_second = load_preview(self.store, second.preview_key)
        self.assertIsNotNone(loaded_second)
        self.assertEqual(loaded_second.bundle_key, second.bundle_key)
        self.assertEqual(loaded_second.bundle, second.bundle)

        service = CADService(self.store)
        self.assertEqual(
            service.preview_asset(stored_first.bundle_key), stored_first.bundle
        )
        self.assertEqual(
            service.preview_asset(stored_second.bundle_key), stored_second.bundle
        )
        self.assertNotEqual(
            self.store.preview_bundle_path(stored_first.bundle_key).read_bytes(),
            self.store.preview_bundle_path(stored_second.bundle_key).read_bytes(),
        )

    def test_warm_lookup_does_not_repack_the_scene(self) -> None:
        plan = plan_preview(_scene(), **_METADATA)
        write_preview(self.store, plan)
        with patch.object(
            preview_module,
            "pack_scene",
            side_effect=AssertionError("warm lookup must not pack geometry"),
        ):
            loaded = load_preview(self.store, plan.preview_key)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.bundle, plan.bundle)
            ensured = ensure_preview(self.store, {}, **_METADATA)
            self.assertEqual(ensured.preview_key, plan.preview_key)
            self.assertEqual(ensured.bundle_key, plan.bundle_key)

    def test_store_rejects_bytes_that_do_not_match_their_content_key(self) -> None:
        plan = plan_preview(_scene(), **_METADATA)
        self.assert_code(
            "BUNDLE_KEY_MISMATCH",
            self.store.put_preview_bundle,
            plan.bundle_key,
            b"not the bundle",
        )

    def test_lookup_without_a_bundle_key_is_a_miss(self) -> None:
        plan = plan_preview(_scene(), **_METADATA)
        self.store.put_preview_bundle(plan.bundle_key, plan.bundle)
        self.store.put_preview_manifest(plan.preview_key, dict(plan.manifest))
        self.assertIsNone(load_preview(self.store, plan.preview_key))

    def test_bundle_key_is_lookup_only(self) -> None:
        plan = plan_preview(_scene(), **_METADATA)
        validate_manifest({**plan.manifest, "bundleKey": plan.bundle_key})
        with self.assertRaises(PreviewFormatError) as caught:
            encode_bundle(
                {**plan.manifest, "bundleKey": plan.bundle_key},
                plan.prototype_blobs,
            )
        self.assertEqual(caught.exception.code, "BUNDLE_KEY_IN_BUNDLE")


class BundleHttpIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.app = create_app(self.folder.name)
        self.service = self.app.state.service
        self.store, _service, self.assembly = _fixture_store(self.service.store.root)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def _url(self, version=None):
        base = f"/api/assemblies/{self.assembly.id}/preview"
        return base if version is None else f"{base}?version={version}"

    def _wait_for_ready(self, timeout=20.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            response = self.client.get(self._url())
            if response.status_code == 200:
                return response
            self.assertEqual(response.status_code, 202, response.text)
            time.sleep(0.01)
        self.fail("preview build did not become ready")

    def test_api_exposes_bundle_key_and_rejects_lookup_key_url(self) -> None:
        first = self.client.get(self._url())
        self.assertEqual(first.status_code, 202, first.text)
        lookup_key = first.json()["previewKey"]
        ready = self._wait_for_ready()
        bundle_key_value = ready.headers["x-bundle-key"]
        self.assertEqual(ready.headers["x-preview-key"], lookup_key)
        self.assertEqual(
            hashlib.sha256(ready.content).hexdigest(), bundle_key_value
        )

        asset = self.client.get(f"/api/preview/{bundle_key_value}.bpx")
        self.assertEqual(asset.status_code, 200, asset.text)
        self.assertEqual(asset.headers["etag"], f'"{bundle_key_value}"')
        self.assertEqual(asset.content, ready.content)

        stale_lookup_url = self.client.get(f"/api/preview/{lookup_key}.bpx")
        self.assertEqual(stale_lookup_url.status_code, 404)

        warm = self.client.get(self._url())
        self.assertEqual(warm.status_code, 200)
        self.assertEqual(warm.content, ready.content)
        self.assertEqual(warm.headers["x-bundle-key"], bundle_key_value)

    def test_changed_bundle_file_is_never_served_under_its_old_url(self) -> None:
        ready = self._wait_for_ready()
        bundle_key_value = ready.headers["x-bundle-key"]
        self.store.preview_bundle_path(bundle_key_value).write_bytes(b"tampered")
        asset = self.client.get(f"/api/preview/{bundle_key_value}.bpx")
        self.assertEqual(asset.status_code, 404)


if __name__ == "__main__":
    unittest.main()
