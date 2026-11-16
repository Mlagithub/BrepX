"""Tests for the assembly model: version pins, placements, and JSON round trips."""

from __future__ import annotations

import json
import unittest

from cadwork.design.assembly import (
    AssemblyDocument,
    AssemblyRef,
    Instance,
    Mate,
    PartRef,
    Transform,
    assembly_document_from_json,
    assembly_document_from_json_text,
    assembly_document_to_json,
    assembly_document_to_json_text,
    assembly_ref_from_json,
    assembly_ref_to_json,
    instance_from_json,
    instance_to_json,
    mate_from_json,
    mate_to_json,
    new_assembly_document,
    part_ref_from_json,
    part_ref_to_json,
    reference_from_json,
    reference_to_json,
    transform_from_json,
    transform_to_json,
)
from cadwork.design.document import DocumentError


def _instance(instance_id: str = "i_shaft", **changes: object) -> Instance:
    fields: dict[str, object] = {
        "id": instance_id,
        "ref": PartRef("d_shaft", 3),
        "placement": Transform(),
    }
    fields.update(changes)
    return Instance(**fields)


def _assembly(**changes: object) -> AssemblyDocument:
    fields: dict[str, object] = {
        "id": "a_drive",
        "name": "Drive",
        "version": 1,
        "instances": (),
    }
    fields.update(changes)
    return AssemblyDocument(**fields)


