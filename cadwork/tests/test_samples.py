"""The sample registry: three part families, one generic step engine."""

from __future__ import annotations

import tempfile
import unittest

from fastapi.testclient import TestClient

from cadwork.design import build as build_document
from cadwork.samples.registry import SAMPLES, build as make_sample, catalog
from cadwork.service import create_app


class SampleRegistryTests(unittest.TestCase):
    def test_three_families_build_from_generic_steps(self) -> None:
        self.assertEqual([entry["name"] for entry in catalog()],
                         ["impeller", "volute", "blade", "flange"])
        for name in SAMPLES:
            result = build_document(make_sample(name))
            final = result.final
            self.assertTrue(final.is_valid(), name)
            self.assertTrue(final.mesh().is_closed(), name)
            self.assertGreater(float(final.volume), 0.0, name)

    def test_parameters_are_checked(self) -> None:
        with self.assertRaises(ValueError):
            make_sample("impeller", {"count": 999})
        with self.assertRaises(ValueError):
            make_sample("impeller", {"no_such_param": 1})
        with self.assertRaises(KeyError):
            make_sample("no_such_sample")

    def test_parameter_changes_the_build(self) -> None:
        nine = build_document(make_sample("impeller", {"count": 9}))
        eleven = build_document(make_sample("impeller", {"count": 11}))
        self.assertNotEqual(len(nine.final.faces()), len(eleven.final.faces()))


class SampleRouteTests(unittest.TestCase):
    def test_load_sample_replaces_the_document(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with TestClient(create_app(folder)) as client:
                document = client.post("/api/docs", json={"name": "Impeller"}).json()
                first = client.post(
                    f"/api/docs/{document['id']}/sample/impeller",
                    json={"params": {"count": 9}},
                )
                self.assertEqual(first.status_code, 200, first.text[:300])
                self.assertEqual(len(first.json()["document"]["features"]), 9)

                second = client.post(
                    f"/api/docs/{document['id']}/sample/volute",
                    json={"params": {"turns": 1.25, "r_end": 70, "wall": 1.0}},
                )
                self.assertEqual(second.status_code, 200, second.text[:300])
                self.assertEqual(len(second.json()["document"]["features"]), 4)
                self.assertEqual(second.json()["document"]["version"], 3)
                # The name is what lets the client label the picker.
                self.assertEqual(second.json()["document"]["name"], "Volute casing")

                scene = client.get(f"/api/docs/{document['id']}/scene").json()
                self.assertTrue(scene["faces"])

    def test_bad_sample_parameters_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with TestClient(create_app(folder)) as client:
                document = client.post("/api/docs", json={"name": "x"}).json()
                response = client.post(
                    f"/api/docs/{document['id']}/sample/blade",
                    json={"params": {"thickness": 99}},
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "INVALID_PARAM")


if __name__ == "__main__":
    unittest.main()
