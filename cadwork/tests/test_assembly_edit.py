"""Assembly edits are atomic, versioned and mate-safe."""

from __future__ import annotations

import unittest

from cadwork.design.assembly import (
    AssemblyDocument,
    Instance,
    Mate,
    PartRef,
    Transform,
)
from cadwork.design.assembly_edit import (
    add_instance,
    apply_ops,
    override_instance,
    remove_instance,
    replace_instance,
    suppress_instance,
    transform_instance,
    update_pin,
)
from cadwork.design.document import DocumentError


def _assembly(*instances: Instance, mates: tuple[Mate, ...] = ()) -> AssemblyDocument:
    return AssemblyDocument(
        id="assembly_demo",
        name="demo",
        version=1,
        instances=instances,
        mates=mates,
    )


class AssemblyEditTests(unittest.TestCase):
    def _base(self) -> AssemblyDocument:
        return _assembly(
            Instance("blade_a", PartRef("part_blade", 1), Transform()),
            Instance("blade_b", PartRef("part_blade", 1), Transform()),
        )

    def test_add_transform_override_suppress(self) -> None:
        document = self._base()
        document = add_instance(
            document,
            Instance("blade_c", PartRef("part_blade", 1), Transform()),
        )
        self.assertEqual(document.version, 2)
        document = transform_instance(
            document, "blade_c", Transform(translation=(1.0, 2.0, 3.0))
        )
        self.assertEqual(document.version, 3)
        document = override_instance(document, "blade_c", {"length": 12.0})
        self.assertEqual(document.instances[-1].overrides["length"], 12.0)
        document = suppress_instance(document, "blade_c")
        self.assertTrue(document.instances[-1].suppressed)

    def test_remove_refuses_mate_reference(self) -> None:
        document = _assembly(
            Instance("a", PartRef("part_blade", 1), Transform()),
            Instance("b", PartRef("part_blade", 1), Transform()),
            mates=(Mate("m1", "a", "b", "coincident"),),
        )
        with self.assertRaises(DocumentError) as caught:
            remove_instance(document, "a")
        self.assertEqual(caught.exception.code, "MATE_REFERENCES_INSTANCE")
        self.assertEqual(document.version, 1)

    def test_replace_and_update_pin(self) -> None:
        document = self._base()
        document = replace_instance(document, "blade_a", PartRef("part_other", 2))
        self.assertEqual(document.instances[0].ref.document_id, "part_other")
        document = update_pin(document, "blade_b", version=3)
        self.assertEqual(document.instances[1].ref.version, 3)

    def test_stale_expected_version_is_rejected(self) -> None:
        document = self._base()
        with self.assertRaises(DocumentError) as caught:
            transform_instance(document, "blade_a", Transform(), expected_version=99)
        self.assertEqual(caught.exception.code, "STALE_VERSION")

    def test_batch_is_atomic(self) -> None:
        document = self._base()
        with self.assertRaises(DocumentError):
            apply_ops(
                document,
                [
                    {
                        "op": "transform",
                        "id": "blade_a",
                        "placement": {
                            "rotation": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                            "translation": [1, 0, 0],
                        },
                    },
                    {"op": "remove", "id": "missing"},
                ],
            )
        self.assertEqual(document.version, 1)
        self.assertEqual(document.instances[0].placement.translation, (0.0, 0.0, 0.0))

    def test_batch_apply(self) -> None:
        document = apply_ops(
            self._base(),
            [
                {"op": "suppress", "id": "blade_a"},
                {"op": "update_pin", "id": "blade_b", "version": 2},
            ],
        )
        self.assertTrue(document.instances[0].suppressed)
        self.assertEqual(document.instances[1].ref.version, 2)
        self.assertEqual(document.version, 2)


if __name__ == "__main__":
    unittest.main()
