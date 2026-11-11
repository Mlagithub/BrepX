"""Version history navigation and milestone recording."""

from __future__ import annotations

import tempfile
import unittest

from cadwork.design.document import DocumentError, FocusParam, apply_ops, new_document
from cadwork.design.history import HistoryStack
from cadwork.service.store import Store, StoreError


class HistoryStackTests(unittest.TestCase):
    def test_milestones_and_focus_params_recorded_on_apply(self) -> None:
        doc = new_document("Part", "d_hist")
        self.assertEqual(doc.version, 0)
        doc2 = apply_ops(
            doc,
            [{"op": "add", "feature": {"id": "b1", "type": "solid_box", "params": {"length": 40.0}}}],
            milestone_title="Create base box",
            focus_params=[FocusParam("b1", "length", "Box Length", "mm")],
        )
        self.assertEqual(doc2.version, 1)
        self.assertEqual(len(doc2.milestones), 2)
        self.assertEqual(doc2.milestones[0].version, 0)
        ms = doc2.milestones[-1]
        self.assertEqual(ms.version, 1)
        self.assertEqual(ms.parent_version, 0)
        self.assertEqual(ms.title, "Create base box")
        self.assertEqual(ms.changed_features, ("b1",))
        self.assertEqual(ms.focus_params[0].param, "length")
        self.assertGreater(ms.created, 0)

    def test_history_stack_jump_and_revert(self) -> None:
        stack = HistoryStack()
        v0 = new_document("Part", "d_jump")
        stack.push(v0)
        v1 = apply_ops(v0, [{"op": "add", "feature": {"id": "f1", "type": "solid_box"}}])
        stack.push(v1)
        v2 = apply_ops(v1, [{"op": "update", "id": "f1", "params": {"length": 100.0}}])

        self.assertEqual(stack.list_versions(), [0, 1])
        fetched = stack.get_version(0)
        self.assertEqual(fetched.version, 0)
        self.assertEqual(len(fetched.features), 0)

        reverted = stack.revert_to(v2, 1)
        self.assertEqual(reverted.version, 1)
        self.assertEqual(stack.list_versions(), [0])

        with self.assertRaises(DocumentError):
            stack.get_version(99)

    def test_store_get_version_and_revert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            doc = store.create("Test")
            self.assertEqual(doc.version, 0)
            v1 = apply_ops(doc, [{"op": "add", "feature": {"id": "f1", "type": "solid_box"}}])
            store.save(v1)
            v2 = apply_ops(v1, [{"op": "update", "id": "f1", "params": {"length": 120.0}}])
            store.save(v2)

            self.assertEqual(store.get_version(doc.id, 0).version, 0)
            self.assertEqual(store.get_version(doc.id, 1).version, 1)
            self.assertEqual(store.get_version(doc.id, 2).version, 2)

            reverted = store.revert(doc.id, 1)
            self.assertEqual(reverted.version, 1)
            self.assertEqual(store.get(doc.id).version, 1)

            with self.assertRaises(StoreError):
                store.get_version(doc.id, 2)


if __name__ == "__main__":
    unittest.main()
