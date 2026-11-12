"""The sample registry: four part families, one generic action engine."""

from __future__ import annotations

import tempfile
import unittest

from fastapi.testclient import TestClient

from cadwork import smlib as S
from cadwork.design import build as build_document
from cadwork.samples.registry import SAMPLES, build as make_sample, catalog
from cadwork.service import create_app

EXPECTED = {
    # name: (features, checks, final volume)
    "impeller": (36, 55, 152725.69),
    "blade": (32, 38, 1627.83),
    "flange": (12, 40, 161388.72),
    "volute": (4, 10, 13458.29),
}


class SampleRegistryTests(unittest.TestCase):
    def test_four_families_build_from_generic_actions(self) -> None:
        self.assertEqual([entry["name"] for entry in catalog()],
                         ["impeller", "volute", "blade", "flange"])
        for name in SAMPLES:
            document = make_sample(name)
            result = build_document(document)
            features, checks, volume = EXPECTED[name]
            self.assertEqual(len(document.features), features, name)
            self.assertEqual(len(result.features), features, name)
            total_checks = sum(len(item.checks) for item in result.features)
            self.assertEqual(total_checks, checks, name)
            self.assertTrue(all(check.ok for item in result.features for check in item.checks),
                            name)
            final = result.final
            self.assertIsInstance(final, S.Part, name)
            self.assertTrue(final.is_valid(), name)
            self.assertTrue(final.mesh().is_closed(), name)
            self.assertAlmostEqual(float(final.volume), volume, delta=volume * 0.001, msg=name)
            self.assertGreater(len(final.faces()), 0, name)

    def test_catalog_shape(self) -> None:
        entries = catalog()
        self.assertEqual(len(entries), 4)
        for entry in entries:
            self.assertEqual(set(entry), {"name", "title", "summary", "params"})
            self.assertTrue(entry["title"])
            for param in entry["params"]:
                self.assertEqual(set(param), {"name", "default", "min", "max",
                                              "kind", "unit", "description"})
                self.assertIn(param["kind"], {"float", "int"})
        impeller = next(entry for entry in entries if entry["name"] == "impeller")
        count = next(param for param in impeller["params"] if param["name"] == "count")
        self.assertEqual(count["default"], 9)
        self.assertEqual(count["min"], 5)
        self.assertEqual(count["max"], 24)
        self.assertEqual(count["kind"], "int")

    def test_parameters_are_checked(self) -> None:
        with self.assertRaises(ValueError):
            make_sample("impeller", {"count": 999})
        with self.assertRaises(ValueError):
            make_sample("impeller", {"count": 4})
        with self.assertRaises(ValueError):
            make_sample("impeller", {"no_such_param": 1})
        with self.assertRaises(ValueError):
            make_sample("blade", {"thickness": "thick"})
        with self.assertRaises(KeyError):
            make_sample("no_such_sample")

    def test_parameter_changes_the_build(self) -> None:
        nine = build_document(make_sample("impeller", {"count": 9}))
        eleven = build_document(make_sample("impeller", {"count": 11}))
        self.assertNotEqual(len(nine.final.faces()), len(eleven.final.faces()))
        self.assertNotEqual(round(float(nine.final.volume), 2),
                            round(float(eleven.final.volume), 2))


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
                self.assertEqual(len(first.json()["document"]["features"]), 36)

                second = client.post(
                    f"/api/docs/{document['id']}/sample/volute",
                    json={"params": {"turns": 1.25, "r_end": 70, "wall": 1.0}},
                )
                self.assertEqual(second.status_code, 200, second.text[:300])
                self.assertEqual(len(second.json()["document"]["features"]), 4)
                self.assertEqual(second.json()["document"]["version"], 2)
                # The name is what lets the client label the picker.
                self.assertEqual(second.json()["document"]["name"], "Volute casing")
                self.assertAlmostEqual(second.json()["milestone"]["metrics"]["volume"],
                                       13458.29, delta=15.0)

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
