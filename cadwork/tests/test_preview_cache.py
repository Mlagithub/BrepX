"""Regression tests for preview cache atomicity and corrupt-manifest misses."""

from __future__ import annotations

import hashlib
import os
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from unittest.mock import patch

import cadwork.service.preview as preview_module
from cadwork.design.assembly import Instance, PartRef, Transform, new_assembly_document
from cadwork.design.document import apply_ops
from cadwork.service import store as store_module
from cadwork.service.preview import ensure_preview, gc_previews, load_preview
from cadwork.service.preview_format import PreviewFormatError, decode_manifest
from cadwork.service.service import CADService, ServiceError
from cadwork.service.store import Store

_TEST_KEY = "ab" * 32
_OTHER_KEY = "cd" * 32
_DEEP_ARRAY = b"[" * 5000 + b"]" * 5000
_HUGE_INTEGER = b'{"a":' + b"1" * 5000 + b"}"


def _manifest(preview_key: str = _TEST_KEY) -> dict:
    return {
        "schema": "brepx-assembly-preview",
        "schemaVersion": 1,
        "previewKey": preview_key,
        "assembly": {
            "id": "a_test",
            "version": 1,
            "configuration": "default",
            "name": "test assembly",
        },
        "generator": {
            "version": "1",
            "kernel": "smlibpy 0.6.2",
            "tessellationProfile": "tessellation-standard",
        },
        "units": "mm",
        "rootOffset": [0.0, 0.0, 0.0],
        "prototypeCount": 0,
        "instanceCount": 0,
        "leafCount": 0,
        "sceneInstanceCount": 0,
        "frameCount": 0,
        "failedCount": 0,
        "suppressedCount": 0,
        "bom": {"rows": 0, "quantity": 0, "definitions": 0},
        "prototypes": [],
        "instances": [],
    }


class AtomicWriteRaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)

    def test_concurrent_reader_does_not_fail_manifest_writes(self) -> None:
        manifest = _manifest()
        self.store.put_preview_manifest(_TEST_KEY, manifest)
        errors: list[tuple[str, str]] = []

        def writer() -> None:
            for _ in range(500):
                try:
                    self.store.put_preview_manifest(_TEST_KEY, manifest)
                except Exception as exc:  # pragma: no cover - failure reporting
                    errors.append(("write", repr(exc)))
                    break

        def reader() -> None:
            for _ in range(500):
                try:
                    self.store.get_preview_manifest(_TEST_KEY)
                except Exception as exc:  # pragma: no cover - failure reporting
                    errors.append(("read", repr(exc)))
                    break

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        self.assertEqual(self.store.get_preview_manifest(_TEST_KEY), manifest)
        self.assertEqual(list(self.store.root.rglob("*.tmp")), [])

    def test_transient_permission_error_is_retried(self) -> None:
        target = self.store.root / "probe.bin"
        real_replace = os.replace
        attempts = {"count": 0}

        def flaky_replace(source, destination):
            attempts["count"] += 1
            if attempts["count"] <= 2:
                raise PermissionError("busy")
            return real_replace(source, destination)

        with patch(
            "cadwork.service.store.os.replace", side_effect=flaky_replace
        ) as replace_mock:
            self.store._atomic_write(target, b"payload")

        self.assertEqual(target.read_bytes(), b"payload")
        self.assertEqual(replace_mock.call_count, 3)
        self.assertEqual(list(self.store.root.rglob("*.tmp")), [])

    def test_permission_error_retries_are_bounded(self) -> None:
        target = self.store.root / "probe.bin"
        with patch(
            "cadwork.service.store.os.replace", side_effect=PermissionError("busy")
        ) as replace_mock, patch("cadwork.service.store.time.sleep") as sleep_mock:
            with self.assertRaises(PermissionError):
                self.store._atomic_write(target, b"payload")

        self.assertEqual(
            replace_mock.call_count, store_module._ATOMIC_REPLACE_ATTEMPTS
        )
        self.assertEqual(
            sleep_mock.call_count, store_module._ATOMIC_REPLACE_ATTEMPTS - 1
        )
        self.assertFalse(target.exists())
        self.assertEqual(list(self.store.root.rglob("*.tmp")), [])


class CorruptManifestMissTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)
        self.store.put_preview_manifest(_OTHER_KEY, _manifest(_OTHER_KEY))

    def _write_corrupt(self, payload: bytes) -> None:
        path = self.store.preview_manifest_path(_TEST_KEY)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    def test_deeply_nested_manifest_is_a_miss(self) -> None:
        self._write_corrupt(_DEEP_ARRAY)
        self.assertIsNone(self.store.get_preview_manifest(_TEST_KEY))
        self.assertEqual(
            self.store.get_preview_manifest(_OTHER_KEY), _manifest(_OTHER_KEY)
        )

    def test_huge_integer_manifest_is_a_miss(self) -> None:
        self._write_corrupt(_HUGE_INTEGER)
        self.assertIsNone(self.store.get_preview_manifest(_TEST_KEY))
        self.assertEqual(
            self.store.get_preview_manifest(_OTHER_KEY), _manifest(_OTHER_KEY)
        )

    def test_parser_limits_are_normalized_to_format_errors(self) -> None:
        for payload in (_DEEP_ARRAY, _HUGE_INTEGER):
            with self.subTest(payload=payload[:8]):
                with self.assertRaises(PreviewFormatError) as caught:
                    decode_manifest(payload)
                self.assertEqual(caught.exception.code, "MANIFEST_NOT_JSON")


class PreviewRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)
        part = self.store.create("part")
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
        self.part = self.store.save(part)
        assembly = new_assembly_document("assembly", seq=1)
        assembly = replace(
            assembly,
            instances=(
                Instance("blade", PartRef(self.part.id, 1), Transform()),
            ),
        )
        self.assembly = self.store.save_assembly(assembly)
        self.service = CADService(self.store)

    def _wait_ready(self, timeout: float = 20.0) -> dict:
        deadline = time.time() + timeout
        latest = None
        while time.time() < deadline:
            latest = self.service.assembly_preview(
                self.assembly.id, self.assembly.version
            )
            if latest["state"] == "ready":
                return latest
            time.sleep(0.01)
        self.fail(f"preview did not become ready: {latest}")

    def _wait_failed(self, preview_key: str, timeout: float = 20.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            job = self.service.preview_jobs.for_key(preview_key)
            if job is not None and job.status == "failed":
                return job
            time.sleep(0.005)
        self.fail("preview build did not fail within the timeout")

    def test_corrupt_manifest_rebuilds_without_a_server_error(self) -> None:
        for payload in (_DEEP_ARRAY, _HUGE_INTEGER):
            with self.subTest(payload=payload[:8]):
                ready = self._wait_ready()
                key = ready["previewKey"]
                self.store.preview_manifest_path(key).write_bytes(payload)

                started = self.service.assembly_preview(
                    self.assembly.id, self.assembly.version
                )
                self.assertEqual(started["state"], "building")
                rebuilt = self._wait_ready()

                self.assertEqual(rebuilt["previewKey"], key)
                self.assertEqual(rebuilt["bundle"], ready["bundle"])
                self.assertIsNotNone(self.store.get_preview_manifest(key))

    def test_failed_job_is_retried_after_the_failure_is_reported(self) -> None:
        with patch.object(
            self.service,
            "assembly_scene",
            side_effect=RuntimeError("scene failed"),
        ):
            started = self.service.assembly_preview(self.assembly.id)
            self.assertEqual(started["state"], "building")
            key = started["previewKey"]
            self._wait_failed(key)

            with self.assertRaises(ServiceError) as caught:
                self.service.assembly_preview(self.assembly.id)
            self.assertEqual(caught.exception.code, "PREVIEW_FAILED")
            self.assertFalse(self.store.preview_manifest_path(key).is_file())

        retry = self.service.assembly_preview(self.assembly.id)
        self.assertEqual(retry["state"], "building")
        ready = self._wait_ready()

        self.assertEqual(ready["previewKey"], key)
        self.assertIsNotNone(self.store.get_preview_manifest(key))

    def test_concurrent_rebuild_polling_never_returns_a_server_error(self) -> None:
        ready = self._wait_ready()
        key = ready["previewKey"]
        self.store.preview_manifest_path(key).write_bytes(_DEEP_ARRAY)

        real_replace = os.replace
        failures = {"count": 0}

        def flaky_replace(source, destination):
            if failures["count"] < 3:
                failures["count"] += 1
                raise PermissionError("simulated open reader")
            return real_replace(source, destination)

        errors: list[str] = []

        def poll() -> None:
            deadline = time.time() + 20.0
            while time.time() < deadline:
                try:
                    result = self.service.assembly_preview(
                        self.assembly.id, self.assembly.version
                    )
                except Exception as exc:  # pragma: no cover - failure reporting
                    errors.append(repr(exc))
                    return
                if result["state"] == "ready":
                    return
                time.sleep(0.005)
            errors.append("preview polling timed out")

        with patch("cadwork.service.store.os.replace", side_effect=flaky_replace):
            threads = [threading.Thread(target=poll) for _ in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        self.assertEqual(errors, [])
        self.assertIsNotNone(self.store.get_preview_manifest(key))


_GC_DEFINITION = "d_gc@1#default#{}"
_GC_METADATA = {
    "assembly_id": "a_gc",
    "configuration": "default",
    "name": "gc fixture",
    "overrides": {},
    "generator_version": "test-generator",
    "kernel_version": "kernel-a",
    "tessellation_profile": "profile-a",
}


def _gc_scene(vertex: float = 1.0) -> dict:
    return {
        "assembly": "a_gc",
        "version": 1,
        "definitions": {
            _GC_DEFINITION: {
                "definition_id": "d_gc",
                "version": 1,
                "configuration": "default",
                "overrides": {},
                "feature": _GC_DEFINITION,
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
                "definition_id": "d_gc",
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
                "definition_key": _GC_DEFINITION,
            }
        ],
        "bom": [
            {
                "document_id": "d_gc",
                "version": 1,
                "configuration": "default",
                "quantity": 1,
                "paths": ["part"],
            }
        ],
        "bbox": None,
        "metrics": {},
    }


def _gc_metadata(version: int) -> dict:
    return {**_GC_METADATA, "assembly_version": version}


def _preview_paths(store: Store, stored) -> list:
    paths = [store.preview_manifest_path(stored.preview_key)]
    paths.append(store.preview_bundle_path(stored.bundle_key))
    paths.extend(
        store.preview_prototype_path(record["prototypeKey"])
        for record in stored.manifest["prototypes"]
    )
    return paths


class ConcurrentPreviewBuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)

    def test_same_key_shares_one_build(self) -> None:
        scene = _gc_scene()
        metadata = _gc_metadata(1)
        calls: list[float] = []
        lock = threading.Lock()
        original = preview_module.plan_preview

        def counted(*args, **kwargs):
            with lock:
                calls.append(time.perf_counter())
            time.sleep(0.1)
            return original(*args, **kwargs)

        workers = 8
        barrier = threading.Barrier(workers)

        def run():
            barrier.wait()
            return ensure_preview(self.store, scene, **metadata)

        with patch.object(
            preview_module, "plan_preview", side_effect=counted
        ):
            with ThreadPoolExecutor(max_workers=workers) as pool:
                results = list(pool.map(lambda _: run(), range(workers)))

        self.assertEqual(len(calls), 1)
        self.assertEqual(len({result.preview_key for result in results}), 1)
        self.assertEqual(len({result.bundle_key for result in results}), 1)
        self.assertEqual(len({result.bundle for result in results}), 1)
        loaded = load_preview(self.store, results[0].preview_key)
        self.assertIsNotNone(loaded)


class PreviewGcTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(self.folder.name)

    def _build(self, version: int, vertex: float = 1.0):
        return ensure_preview(
            self.store,
            _gc_scene(vertex),
            **_gc_metadata(version),
        )

    def test_gc_keeps_current_lookup_and_removes_orphans(self) -> None:
        current = self._build(1)
        current_paths = _preview_paths(self.store, current)
        orphan_bundle = b"orphan-bundle-bytes"
        orphan_key = hashlib.sha256(orphan_bundle).hexdigest()
        self.store.put_preview_bundle(orphan_key, orphan_bundle)
        orphan_prototype = "ef" * 32
        self.store.put_preview_prototype(orphan_prototype, b"orphan-prototype")
        invalid_manifest = self.store.preview_manifest_path("12" * 32)
        invalid_manifest.parent.mkdir(parents=True, exist_ok=True)
        invalid_manifest.write_bytes(b"{")

        diagnostics = gc_previews(self.store)

        for path in current_paths:
            self.assertTrue(path.is_file(), path)
        self.assertIsNotNone(load_preview(self.store, current.preview_key))
        self.assertFalse(self.store.preview_bundle_path(orphan_key).exists())
        self.assertFalse(
            self.store.preview_prototype_path(orphan_prototype).exists()
        )
        self.assertFalse(invalid_manifest.exists())
        self.assertIn(orphan_key, diagnostics["deleted"]["bundles"])
        self.assertIn(orphan_prototype, diagnostics["deleted"]["prototypes"])
        self.assertEqual(diagnostics["entries"]["currentLookups"], 1)
        self.assertLess(
            diagnostics["after"]["bytes"], diagnostics["before"]["bytes"]
        )

    def test_gc_expires_old_lookup_and_keeps_shared_prototypes(self) -> None:
        old = self._build(1)
        current = self._build(2)
        old_manifest = self.store.preview_manifest_path(old.preview_key)
        old_bundle = self.store.preview_bundle_path(old.bundle_key)
        current_paths = _preview_paths(self.store, current)
        ancient = time.time() - 1000
        os.utime(old_manifest, (ancient, ancient))

        diagnostics = gc_previews(self.store, max_age_seconds=10)

        self.assertFalse(old_manifest.exists())
        self.assertFalse(old_bundle.exists())
        for path in current_paths:
            self.assertTrue(path.is_file(), path)
        self.assertIsNotNone(load_preview(self.store, current.preview_key))
        self.assertIn(old.preview_key, diagnostics["expiredLookups"])
        self.assertEqual(diagnostics["deleted"]["prototypes"], [])
        self.assertEqual(diagnostics["overBudgetBytes"], 0)

    def test_size_cap_evicts_old_lookup_before_current(self) -> None:
        old = self._build(1)
        current = self._build(2)
        current_manifest = self.store.preview_manifest_path(current.preview_key)
        current_bundle = self.store.preview_bundle_path(current.bundle_key)
        cap = current_manifest.stat().st_size + current_bundle.stat().st_size
        for record in current.manifest["prototypes"]:
            cap += self.store.preview_prototype_path(
                record["prototypeKey"]
            ).stat().st_size

        diagnostics = gc_previews(self.store, max_bytes=cap)

        self.assertTrue(current_manifest.is_file())
        self.assertTrue(current_bundle.is_file())
        self.assertFalse(
            self.store.preview_manifest_path(old.preview_key).exists()
        )
        self.assertIn(old.preview_key, diagnostics["evictedForSize"])
        self.assertEqual(diagnostics["overBudgetBytes"], 0)
        self.assertIsNotNone(load_preview(self.store, current.preview_key))

    def test_over_budget_keeps_the_current_lookup(self) -> None:
        current = self._build(1)
        diagnostics = gc_previews(self.store, max_bytes=1)
        self.assertTrue(
            self.store.preview_manifest_path(current.preview_key).is_file()
        )
        self.assertGreater(diagnostics["overBudgetBytes"], 0)
        self.assertIsNotNone(load_preview(self.store, current.preview_key))

    def test_service_exposes_gc_diagnostics(self) -> None:
        current = self._build(1)
        service = CADService(self.store)
        diagnostics = service.gc_previews()
        self.assertEqual(diagnostics["before"]["files"], diagnostics["after"]["files"] + diagnostics["deleted"]["files"])
        self.assertIsNotNone(load_preview(self.store, current.preview_key))


if __name__ == "__main__":
    unittest.main()
