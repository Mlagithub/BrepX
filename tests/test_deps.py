"""Dependency availability verification tests for BrepX."""

from __future__ import annotations

import unittest


class TestDependencies(unittest.TestCase):
    def test_smlibpy_import_and_version(self) -> None:
        import smlibpy

        self.assertTrue(hasattr(smlibpy, "__version__"))
        self.assertIsInstance(smlibpy.__version__, str)

    def test_fastapi_import(self) -> None:
        import fastapi

        self.assertTrue(hasattr(fastapi, "__version__"))

    def test_uvicorn_import(self) -> None:
        import uvicorn

        self.assertTrue(hasattr(uvicorn, "__version__"))

    def test_pydantic_import(self) -> None:
        import pydantic

        self.assertTrue(hasattr(pydantic, "__version__"))

    def test_numpy_import(self) -> None:
        import numpy

        self.assertTrue(hasattr(numpy, "__version__"))


if __name__ == "__main__":
    unittest.main()
