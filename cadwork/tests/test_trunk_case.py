"""The main trunk: intent, plan, build, failure isolation, recovery, incremental edit."""

from __future__ import annotations

import tempfile
import unittest

from cadwork.service.service import CADService
from cadwork.service.store import Store
from cadwork.service.trunk_case import run_trunk_case


class TrunkCaseTests(unittest.TestCase):
    def test_five_turns_with_failure_recovery_and_incremental_edit(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            service = CADService(Store(folder))
            summary = run_trunk_case(service)

            self.assertEqual(len(summary["turns"]), 5)
            versions = [turn["version"] for turn in summary["turns"]]
            self.assertEqual(versions, [3, 6, 6, 7, 11])
            self.assertIsNotNone(summary["turns"][2]["error"])
            self.assertEqual(summary["turns"][2]["version_after_failure"], 6)
            self.assertIsNone(summary["turns"][3]["error"])
            self.assertIsNone(summary["turns"][4]["error"])
            self.assertEqual(summary["final_version"], 11)
            self.assertTrue(all(node["status"] == "done"
                                for node in summary["final_plan"]["nodes"]))
            for turn in summary["turns"]:
                self.assertTrue(turn["png"])
                self.assertTrue(turn["step"])
