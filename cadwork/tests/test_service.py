"""Integration tests for the HTTP surface and the service layer."""

from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from cadwork.design.document import feature_to_json
from cadwork.design.features import FEATURES
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

    def _build_box(self, client: TestClient, length: float = 20.0) -> tuple[str, dict]:
        document = self._create(client)
        response = client.put(
            f"/api/docs/{document['id']}",
            json={"base_version": 0, "ops": [{
                "op": "add",
                "feature": {"id": "b1", "type": "k_box",
                            "params": {"length": length, "width": 20.0, "height": 20.0}},
            }]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return document["id"], response.json()

    def test_health_and_catalog(self) -> None:
        with self._client() as client:
            self.assertEqual(client.get("/api/health").json()["status"], "ok")
            catalog = client.get("/api/catalog").json()
            self.assertEqual({entry["type"] for entry in catalog}, set(FEATURES))
            self.assertIn("k_box", {entry["type"] for entry in catalog})

    def test_build_impeller_through_the_api(self) -> None:
        with self._client() as client:
            payload = self._build_impeller(client)
            self.assertEqual(payload["document"]["version"], 1)
            self.assertEqual(len(payload["build"]["features"]), 36)
            self.assertEqual(sorted(payload["tags"]), ["t_in", "t_out", "t_wall"])

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
                json={"ops": [{"op": "update", "id": "b_pattern", "params": {"count": 11}}]},
            )
            self.assertEqual(response.status_code, 200, response.text)
            preview = response.json()
            self.assertIn("b_pattern", preview["diff"]["changed"])
            current = client.get(f"/api/docs/{document_id}").json()
            self.assertEqual(current["version"], 1)
            pattern = next(item for item in current["features"] if item["id"] == "b_pattern")
            self.assertEqual(pattern["params"]["count"], 9)

    def test_stale_version_is_rejected(self) -> None:
        with self._client() as client:
            document_id = self._build_impeller(client)["document"]["id"]
            response = client.put(
                f"/api/docs/{document_id}",
                json={"base_version": 0, "ops": []},
            )
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()["error"]["code"], "STALE_VERSION")

    def test_failed_build_leaves_document_unchanged(self) -> None:
        with self._client() as client:
            document_id = self._build_impeller(client)["document"]["id"]
            response = client.put(
                f"/api/docs/{document_id}",
                json={"base_version": 1,
                      "ops": [{"op": "update", "id": "b_fillet",
                               "params": {"radius": 3.0}}]},
            )
            self.assertEqual(response.status_code, 422, response.text)
            error = response.json()["error"]
            self.assertEqual(error["feature_id"], "b_fillet")
            self.assertEqual(error["blocked_downstream"],
                             ["t_in", "t_out", "t_wall", "fluid_cavity"])
            current = client.get(f"/api/docs/{document_id}").json()
            self.assertEqual(current["version"], 1)

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
            self.assertEqual(response.json()["document"]["version"], 2)
            self.assertEqual(response.json()["document"]["features"], [])

    def test_store_survives_app_restart(self) -> None:
        with self._client() as client:
            document_id = self._build_impeller(client)["document"]["id"]
        with TestClient(create_app(self.folder.name)) as second:
            payload = second.get(f"/api/docs/{document_id}").json()
            self.assertEqual(payload["version"], 1)
            self.assertEqual(len(payload["features"]), 36)

    def test_impeller_sample_route(self) -> None:
        with self._client() as client:
            document = self._create(client)
            sample = client.post(f"/api/docs/{document['id']}/sample/impeller")
            self.assertEqual(sample.status_code, 200, sample.text[:200])
            self.assertEqual(len(sample.json()["document"]["features"]), 36)

    def test_delete_document(self) -> None:
        with self._client() as client:
            document = self._create(client)
            self.assertEqual(client.delete(f"/api/docs/{document['id']}").status_code, 200)
            self.assertEqual(client.get(f"/api/docs/{document['id']}").status_code, 404)
            self.assertNotIn(document["id"], [item["id"] for item in client.get("/api/docs").json()])
            self.assertEqual(client.delete(f"/api/docs/{document['id']}").status_code, 404)

    def test_no_standalone_frontend(self) -> None:
        # The workbench is the dsh client plugin; the service is API-only.
        with self._client() as client:
            self.assertEqual(client.get("/web/src/main.js").status_code, 404)
            self.assertEqual(client.get("/api/health").status_code, 200)

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
            box = {"op": "add", "feature": {
                "id": "f1", "type": "k_box",
                "params": {"length": 20.0, "width": 20.0, "height": 20.0},
            }}
            cylinder = {"op": "add", "feature": {
                "id": "f2", "type": "k_cylinder",
                "params": {"radius": 5.0, "height": 10.0},
            }}
            applied = first.put(
                f"/api/docs/{document_id}",
                json={"base_version": 0, "ops": [box]},
            )
            self.assertEqual(applied.status_code, 200)

            stale = second.put(
                f"/api/docs/{document_id}",
                json={"base_version": 0, "ops": [cylinder]},
            )
            self.assertEqual(stale.status_code, 409)
            self.assertEqual(stale.json()["error"]["code"], "STALE_VERSION")

            retried = second.put(
                f"/api/docs/{document_id}",
                json={"base_version": 1, "ops": [cylinder]},
            )
            self.assertEqual(retried.status_code, 200, retried.text)
            self.assertEqual(len(retried.json()["document"]["features"]), 2)

    def test_undo_chain_and_exhaustion(self) -> None:
        with self._client() as client:
            document = self._create(client)
            document_id = document["id"]

            empty_undo = client.post(f"/api/docs/{document_id}/undo")
            self.assertEqual(empty_undo.status_code, 409)
            self.assertEqual(empty_undo.json()["error"]["code"], "NO_HISTORY")

            sequence = [
                {"op": "add", "feature": {
                    "id": "f1", "type": "k_box",
                    "params": {"length": 20.0, "width": 20.0, "height": 20.0},
                }},
                {"op": "add", "feature": {
                    "id": "f2", "type": "k_cylinder",
                    "params": {"radius": 5.0, "height": 10.0},
                }},
                {"op": "add", "feature": {
                    "id": "f3", "type": "pattern",
                    "params": {"kind": "linear", "count": 3, "dx": 30.0},
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
            self.assertEqual(version, 3)

            # Undo writes a new milestone instead of rewriting the chain.
            undone = client.post(f"/api/docs/{document_id}/undo")
            self.assertEqual(undone.status_code, 200)
            self.assertEqual(undone.json()["document"]["version"], 4)
            self.assertEqual(len(undone.json()["document"]["features"]), 2)
            self.assertEqual(undone.json()["document"]["milestones"][-1]["parent_version"], 2)

            reverted = client.post(
                f"/api/docs/{document_id}/revert",
                json={"target_version": 1, "title": "回到单特征"},
            )
            self.assertEqual(reverted.status_code, 200, reverted.text)
            self.assertEqual(reverted.json()["document"]["version"], 5)
            self.assertEqual(len(reverted.json()["document"]["features"]), 1)
            self.assertEqual(reverted.json()["document"]["milestones"][-1]["title"], "回到单特征")

    def test_tweak_writes_focus_metrics(self) -> None:
        with self._client() as client:
            document_id, _ = self._build_box(client)
            response = client.post(
                f"/api/docs/{document_id}/tweak",
                json={"base_version": 1,
                      "changes": [{"feature_id": "b1", "params": {"length": 40.0}}]},
            )
            self.assertEqual(response.status_code, 200, response.text)
            payload = response.json()
            self.assertEqual(payload["document"]["version"], 2)
            self.assertAlmostEqual(payload["milestone"]["metrics"]["volume"], 16000.0, places=2)
            scene = client.get(f"/api/docs/{document_id}/scene").json()
            self.assertAlmostEqual(float(scene["metrics"]["volume"]), 16000.0, places=1)

    def test_render_png(self) -> None:
        with self._client() as client:
            document_id = self._build_impeller(client)["document"]["id"]
            response = client.get(f"/api/docs/{document_id}/render.png")
            self.assertEqual(response.status_code, 200, response.text[:200])
            self.assertTrue(response.content.startswith(b"\x89PNG"))


class PlanServiceTests(unittest.TestCase):
    """The planning surface: plan CRUD, compile, run, timeline and import."""

    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.app = create_app(self.folder.name)

    def _client(self) -> TestClient:
        return TestClient(self.app)

    def _create(self, client: TestClient) -> dict:
        response = client.post("/api/docs", json={"name": "Plan"})
        self.assertEqual(response.status_code, 200)
        return response.json()

    @staticmethod
    def _plan_ops() -> list[dict]:
        return [
            {"op": "add_node", "node": {"id": "g", "kind": "goal",
                                         "title": "make a box"}},
            {"op": "add_node", "node": {
                "id": "n1", "kind": "feature", "title": "box", "action": "k_box",
                "params": {"length": 20.0, "width": 20.0, "height": 20.0},
            }},
            {"op": "add_node", "node": {
                "id": "c1", "kind": "check", "title": "has volume", "deps": ["n1"],
                "expect": [{"metric": "volume", "op": "ge", "value": 1.0}],
            }},
        ]

    def test_plan_crud_and_compile(self) -> None:
        with self._client() as client:
            document = self._create(client)
            document_id = document["id"]

            empty = client.get(f"/api/docs/{document_id}/plan")
            self.assertEqual(empty.status_code, 200)
            self.assertIsNone(empty.json()["plan"])

            edited = client.post(
                f"/api/docs/{document_id}/plan/edit",
                json={"ops": self._plan_ops(), "goal": "make a box"},
            )
            self.assertEqual(edited.status_code, 200, edited.text)
            plan = edited.json()["plan"]
            self.assertEqual(plan["goal"], "make a box")
            self.assertEqual([node["id"] for node in plan["nodes"]], ["g", "n1", "c1"])
            self.assertEqual(plan["base_version"], 0)
            self.assertEqual(plan["revision"], 2)

            fetched = client.get(f"/api/docs/{document_id}/plan").json()["plan"]
            self.assertEqual(fetched["id"], plan["id"])
            self.assertEqual(fetched["revision"], 2)

            compiled = client.post(f"/api/docs/{document_id}/plan/compile")
            self.assertEqual(compiled.status_code, 200, compiled.text)
            report = compiled.json()
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["ops_count"], 1)
            self.assertEqual(report["coverage"]["found"], ["k_box"])
            self.assertEqual(report["program"]["steps"][0]["action"], "k_box")

    def test_plan_run_a_feature_then_a_check(self) -> None:
        with self._client() as client:
            document = self._create(client)
            document_id = document["id"]
            client.post(f"/api/docs/{document_id}/plan/edit",
                        json={"ops": self._plan_ops()})

            ran = client.post(f"/api/docs/{document_id}/plan/run",
                              json={"node_id": "n1"})
            self.assertEqual(ran.status_code, 200, ran.text)
            plan = ran.json()["plan"]
            statuses = {node["id"]: node["status"] for node in plan["nodes"]}
            self.assertEqual(statuses["n1"], "done")
            self.assertEqual(ran.json()["document_version"], 1)
            current = client.get(f"/api/docs/{document_id}").json()
            self.assertEqual([item["id"] for item in current["features"]], ["n1"])
            self.assertEqual(current["version"], 1)

            checked = client.post(f"/api/docs/{document_id}/plan/run",
                                  json={"node_id": "c1", "base_version": 1})
            self.assertEqual(checked.status_code, 200, checked.text)
            nodes = {node["id"]: node for node in checked.json()["plan"]["nodes"]}
            self.assertEqual(nodes["c1"]["status"], "done")
            self.assertIn("volume", nodes["c1"]["observed"])
            # A check node evaluates without writing another milestone.
            self.assertEqual(client.get(f"/api/docs/{document_id}").json()["version"], 1)

    def test_plan_run_refuses_unknown_or_blocked_nodes(self) -> None:
        with self._client() as client:
            document = self._create(client)
            document_id = document["id"]
            client.post(f"/api/docs/{document_id}/plan/edit",
                        json={"ops": self._plan_ops()})
            missing = client.post(f"/api/docs/{document_id}/plan/run",
                                  json={"node_id": "nope"})
            self.assertEqual(missing.status_code, 404)
            self.assertEqual(missing.json()["error"]["code"], "NODE_NOT_FOUND")
            blocked = client.post(f"/api/docs/{document_id}/plan/run",
                                  json={"node_id": "c1"})
            self.assertEqual(blocked.status_code, 409)
            self.assertEqual(blocked.json()["error"]["code"], "NODE_NOT_READY")

    def test_timeline_projects_milestones_and_plan_nodes(self) -> None:
        with self._client() as client:
            document = self._create(client)
            document_id = document["id"]
            client.post(f"/api/docs/{document_id}/plan/edit",
                        json={"ops": self._plan_ops()})
            client.post(f"/api/docs/{document_id}/plan/run", json={"node_id": "n1"})

            response = client.get(f"/api/docs/{document_id}/timeline")
            self.assertEqual(response.status_code, 200)
            entries = response.json()
            self.assertTrue(entries)
            node_ids = {entry.get("node_id") for entry in entries}
            self.assertIn("n1", node_ids)
            self.assertIn("c1", node_ids)
            feature_milestone = next(
                entry for entry in entries
                if entry.get("version") == 1 and entry.get("node_id") == "n1"
                and entry.get("changed")
            )
            self.assertEqual(feature_milestone["changed"], ["n1"])
            self.assertEqual(feature_milestone["features"], [{"id": "n1", "type": "k_box"}])

    def test_import_file_freezes_a_real_step(self) -> None:
        from cadwork.design import build as build_document
        from cadwork.design.document import Document, Feature
        from cadwork.service.export import export_bytes

        part = build_document(Document(id="t", name="t", features=(
            Feature("b1", "k_box",
                    params={"length": 20.0, "width": 20.0, "height": 20.0}),
        ))).final
        step_bytes, _ = export_bytes(part, "step")
        self.assertIn(b"ISO-10303", step_bytes[:200])
        step_path = Path(self.folder.name) / "box.step"
        step_path.write_bytes(step_bytes)

        with self._client() as client:
            document = self._create(client)
            document_id = document["id"]
            response = client.post(
                f"/api/docs/{document_id}/import",
                json={"path": str(step_path), "format": "step"},
            )
            self.assertEqual(response.status_code, 200, response.text)
            imported = response.json()
            self.assertTrue(imported["feature_id"].startswith("import_"))
            self.assertEqual(len(imported["sha256"]), 64)
            self.assertEqual(imported["version"], 1)

            current = client.get(f"/api/docs/{document_id}").json()
            self.assertEqual(len(current["features"]), 1)
            self.assertEqual(current["features"][0]["type"], "import_base")
            state = client.get(f"/api/docs/{document_id}/state").json()
            self.assertFalse(state["vacant"])
            self.assertAlmostEqual(state["metrics"]["volume"], 8000.0, delta=1.0)

    def test_import_file_rejects_missing_files_and_formats(self) -> None:
        with self._client() as client:
            document = self._create(client)
            document_id = document["id"]
            missing = client.post(
                f"/api/docs/{document_id}/import",
                json={"path": str(Path(self.folder.name) / "nope.step")},
            )
            self.assertEqual(missing.status_code, 404)
            self.assertEqual(missing.json()["error"]["code"], "IMPORT_NOT_FOUND")
            bad_format = client.post(
                f"/api/docs/{document_id}/import",
                json={"path": __file__, "format": "dwg"},
            )
            self.assertEqual(bad_format.status_code, 400)
            self.assertEqual(bad_format.json()["error"]["code"], "IMPORT_FORMAT")

    def test_import_upload_accepts_base64_and_rejects_other_formats(self) -> None:
        from cadwork.design import build as build_document
        from cadwork.design.document import Document, Feature
        from cadwork.service.export import export_bytes

        part = build_document(Document(id="t", name="t", features=(
            Feature("b1", "k_box",
                    params={"length": 20.0, "width": 20.0, "height": 20.0}),
        ))).final
        step_bytes, _ = export_bytes(part, "step")
        with self._client() as client:
            document = self._create(client)
            document_id = document["id"]
            uploaded = client.post(
                f"/api/docs/{document_id}/import/file",
                json={"filename": "reference.step",
                      "data": base64.b64encode(step_bytes).decode("ascii")},
            )
            self.assertEqual(uploaded.status_code, 200, uploaded.text)
            payload = uploaded.json()
            self.assertTrue(payload["feature_id"].startswith("import_"))
            self.assertEqual(payload["filename"], "reference.step")
            self.assertEqual(payload["version"], 1)
            state = client.get(f"/api/docs/{document_id}/state").json()
            self.assertAlmostEqual(state["metrics"]["volume"], 8000.0, delta=1.0)

            bad_format = client.post(
                f"/api/docs/{document_id}/import/file",
                json={"filename": "reference.obj", "data": "AA=="},
            )
            self.assertEqual(bad_format.status_code, 400)
            self.assertEqual(bad_format.json()["error"]["code"], "IMPORT_FORMAT")
            bad_data = client.post(
                f"/api/docs/{document_id}/import/file",
                json={"filename": "reference.step", "data": "not-base64!!"},
            )
            self.assertEqual(bad_data.status_code, 400)
            self.assertEqual(bad_data.json()["error"]["code"], "IMPORT_DATA")


if __name__ == "__main__":
    unittest.main()
