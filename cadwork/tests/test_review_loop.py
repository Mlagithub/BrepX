"""Review loop: progressive state, focus tweaks, milestones, compare and notes."""

from __future__ import annotations

import tempfile
import unittest

from cadwork.service.service import CADService
from cadwork.service.store import Store


def _box_service(length: float = 40.0) -> tuple[CADService, str]:
    service = CADService(Store(tempfile.mkdtemp(prefix="cadwork-review-")))
    document = service.store.create("Box")
    applied = service.commit(
        document.id,
        0,
        [{"op": "add", "feature": {
            "id": "b1", "type": "solid_box",
            "params": {"length": length, "width": 20.0, "height": 10.0},
        }}],
        title="创建方块",
        actor="human",
    )
    return service, applied["document"]["id"]


class ReviewLoopTests(unittest.TestCase):
    def test_state_projects_chain_metrics_and_focus(self) -> None:
        service, document_id = _box_service()
        state = service.state(document_id)
        self.assertFalse(state["vacant"])
        self.assertEqual(state["document"]["version"], 1)
        self.assertEqual([item["version"] for item in state["milestones"]], [0, 1])
        self.assertEqual(state["milestones"][-1]["title"], "创建方块")
        self.assertEqual(state["milestones"][-1]["parent_version"], 0)
        self.assertEqual(state["metrics"]["faces"], 6)
        self.assertAlmostEqual(state["metrics"]["volume"], 8000.0, places=1)
        self.assertTrue(state["checks"]["ok"])
        self.assertGreater(len(state["focus_params"]), 0)
        focus = state["focus_params"][0]
        self.assertIsNotNone(focus["value"])
        self.assertEqual(state["features"][0]["can_toggle"], True)

    def test_tweak_writes_a_milestone_with_focus(self) -> None:
        service, document_id = _box_service()
        result = service.tweak(document_id, [{"feature_id": "b1", "params": {"length": 60.0}}], 1)
        document = service.read(document_id)
        self.assertEqual(document.version, 2)
        self.assertEqual(result["milestone"]["title"], "微调 length=60.0")
        latest = document.milestones[-1]
        self.assertEqual(latest.parent_version, 1)
        self.assertEqual(latest.actor, "human")
        self.assertEqual(latest.focus_params[0].param, "length")
        self.assertEqual(latest.focus_params[0].maximum, 10000.0)
        state = service.state(document_id)
        self.assertAlmostEqual(state["metrics"]["volume"], 12000.0, places=1)
        self.assertEqual(state["focus_params"][0]["value"], 60.0)

    def test_revert_republishes_an_earlier_snapshot(self) -> None:
        service, document_id = _box_service()
        service.tweak(document_id, [{"feature_id": "b1", "params": {"length": 60.0}}], 1)
        reverted = service.revert(document_id, 1, title="回到 v1")
        document = service.read(document_id)
        self.assertEqual(document.version, 3)
        self.assertEqual(document.milestones[-1].parent_version, 1)
        self.assertEqual(document.milestones[-1].title, "回到 v1")
        self.assertEqual(document.features[0].params["length"], 40.0)
        self.assertIsNotNone(reverted["milestone"])

    def test_undo_returns_to_the_previous_geometry(self) -> None:
        service, document_id = _box_service()
        service.tweak(document_id, [{"feature_id": "b1", "params": {"length": 60.0}}], 1)
        undone = service.undo(document_id)
        self.assertEqual(undone["document"]["version"], 3)
        self.assertEqual(undone["document"]["features"][0]["params"]["length"], 40.0)

        empty_service = CADService(Store(tempfile.mkdtemp(prefix="cadwork-review-")))
        empty = empty_service.store.create("Empty")
        with self.assertRaises(Exception) as caught:
            empty_service.undo(empty.id)
        self.assertEqual(getattr(caught.exception, "code", None), "NO_HISTORY")

    def test_compare_reports_changed_faces_between_versions(self) -> None:
        service, document_id = _box_service()
        service.tweak(document_id, [{"feature_id": "b1", "params": {"length": 60.0}}], 1)
        report = service.compare_versions(document_id, 1)
        self.assertEqual(report["doc_diff"]["version_after"], 2)
        self.assertGreater(report["metrics_delta"]["volume_delta"], 0.0)
        self.assertTrue(report["changed_face_indices"])

    def test_notes_queue_stays_out_of_the_document_list(self) -> None:
        service, document_id = _box_service()
        added = service.add_intent_note(document_id, "把方块加长到 80")
        self.assertEqual(added["pending"], 1)
        listed = service.list_intents(document_id)["intents"]
        self.assertEqual(listed[0]["text"], "把方块加长到 80")

        ids = [item["id"] for item in service.list_documents()]
        self.assertIn(document_id, ids)
        self.assertEqual(len(ids), 1)

        self.assertEqual(service.clear_intents(document_id)["cleared"], 1)
        self.assertEqual(service.list_intents(document_id)["intents"], [])

    def test_probe_reads_geometry_and_resolves_a_pick(self) -> None:
        service, document_id = _box_service()
        payload = service.probe(
            document_id,
            ref={"source": "b1", "select": "faces", "filters": [{"method": "top"}]},
            picked_point=[0.0, 0.0, 5.0],
            picked_normal=[0.0, 0.0, 1.0],
            picked_area=800.0,
        )
        self.assertIsNotNone(payload["geometry"]["bbox"])
        self.assertTrue(payload["ref_probe"]["ok"])
        self.assertEqual(payload["ref_probe"]["count"], 1)
        self.assertTrue(payload["pick_probe"]["ok"])

        anchor = service.pick(document_id, {
            "point": [0.0, 0.0, 5.0], "normal": [0.0, 0.0, 1.0], "area": 800.0,
        })
        self.assertTrue(anchor["label"].startswith("@b1 top"))
        self.assertIn("surface_type", anchor)
        self.assertIn("suggested_ref", anchor)

    def test_step_disk_cache_and_branch_intent(self) -> None:
        service, document_id = _box_service()
        first = service.step_bytes(document_id, version=1)
        second = service.step_bytes(document_id, version=1)
        self.assertEqual(first, second)
        self.assertTrue(any((service.store.root / "steps").glob("*.step")))

        branched = service.add_intent_note(document_id, "从此分支加孔", base_version=1)
        self.assertEqual(branched["intent"]["base_version"], 1)

    def test_empty_document_reports_vacant(self) -> None:
        service = CADService(Store(tempfile.mkdtemp(prefix="cadwork-review-")))
        document = service.store.create("Blank")
        state = service.state(document.id)
        self.assertTrue(state["vacant"])
        self.assertEqual(state["metrics"], None)
        self.assertEqual(state["focus_params"], [])
        self.assertEqual(state["milestones"][0]["version"], 0)


if __name__ == "__main__":
    unittest.main()
