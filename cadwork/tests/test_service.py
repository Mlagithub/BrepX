"""Integration tests for the HTTP surface and the service layer."""

from __future__ import annotations

import json
import tempfile
import unittest

from fastapi.testclient import TestClient

from cadwork.design.document import feature_to_json
from cadwork.samples.impeller import impeller_document
from cadwork.service import create_app


def _impeller_ops() -> list[dict]:
    document = impeller_document()
    return [{"op": "add", "feature": feature_to_json(feature)} for feature in document.features]


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.app = create_app(self.folder.name)

    def _client(self) -> TestClient:
        return TestClient(self.app)

    def _create(self, client: TestClient) -> dict:
        response = client.post("/api/docs", json={"name": "T"})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def _build_impeller(self, client: TestClient) -> dict:
        document = self._create(client)
        response = client.put(
            f"/api/docs/{document['id']}",
            json={"base_version": document["version"], "ops": _impeller_ops()},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_health_and_catalog(self) -> None:
        with self._client() as client:
            self.assertEqual(client.get("/api/health").json()["status"], "ok")
            catalog = client.get("/api/catalog").json()
            self.assertEqual(len(catalog), 7)

    def test_build_impeller_through_the_api(self) -> None:
        with self._client() as client:
            payload = self._build_impeller(client)
            self.assertEqual(payload["document"]["version"], 2)
            self.assertEqual(len(payload["build"]["features"]), 9)
            self.assertEqual(sorted(payload["tags"]), ["f6", "f7", "f8"])

    def test_scene_and_etag(self) -> None:
        with self._client() as client:
            document_id = self._build_impeller(client)["document"]["id"]
            response = client.get(f"/api/docs/{document_id}/scene")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertGreater(len(payload["faces"]), 0)
            self.assertGreater(len(payload["edges"]), 0)
            etag = response.headers["etag"]
            again = client.get(f"/api/docs/{document_id}/scene",
                               headers={"If-None-Match": etag})
            self.assertEqual(again.status_code, 304)

    def test_preview_does_not_persist(self) -> None:
        with self._client() as client:
            document_id = self._build_impeller(client)["document"]["id"]
            response = client.post(
                f"/api/docs/{document_id}/preview",
                json={"ops": [{"op": "update", "id": "f3", "params": {"count": 11}}]},
            )
            self.assertEqual(response.status_code, 200, response.text)
            preview = response.json()
            self.assertIn("f3", preview["diff"]["changed"])
            current = client.get(f"/api/docs/{document_id}").json()
            self.assertEqual(current["version"], 2)
            self.assertEqual(current["features"][2]["params"]["count"], 9)

    def test_stale_version_is_rejected(self) -> None:
        with self._client() as client:
            document_id = self._build_impeller(client)["document"]["id"]
            response = client.put(
                f"/api/docs/{document_id}",
                json={"base_version": 1, "ops": []},
            )
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()["error"]["code"], "STALE_VERSION")

    def test_failed_build_leaves_document_unchanged(self) -> None:
        with self._client() as client:
            document_id = self._build_impeller(client)["document"]["id"]
            response = client.put(
                f"/api/docs/{document_id}",
                json={"base_version": 2,
                      "ops": [{"op": "update", "id": "f5", "params": {"radius": 2.0}}]},
            )
            self.assertEqual(response.status_code, 422, response.text)
            error = response.json()["error"]
            self.assertEqual(error["feature_id"], "f5")
            self.assertEqual(error["blocked_downstream"], ["f6", "f7", "f8", "f9"])
            current = client.get(f"/api/docs/{document_id}").json()
            self.assertEqual(current["version"], 2)

    def test_export_step_and_cfd(self) -> None:
        with self._client() as client:
            document_id = self._build_impeller(client)["document"]["id"]
            step = client.get(f"/api/docs/{document_id}/export/step")
            self.assertEqual(step.status_code, 200)
            self.assertGreater(len(step.content), 1000)
            self.assertIn("ISO-10303", step.content[:200].decode("latin-1"))
            cfd = client.get(f"/api/docs/{document_id}/export/cfd")
            self.assertEqual(cfd.status_code, 200)
            self.assertEqual(len(cfd.json()["boundaries"]), 3)

    def test_undo_restores_previous_version(self) -> None:
        with self._client() as client:
            document_id = self._build_impeller(client)["document"]["id"]
            response = client.post(f"/api/docs/{document_id}/undo")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["document"]["version"], 1)
            self.assertEqual(response.json()["document"]["features"], [])

    def test_store_survives_app_restart(self) -> None:
        with self._client() as client:
            document_id = self._build_impeller(client)["document"]["id"]
        with TestClient(create_app(self.folder.name)) as second:
            payload = second.get(f"/api/docs/{document_id}").json()
            self.assertEqual(payload["version"], 2)
            self.assertEqual(len(payload["features"]), 9)

    def test_web_assets_and_impeller_sample(self) -> None:
        with self._client() as client:
            index = client.get("/")
            self.assertEqual(index.status_code, 200)
            self.assertIn("importmap", index.text)
            for path in ("/web/src/main.js", "/web/vendor/three.module.js", "/web/style.css"):
                self.assertEqual(client.get(path).status_code, 200, path)
            document = self._create(client)
            sample = client.post(f"/api/docs/{document['id']}/sample/impeller")
            self.assertEqual(sample.status_code, 200, sample.text[:200])
            self.assertEqual(len(sample.json()["document"]["features"]), 9)

    def test_store_lists_newest_first(self) -> None:
        from cadwork.service.store import Store

        store = Store(self.folder.name + "/ordering")
        first = store.create("first")
        second = store.create("second")
        listed = store.list()
        self.assertEqual(listed[0]["id"], second.id)
        self.assertIn(first.id, [item["id"] for item in listed])

    def test_two_clients_conflict_then_retry(self) -> None:
        with self._client() as first, TestClient(create_app(self.folder.name)) as second:
            document = self._create(first)
            document_id = document["id"]
            hub = {"op": "add", "feature": {"id": "f1", "type": "hub_revolve"}}
            blade = {"op": "add", "feature": {"id": "f2", "type": "blade_loft"}}
            applied = first.put(
                f"/api/docs/{document_id}",
                json={"base_version": 1, "ops": [hub]},
            )
            self.assertEqual(applied.status_code, 200)

            stale = second.put(
                f"/api/docs/{document_id}",
                json={"base_version": 1, "ops": [blade]},
            )
            self.assertEqual(stale.status_code, 409)
            self.assertEqual(stale.json()["error"]["code"], "STALE_VERSION")

            retried = second.put(
                f"/api/docs/{document_id}",
                json={"base_version": 2, "ops": [blade]},
            )
            self.assertEqual(retried.status_code, 200, retried.text)
            self.assertEqual(len(retried.json()["document"]["features"]), 2)

    def test_undo_chain_and_exhaustion(self) -> None:
        with self._client() as client:
            document = self._create(client)
            document_id = document["id"]
            sequence = [
                {"op": "add", "feature": {"id": "f1", "type": "hub_revolve"}},
                {"op": "add", "feature": {"id": "f2", "type": "blade_loft"}},
                {"op": "add", "feature": {
                    "id": "f3", "type": "pattern_circular",
                    "refs": {"target": {"source": "f2", "select": "self"}},
                }},
            ]
            version = document["version"]
            for op in sequence:
                response = client.put(
                    f"/api/docs/{document_id}",
                    json={"base_version": version, "ops": [op]},
                )
                self.assertEqual(response.status_code, 200, response.text)
                version = response.json()["document"]["version"]
            self.assertEqual(version, 4)

            for expected_version, expected_features in ((3, 2), (2, 1), (1, 0)):
                undone = client.post(f"/api/docs/{document_id}/undo")
                self.assertEqual(undone.status_code, 200)
                self.assertEqual(undone.json()["document"]["version"], expected_version)
                self.assertEqual(len(undone.json()["document"]["features"]), expected_features)

            exhausted = client.post(f"/api/docs/{document_id}/undo")
            self.assertEqual(exhausted.status_code, 409)
            self.assertEqual(exhausted.json()["error"]["code"], "NO_HISTORY")

    def test_render_png(self) -> None:
        with self._client() as client:
            document_id = self._build_impeller(client)["document"]["id"]
            response = client.get(f"/api/docs/{document_id}/render.png")
            self.assertEqual(response.status_code, 200, response.text[:200])
            self.assertTrue(response.content.startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
