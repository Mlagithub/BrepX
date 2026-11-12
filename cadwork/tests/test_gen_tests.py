"""Every inventory GEN entry has a component case, and every case passes."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cadwork.service import gen_tests


class GenComponentTests(unittest.TestCase):
    def test_cases_cover_every_gen_entry(self) -> None:
        self.assertEqual(len(gen_tests.GEN_KEYS), 152)
        self.assertEqual(gen_tests.MISSING, [])
        self.assertEqual(gen_tests.EXTRA, [])
        self.assertEqual(set(gen_tests.CASES), set(gen_tests.GEN_KEYS))

    def test_all_cases_pass_in_the_real_kernel(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            summary = gen_tests.run_all(folder, "unit")
        self.assertEqual(summary["total"], 152)
        self.assertEqual(summary["passed"], 152)
        self.assertEqual(summary["failed"], [])

    def test_render_keeps_a_nonblank_png(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            result = gen_tests.render_case("smlibpy.Box", folder, "unit")
            png = Path(folder) / "unit" / "render" / "smlibpy_Box.png"
        self.assertEqual(result["status"], "passed")
        self.assertGreater(result["nonwhite"], 64)
        self.assertEqual(result["width"], 640)
        self.assertFalse(png.exists())  # the temporary folder was removed
