"""Domain package registry, brief and generation-snapshot contracts."""

from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import replace

from fastapi.testclient import TestClient

from cadwork.design.assembly import (
    AssemblyDocument,
    assembly_document_from_json,
    assembly_document_to_json,
)
from cadwork.design.document import (
    Document,
    document_from_json,
    document_to_json,
    new_document,
)
from cadwork.domains.base import (
    BriefSchema,
    DomainError,
    FieldSpec,
    GateSpec,
    NodeKind,
)
from cadwork.domains.registry import DomainRegistry, load_default_registry
from cadwork.service.app import create_app


class _FakePack:
    id = "fake"
    version = "1.0.0"

    def brief_schema(self) -> BriefSchema:
        return BriefSchema(
            id="fake-brief",
            title="Fake",
            fields=(FieldSpec("length", "number", required=True, unit="mm"),),
        )

    def node_kinds(self):
        return (NodeKind("fake_box", output="part"),)

    def compile(self, node, context=None):
        return ({"id": node["id"], "type": "k_box"},)

    def validate(self, document, context=None):
        return ()

    def components(self):
        return ()

    def gates(self):
        return (GateSpec("G0", "Fake gate", ("valid",)),)


class DomainRegistryTests(unittest.TestCase):
    def test_register_list_get_and_versions(self) -> None:
        registry = DomainRegistry()
        first = _FakePack()
        second = _FakePack()
        second.version = "2.0.0"
        registry.register(first)
        registry.register(second, active=False)

        self.assertEqual(registry.get("fake"), first)
        self.assertEqual(registry.get("fake", "2.0.0"), second)
        listed = registry.list()
        self.assertEqual(listed[0]["id"], "fake")
        self.assertEqual(listed[0]["active"], True)
        self.assertEqual(listed[0]["versions"], ["1.0.0", "2.0.0"])
        self.assertEqual(registry.brief("fake").id, "fake-brief")

    def test_duplicate_and_unknown_are_explicit(self) -> None:
        registry = DomainRegistry()
        registry.register(_FakePack())
        with self.assertRaises(DomainError) as duplicate:
            registry.register(_FakePack())
        self.assertEqual(duplicate.exception.code, "DOMAIN_ALREADY_REGISTERED")
        with self.assertRaises(DomainError) as missing:
            registry.get("missing")
        self.assertEqual(missing.exception.code, "DOMAIN_NOT_FOUND")
        self.assertEqual(missing.exception.status, 404)

    def test_invalid_ids_are_rejected(self) -> None:
        registry = DomainRegistry()
        bad = _FakePack()
        bad.id = "Bad Id"
        with self.assertRaises(DomainError) as error:
            registry.register(bad)
        self.assertEqual(error.exception.code, "INVALID_DOMAIN_ID")

    def test_environment_selects_shipped_packs(self) -> None:
        previous = os.environ.get("CADWORK_DOMAIN_PACKS")
        try:
            os.environ["CADWORK_DOMAIN_PACKS"] = ""
            self.assertEqual(len(load_default_registry()), 0)
            os.environ["CADWORK_DOMAIN_PACKS"] = "aircraft"
            registry = load_default_registry()
            self.assertEqual(registry.get("aircraft").id, "aircraft")
        finally:
            if previous is None:
                os.environ.pop("CADWORK_DOMAIN_PACKS", None)
            else:
                os.environ["CADWORK_DOMAIN_PACKS"] = previous


class GenerationSnapshotTests(unittest.TestCase):
    def test_part_generation_round_trip(self) -> None:
        document = replace(
            new_document("wing"),
            generation={
                "domain_id": "aircraft",
                "domain_version": "0.1.0",
                "brief": {"span_mm": 8000},
                "assumptions": [{"id": "a1", "text": "root at z=0"}],
            },
        )
        payload = document_to_json(document)
        restored = document_from_json(payload)
        self.assertEqual(restored.generation, document.generation)

    def test_old_document_without_generation_still_loads(self) -> None:
        document = new_document("plain")
        payload = document_to_json(document)
        payload.pop("generation", None)
        restored = document_from_json(payload)
        self.assertEqual(restored.generation, {})

    def test_assembly_generation_round_trip(self) -> None:
        assembly = AssemblyDocument(
            id="a_test",
            name="test",
            version=1,
            instances=(),
            generation={
                "domain_id": "aircraft",
                "domain_version": "0.1.0",
                "gates": [{"id": "W1", "status": "approved"}],
            },
        )
        payload = assembly_document_to_json(assembly)
        restored = assembly_document_from_json(payload)
        self.assertEqual(restored.generation, assembly.generation)


class DomainApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.app = create_app(self.folder.name)
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)

    def test_list_and_brief(self) -> None:
        response = self.client.get("/api/domains")
        self.assertEqual(response.status_code, 200)
        domains = response.json()["domains"]
        self.assertEqual(domains[0]["id"], "aircraft")
        self.assertEqual(domains[0]["version"], "0.1.0")
        self.assertIn("W1", [gate["id"] for gate in domains[0]["gates"]])

        brief = self.client.get("/api/domains/aircraft/brief")
        self.assertEqual(brief.status_code, 200)
        self.assertEqual(brief.json()["brief"]["id"], "aircraft-wing")

    def test_unknown_domain_is_not_found(self) -> None:
        response = self.client.get("/api/domains/missing/brief")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "DOMAIN_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
