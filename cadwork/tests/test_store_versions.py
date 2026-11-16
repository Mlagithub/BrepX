"""Version snapshots are durable, independent of undo history."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest

from cadwork.design.document import apply_ops, document_to_json
from cadwork.service.store import Store, StoreError


def _box(feature_id: str, length: float = 10.0) -> dict:
    return {
        "op": "add",
        "feature": {
            "id": feature_id,
            "type": "k_box",
            "params": {"length": length, "width": 10.0, "height": 10.0},
        },
    }


class VersionStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.store = Store(self.folder.name)

    def tearDown(self) -> None:
        self.folder.cleanup()

    def _three_versions(self) -> str:
        document = self.store.create("versions")
        document = apply_ops(document, [_box("base", 10.0)])
        self.store.save(document)
        document = apply_ops(
            document, [{"op": "update", "id": "base", "params": {"length": 20.0}}]
        )
        self.store.save(document)
        document = apply_ops(
            document, [{"op": "update", "id": "base", "params": {"length": 30.0}}]
        )
        self.store.save(document)
        return document.id

    def test_each_version_is_readable(self) -> None:
        document_id = self._three_versions()
        for version, length in ((1, 10.0), (2, 20.0), (3, 30.0)):
            loaded = self.store.get_version(document_id, version)
            self.assertEqual(loaded.version, version)
            self.assertEqual(loaded.features[0].params["length"], length)
        self.assertEqual(self.store.list_versions(document_id), [0, 1, 2, 3])

    def test_prune_removes_snapshot_and_history(self) -> None:
        document_id = self._three_versions()
        removed = self.store.prune_versions(document_id, {1, 3})
        self.assertIn(2, removed)
        self.assertNotIn(1, removed)
        self.assertNotIn(3, removed)
        with self.assertRaises(StoreError) as caught:
            self.store.get_version(document_id, 2)
        self.assertEqual(caught.exception.code, "VERSION_NOT_FOUND")
        self.assertEqual(
            self.store.get_version(document_id, 3).features[0].params["length"], 30.0
        )

    def test_prune_keeps_current(self) -> None:
        document_id = self._three_versions()
        self.store.prune_versions(document_id, set())
        self.assertEqual(self.store.list_versions(document_id), [3])

    def test_flat_document_migrates_on_read(self) -> None:
        document = self.store.create("legacy")
        document = apply_ops(document, [_box("base", 12.0)])
        # Simulate a pre-snapshot store: current file only, no versions folder.
        path = self.store.root / f"{document.id}.json"
        path.write_text(
            json.dumps(document_to_json(document), ensure_ascii=False), encoding="utf-8"
        )
        saved = self.store.get(document.id)
        self.assertEqual(saved.version, 1)
        self.assertTrue(
            (self.store.root / "versions" / document.id / "1.json").is_file()
        )

    def test_concurrent_reads_do_not_corrupt(self) -> None:
        document_id = self._three_versions()
        errors: list[Exception] = []

        def read(version: int) -> None:
            try:
                for _ in range(20):
                    loaded = self.store.get_version(document_id, version)
                    self.assertEqual(loaded.version, version)
            except Exception as exc:  # pragma: no cover - assertion reporting
                errors.append(exc)

        threads = [
            threading.Thread(target=read, args=(version,)) for version in (1, 2, 3)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