class PartRefTests(unittest.TestCase):
    def test_configuration_defaults_to_default(self) -> None:
        self.assertEqual(PartRef("d_shaft", 3).configuration, "default")

    def test_json_round_trip(self) -> None:
        ref = PartRef("d_shaft", 3, "oversize")
        payload = part_ref_to_json(ref)
        self.assertEqual(payload["kind"], "part")
        self.assertEqual(part_ref_from_json(payload), ref)

    def test_version_must_be_at_least_one(self) -> None:
        for version in (0, -2):
            with self.assertRaises(DocumentError) as caught:
                PartRef("d_shaft", version)
            self.assertEqual(caught.exception.code, "INVALID_VERSION")

    def test_version_must_be_an_integer(self) -> None:
        for version in ("3", 2.5, True):
            with self.assertRaises(DocumentError) as caught:
                PartRef("d_shaft", version)
            self.assertEqual(caught.exception.code, "INVALID_VERSION")

    def test_document_id_must_be_a_name(self) -> None:
        for document_id in ("", " d_shaft", 7, None):
            with self.assertRaises(DocumentError) as caught:
                PartRef(document_id, 1)
            self.assertEqual(caught.exception.code, "INVALID_ID")

    def test_configuration_must_be_a_name(self) -> None:
        for configuration in ("", " oversize", {"name": "oversize"}, 7, None):
            with self.assertRaises(DocumentError) as caught:
                PartRef("d_shaft", 3, configuration)
            self.assertEqual(caught.exception.code, "INVALID_CONFIGURATION")

    def test_json_rejects_unknown_configuration_shape(self) -> None:
        payload = {
            "kind": "part",
            "document_id": "d_shaft",
            "version": 3,
            "configuration": {"name": "oversize"},
        }
        with self.assertRaises(DocumentError) as caught:
            part_ref_from_json(payload)
        self.assertEqual(caught.exception.code, "INVALID_CONFIGURATION")

    def test_json_rejects_unknown_field(self) -> None:
        payload = {
            "kind": "part",
            "document_id": "d_shaft",
            "version": 3,
            "configuration": "default",
            "color": "red",
        }
        with self.assertRaises(DocumentError) as caught:
            part_ref_from_json(payload)
        self.assertEqual(caught.exception.code, "UNKNOWN_FIELD")

    def test_json_requires_document_id(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            part_ref_from_json({"kind": "part", "version": 3})
        self.assertEqual(caught.exception.code, "MISSING_FIELD")

    def test_json_rejects_wrong_reference_kind(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            part_ref_from_json(
                {"kind": "assembly", "document_id": "d_shaft", "version": 3}
            )
        self.assertEqual(caught.exception.code, "INVALID_REF")


class AssemblyReferenceTests(unittest.TestCase):
    def test_json_round_trip(self) -> None:
        ref = AssemblyRef("a_gearbox", 2)
        payload = assembly_ref_to_json(ref)
        self.assertEqual(payload["kind"], "assembly")
        self.assertEqual(assembly_ref_from_json(payload), ref)

    def test_version_must_be_at_least_one(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            AssemblyRef("a_gearbox", 0)
        self.assertEqual(caught.exception.code, "INVALID_VERSION")

    def test_document_id_must_be_a_name(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            AssemblyRef("", 1)
        self.assertEqual(caught.exception.code, "INVALID_ID")

    def test_reference_round_trip_keeps_type(self) -> None:
        references = (PartRef("d_shaft", 1, "narrow"), AssemblyRef("a_gearbox", 2))
        for ref in references:
            self.assertEqual(reference_from_json(reference_to_json(ref)), ref)

    def test_reference_dispatches_on_kind(self) -> None:
        part = reference_from_json(
            {"kind": "part", "document_id": "d_shaft", "version": 1}
        )
        self.assertEqual(part, PartRef("d_shaft", 1))
        assembly = reference_from_json(
            {"kind": "assembly", "document_id": "a_gearbox", "version": 1}
        )
        self.assertEqual(assembly, AssemblyRef("a_gearbox", 1))

    def test_reference_rejects_unknown_kind(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            reference_from_json(
                {"kind": "sheet", "document_id": "d_shaft", "version": 1}
            )
        self.assertEqual(caught.exception.code, "INVALID_REF")

    def test_reference_rejects_non_reference_value(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            reference_to_json("d_shaft")
        self.assertEqual(caught.exception.code, "INVALID_REF")


class TransformTests(unittest.TestCase):
    def test_identity_by_default(self) -> None:
        transform = Transform()
        self.assertEqual(
            transform.rotation,
            ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        )
        self.assertEqual(transform.translation, (0.0, 0.0, 0.0))

    def test_json_round_trip(self) -> None:
        transform = Transform(
            rotation=((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
            translation=(10.0, -2.5, 4.0),
        )
        payload = transform_to_json(transform)
        self.assertEqual(payload["rotation"][0], [0.0, -1.0, 0.0])
        self.assertEqual(transform_from_json(payload), transform)

    def test_json_defaults_to_identity(self) -> None:
        self.assertEqual(transform_from_json({}), Transform())

    def test_rotation_must_be_three_by_three(self) -> None:
        rotations = (
            ((1.0, 0.0), (0.0, 1.0)),
            ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            "identity",
        )
        for rotation in rotations:
            with self.assertRaises(DocumentError) as caught:
                Transform(rotation=rotation)
            self.assertEqual(caught.exception.code, "INVALID_PLACEMENT")

    def test_numbers_must_be_finite(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            Transform(translation=(0.0, float("inf"), 0.0))
        self.assertEqual(caught.exception.code, "INVALID_PLACEMENT")
        rotation = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, float("nan")))
        with self.assertRaises(DocumentError) as caught:
            Transform(rotation=rotation)
        self.assertEqual(caught.exception.code, "INVALID_PLACEMENT")

    def test_json_rejects_unknown_field(self) -> None:
        payload = {
            "rotation": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            "translation": [0.0, 0.0, 0.0],
            "scale": 2.0,
        }
        with self.assertRaises(DocumentError) as caught:
            transform_from_json(payload)
        self.assertEqual(caught.exception.code, "UNKNOWN_FIELD")


class InstanceTests(unittest.TestCase):
    def test_json_round_trip(self) -> None:
        instance = Instance(
            id="i_bearing",
            ref=PartRef("d_bearing", 2, "sealed"),
            placement=Transform(translation=(1.0, 2.0, 3.0)),
            overrides={"width": 12.0, "chamfer": [0.5, 0.5]},
            name="Front bearing",
            suppressed=False,
            visible=True,
        )
        self.assertEqual(instance_from_json(instance_to_json(instance)), instance)

    def test_json_requires_placement(self) -> None:
        payload = instance_to_json(_instance())
        payload.pop("placement")
        with self.assertRaises(DocumentError) as caught:
            instance_from_json(payload)
        self.assertEqual(caught.exception.code, "MISSING_FIELD")

    def test_ref_must_be_a_reference(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            Instance(id="i_shaft", ref="d_shaft", placement=Transform())
        self.assertEqual(caught.exception.code, "INVALID_REF")

    def test_overrides_must_hold_parameter_values(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            Instance(
                id="i_shaft",
                ref=PartRef("d_shaft", 1),
                placement=Transform(),
                overrides={"profile": {"kind": "box"}},
            )
        self.assertEqual(caught.exception.code, "INVALID_VALUE")

    def test_overrides_must_be_an_object(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            Instance(
                id="i_shaft",
                ref=PartRef("d_shaft", 1),
                placement=Transform(),
                overrides=[("width", 1.0)],
            )
        self.assertEqual(caught.exception.code, "INVALID_FIELD")

    def test_flags_must_be_booleans(self) -> None:
        for field_name in ("suppressed", "visible"):
            with self.assertRaises(DocumentError) as caught:
                Instance(
                    id="i_shaft",
                    ref=PartRef("d_shaft", 1),
                    placement=Transform(),
                    **{field_name: 1},
                )
            self.assertEqual(caught.exception.code, "INVALID_FIELD")

    def test_json_rejects_unknown_field(self) -> None:
        payload = instance_to_json(_instance())
        payload["color"] = "red"
        with self.assertRaises(DocumentError) as caught:
            instance_from_json(payload)
        self.assertEqual(caught.exception.code, "UNKNOWN_FIELD")


class MateTests(unittest.TestCase):
    def test_json_round_trip(self) -> None:
        mate = Mate(
            id="m_seat",
            a_instance="i_shaft",
            b_instance="i_housing",
            kind="coincident",
            params={"gap": 0.0},
        )
        self.assertEqual(mate_from_json(mate_to_json(mate)), mate)

    def test_mate_cannot_join_an_instance_to_itself(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            Mate(id="m1", a_instance="i_shaft", b_instance="i_shaft", kind="coincident")
        self.assertEqual(caught.exception.code, "INVALID_MATE")

    def test_kind_must_be_a_name(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            Mate(id="m1", a_instance="i_a", b_instance="i_b", kind="")
        self.assertEqual(caught.exception.code, "INVALID_MATE")

    def test_params_must_hold_parameter_values(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            Mate(
                id="m1",
                a_instance="i_a",
                b_instance="i_b",
                kind="coincident",
                params={"axis": {"x": 1.0}},
            )
        self.assertEqual(caught.exception.code, "INVALID_VALUE")

    def test_json_rejects_unknown_field(self) -> None:
        payload = mate_to_json(
            Mate(id="m1", a_instance="i_a", b_instance="i_b", kind="coincident")
        )
        payload["axis"] = "z"
        with self.assertRaises(DocumentError) as caught:
            mate_from_json(payload)
        self.assertEqual(caught.exception.code, "UNKNOWN_FIELD")


class AssemblyDocumentTests(unittest.TestCase):
    def _document(self) -> AssemblyDocument:
        return AssemblyDocument(
            id="a_drive",
            name="Drive",
            version=1,
            instances=(
                Instance(
                    id="i_shaft", ref=PartRef("d_shaft", 3), placement=Transform()
                ),
                Instance(
                    id="i_housing",
                    ref=PartRef("d_housing", 1, "narrow"),
                    placement=Transform(translation=(50.0, 0.0, 0.0)),
                ),
                Instance(
                    id="i_gearbox",
                    ref=AssemblyRef("a_gearbox", 4),
                    placement=Transform(translation=(0.0, 0.0, 20.0)),
                ),
            ),
            mates=(
                Mate(
                    id="m_seat",
                    a_instance="i_shaft",
                    b_instance="i_housing",
                    kind="coincident",
                    params={"gap": 0.0},
                ),
            ),
            seq=7,
        )

    def test_json_round_trip(self) -> None:
        document = self._document()
        self.assertEqual(
            assembly_document_from_json(assembly_document_to_json(document)), document
        )
        text = assembly_document_to_json_text(document)
        self.assertEqual(assembly_document_from_json_text(text), document)

    def test_json_round_trip_is_canonical(self) -> None:
        document = self._document()
        text = assembly_document_to_json_text(document)
        self.assertEqual(json.loads(text), assembly_document_to_json(document))
        self.assertNotIn(": ", text)
        self.assertNotIn(", ", text)
        self.assertEqual(
            assembly_document_to_json_text(assembly_document_from_json_text(text)),
            text,
        )

    def test_version_must_be_at_least_one(self) -> None:
        for version in (0, -1):
            with self.assertRaises(DocumentError) as caught:
                AssemblyDocument(
                    id="a_drive", name="Drive", version=version, instances=()
                )
            self.assertEqual(caught.exception.code, "INVALID_VERSION")

    def test_document_id_must_be_a_name(self) -> None:
        for document_id in ("", " a_drive", 9, None):
            with self.assertRaises(DocumentError) as caught:
                AssemblyDocument(id=document_id, name="Drive", version=1, instances=())
            self.assertEqual(caught.exception.code, "INVALID_ID")

    def test_name_must_be_a_string(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            AssemblyDocument(id="a_drive", name=5, version=1, instances=())
        self.assertEqual(caught.exception.code, "INVALID_FIELD")

    def test_sequence_must_be_a_nonnegative_integer(self) -> None:
        for seq in (-1, "0", 1.5, True):
            with self.assertRaises(DocumentError) as caught:
                _assembly(seq=seq)
            self.assertEqual(caught.exception.code, "INVALID_FIELD")

    def test_instances_are_stored_as_a_tuple(self) -> None:
        document = _assembly(instances=[_instance()])
        self.assertIsInstance(document.instances, tuple)

    def test_instances_must_hold_instances(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            _assembly(instances=("i_shaft",))
        self.assertEqual(caught.exception.code, "INVALID_FIELD")

    def test_duplicate_instance_id_is_rejected(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            _assembly(instances=(_instance(), _instance()))
        self.assertEqual(caught.exception.code, "DUPLICATE_ID")

    def test_duplicate_instance_id_in_json_is_rejected(self) -> None:
        payload = assembly_document_to_json(_assembly(instances=(_instance(),)))
        payload["instances"].append(instance_to_json(_instance()))
        with self.assertRaises(DocumentError) as caught:
            assembly_document_from_json(payload)
        self.assertEqual(caught.exception.code, "DUPLICATE_ID")

    def test_assembly_cannot_contain_itself(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            _assembly(
                instances=(
                    Instance(
                        id="i_self",
                        ref=AssemblyRef("a_drive", 1),
                        placement=Transform(),
                    ),
                )
            )
        self.assertEqual(caught.exception.code, "SELF_REFERENCE")

    def test_assembly_cannot_pin_a_part_with_its_own_id(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            _assembly(
                instances=(
                    Instance(
                        id="i_self", ref=PartRef("a_drive", 1), placement=Transform()
                    ),
                )
            )
        self.assertEqual(caught.exception.code, "SELF_REFERENCE")

    def test_self_reference_in_json_is_rejected(self) -> None:
        payload = assembly_document_to_json(_assembly(instances=(_instance(),)))
        payload["instances"][0]["ref"] = {
            "kind": "assembly",
            "document_id": "a_drive",
            "version": 1,
        }
        with self.assertRaises(DocumentError) as caught:
            assembly_document_from_json(payload)
        self.assertEqual(caught.exception.code, "SELF_REFERENCE")

    def test_mate_endpoints_must_exist(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            _assembly(
                instances=(_instance(),),
                mates=(
                    Mate(
                        id="m1",
                        a_instance="i_shaft",
                        b_instance="i_missing",
                        kind="coincident",
                    ),
                ),
            )
        self.assertEqual(caught.exception.code, "UNKNOWN_INSTANCE")

    def test_duplicate_mate_id_is_rejected(self) -> None:
        mate = Mate(
            id="m1", a_instance="i_shaft", b_instance="i_housing", kind="coincident"
        )
        with self.assertRaises(DocumentError) as caught:
            _assembly(
                instances=(
                    _instance(),
                    _instance("i_housing", ref=PartRef("d_housing", 1)),
                ),
                mates=(mate, mate),
            )
        self.assertEqual(caught.exception.code, "DUPLICATE_ID")


class AssemblyJsonValidationTests(unittest.TestCase):
    def test_unknown_document_field_is_rejected(self) -> None:
        payload = assembly_document_to_json(_assembly())
        payload["revision"] = 2
        with self.assertRaises(DocumentError) as caught:
            assembly_document_from_json(payload)
        self.assertEqual(caught.exception.code, "UNKNOWN_FIELD")

    def test_unknown_nested_field_is_rejected(self) -> None:
        payload = assembly_document_to_json(_assembly(instances=(_instance(),)))
        payload["instances"][0]["placement"]["scale"] = 1.0
        with self.assertRaises(DocumentError) as caught:
            assembly_document_from_json(payload)
        self.assertEqual(caught.exception.code, "UNKNOWN_FIELD")

    def test_missing_instances_is_rejected(self) -> None:
        payload = assembly_document_to_json(_assembly())
        payload.pop("instances")
        with self.assertRaises(DocumentError) as caught:
            assembly_document_from_json(payload)
        self.assertEqual(caught.exception.code, "MISSING_FIELD")

    def test_missing_version_is_rejected(self) -> None:
        payload = assembly_document_to_json(_assembly())
        payload.pop("version")
        with self.assertRaises(DocumentError) as caught:
            assembly_document_from_json(payload)
        self.assertEqual(caught.exception.code, "MISSING_FIELD")

    def test_version_must_be_an_integer_in_json(self) -> None:
        payload = assembly_document_to_json(_assembly())
        payload["version"] = "1"
        with self.assertRaises(DocumentError) as caught:
            assembly_document_from_json(payload)
        self.assertEqual(caught.exception.code, "INVALID_VERSION")

    def test_instances_must_be_an_array(self) -> None:
        payload = assembly_document_to_json(_assembly())
        payload["instances"] = {"id": "i_shaft"}
        with self.assertRaises(DocumentError) as caught:
            assembly_document_from_json(payload)
        self.assertEqual(caught.exception.code, "INVALID_JSON")

    def test_mates_must_be_an_array(self) -> None:
        payload = assembly_document_to_json(_assembly())
        payload["mates"] = "m_seat"
        with self.assertRaises(DocumentError) as caught:
            assembly_document_from_json(payload)
        self.assertEqual(caught.exception.code, "INVALID_JSON")

    def test_payload_must_be_an_object(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            assembly_document_from_json([])
        self.assertEqual(caught.exception.code, "INVALID_JSON")

    def test_duplicate_json_field_is_rejected(self) -> None:
        text = '{"id":"a_drive","name":"Drive","version":1,"instances":[],"version":2}'
        with self.assertRaises(DocumentError) as caught:
            assembly_document_from_json_text(text)
        self.assertEqual(caught.exception.code, "DUPLICATE_FIELD")

    def test_nested_duplicate_json_field_is_rejected(self) -> None:
        text = '{"id":"a_drive","name":"Drive","version":1,"instances":[{"id":"i","id":"j"}]}'
        with self.assertRaises(DocumentError) as caught:
            assembly_document_from_json_text(text)
        self.assertEqual(caught.exception.code, "DUPLICATE_FIELD")

    def test_invalid_json_text_is_rejected(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            assembly_document_from_json_text("{")
        self.assertEqual(caught.exception.code, "INVALID_JSON")

    def test_non_text_payload_is_rejected(self) -> None:
        with self.assertRaises(DocumentError) as caught:
            assembly_document_from_json_text({"id": "a_drive"})
        self.assertEqual(caught.exception.code, "INVALID_JSON")


class NewAssemblyDocumentTests(unittest.TestCase):
    def test_new_document_is_version_one_and_empty(self) -> None:
        document = new_assembly_document("Drive")
        self.assertEqual(document.version, 1)
        self.assertEqual(document.instances, ())
        self.assertEqual(document.mates, ())
        self.assertEqual(document.name, "Drive")
        self.assertTrue(document.id.startswith("a_"))

    def test_new_document_accepts_an_explicit_id(self) -> None:
        document = new_assembly_document("Drive", document_id="a_drive")
        self.assertEqual(document.id, "a_drive")


if __name__ == "__main__":
    unittest.main()
