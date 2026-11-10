"""Variant sets: build several parameter values without touching the document."""

from __future__ import annotations

import tempfile
import unittest

from fastapi.testclient import TestClient

from cadwork.service import create_app


class VariantTests(unittest.TestCase):
    def setUp(self) -> None:
        self._folder = tempfile.TemporaryDirectory()
        self.client = TestClient(create_app(self._folder.name))
        self.client.__enter__()
        document = self.client.post("/api/docs", json={"name": "Flange"}).json()
        self.doc_id = document["id"]
        built = self.client.post(f"/api/docs/{self.doc_id}/sample/flange",
                                 json={"params": {}}).json()
        self.version = built["document"]["version"]

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self._folder.cleanup()

    def _variants(self, params: dict, feature: str = "p9") -> dict:
        response = self.client.post(
            f"/api/docs/{self.doc_id}/variants",
            json={"feature": feature, "params": params},
        )
        self.assertEqual(response.status_code, 200, response.text[:300])
        return response.json()

    def test_variants_build_side_by_side(self) -> None:
        payload = self._variants({"length": [0.6, 1.5, 2.5]})
        variants = payload["variants"]
        self.assertEqual(len(variants), 3)
        self.assertEqual([item["values"]["length"] for item in variants],
                         [0.6, 1.5, 2.5])
        volumes = [item["volume"] for item in variants]
        self.assertEqual(volumes, sorted(volumes, reverse=True))  # bigger bevel, less metal
        for item in variants:
            self.assertTrue(item["ok"])
            self.assertGreater(item["faces"], 0)
            self.assertTrue(item["thumb"].startswith("/api/variants/"))

    def test_variants_do_not_touch_the_document(self) -> None:
        self._variants({"length": [0.6, 2.5]})
        document = self.client.get(f"/api/docs/{self.doc_id}").json()
        self.assertEqual(document["version"], self.version)
        chamfer = next(item for item in document["features"] if item["id"] == "p9")
        self.assertEqual(chamfer["params"]["length"], 1.5)

    def test_thumbnail_is_served(self) -> None:
        payload = self._variants({"length": [1.0]})
        url = payload["variants"][0]["thumb"]
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertGreater(len(response.content), 1000)

    def test_apply_writes_the_variant(self) -> None:
        payload = self._variants({"length": [2.5]})
        applied = self.client.post(
            f"/api/variants/{payload['set']}/0/apply").json()
        self.assertEqual(applied["document"]["version"], self.version + 1)
        chamfer = next(item for item in applied["document"]["features"] if item["id"] == "p9")
        self.assertEqual(chamfer["params"]["length"], 2.5)

    def test_sheet_composes_every_variant(self) -> None:
        payload = self._variants({"length": [0.8, 1.5, 2.5]})
        response = self.client.get(f"/api/variants/{payload['set']}/sheet.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content[:8], b"\x89PNG\r\n\x1a\n")
        self.assertGreater(len(response.content), 20000)
        from PIL import Image
        import io

        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.width > image.height, True)  # a strip, not a page
        self.assertGreater(image.width, 3 * 400)

    def test_any_document_delta_is_a_variant(self) -> None:
        payload = self.client.post(
            f"/api/docs/{self.doc_id}/variants",
            json={"variants": [
                {"label": "无倒角", "ops": [{"op": "update", "id": "p9", "enabled": False}]},
                {"label": "倒角 3", "ops": [{"op": "update", "id": "p9",
                                              "params": {"length": 3.0}}]},
            ]},
        ).json()
        self.assertEqual([item["label"] for item in payload["variants"]],
                         ["无倒角", "倒角 3"])
        self.assertNotIn("feature", payload)  # a set is not tied to one feature
        for item in payload["variants"]:
            self.assertTrue(item["ok"])
            self.assertTrue(item["ops"])
        # switching the chamfer off keeps more metal than a 3 mm bevel
        self.assertGreater(payload["variants"][0]["volume"], payload["variants"][1]["volume"])

    def test_a_label_is_generated_when_missing(self) -> None:
        payload = self.client.post(
            f"/api/docs/{self.doc_id}/variants",
            json={"variants": [{"ops": [{"op": "update", "id": "p9",
                                          "params": {"length": 2.0}}]}]},
        ).json()
        self.assertEqual(payload["variants"][0]["label"], "length 2")

    def test_the_current_document_can_be_one_of_the_cards(self) -> None:
        before = self.client.get(f"/api/docs/{self.doc_id}/scene").json()["metrics"]["volume"]
        payload = self.client.post(
            f"/api/docs/{self.doc_id}/variants",
            json={"include_base": True,
                  "variants": [{"label": "倒角 3", "ops": [{"op": "update", "id": "p9",
                                                            "params": {"length": 3.0}}]}]},
        ).json()
        base = payload["variants"][0]
        self.assertEqual(base["label"], "当前")
        self.assertEqual(base["ops"], [])
        self.assertAlmostEqual(base["volume"], round(float(before), 1), places=1)

    def test_a_broken_delta_is_reported_not_raised(self) -> None:
        response = self.client.post(
            f"/api/docs/{self.doc_id}/variants",
            json={"variants": [{"label": "坏", "ops": [{"op": "update", "id": "nope",
                                                        "params": {"x": 1}}]}]},
        )
        self.assertEqual(response.status_code, 200)
        variant = response.json()["variants"][0]
        self.assertFalse(variant["ok"])
        self.assertTrue(variant["error"]["code"])

    def test_a_variant_can_be_loaded_into_the_viewport(self) -> None:
        payload = self._variants({"length": [0.6, 2.5]})
        url = payload["variants"][1]["step"]
        self.assertTrue(url.endswith("/step"), url)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 2000)

    def test_bad_requests_are_rejected(self) -> None:
        missing = self.client.post(
            f"/api/docs/{self.doc_id}/variants",
            json={"feature": "nope", "params": {"x": [1]}},
        )
        self.assertEqual(missing.status_code, 400)
        unknown = self.client.post(
            f"/api/docs/{self.doc_id}/variants",
            json={"feature": "p9", "params": {"nope": [1]}},
        )
        self.assertEqual(unknown.status_code, 400)
        too_many = self.client.post(
            f"/api/docs/{self.doc_id}/variants",
            json={"feature": "p9", "params": {"length": [0.5, 1.0, 1.5, 2.0, 3.0]}},
        )
        self.assertEqual(too_many.status_code, 400)
        absent = self.client.get("/api/variants/vs_missing")
        self.assertEqual(absent.status_code, 404)


if __name__ == "__main__":
    unittest.main()
