"""The four acceptance criteria, exercised through the service layer."""

from __future__ import annotations

import tempfile
import unittest

from cadwork.service.acceptance import run_acceptance


class AcceptanceTests(unittest.TestCase):
    def test_four_criteria(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cadwork-accept-test-") as folder:
            report = run_acceptance(folder)
        self.assertTrue(report["ok"], report)
        self.assertEqual(len(report["steps"]), 5)
        self.assertIn("BUILD_FAILED", report["steps"][3])
        self.assertIn("restarted service", report["steps"][4])


if __name__ == "__main__":
    unittest.main()
