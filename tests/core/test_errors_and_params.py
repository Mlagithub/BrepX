"""Unit tests for core error contracts and parameter verification."""

from __future__ import annotations

import unittest
from backend.core.errors import (
    DomainError,
    OperatorNotFoundError,
    ParamRangeError,
    ParamTypeError,
    PostconditionError,
    PreconditionError,
)
from backend.core.params import ParamKind, ParamSpec, validate_value
from backend.selector.errors import SelectorResolutionError


class TestErrors(unittest.TestCase):
    def test_domain_error_base_diagnostic(self) -> None:
        err = DomainError("generic failure")
        diag = err.to_diagnostic()
        self.assertEqual(diag["error"], "DomainError")
        self.assertEqual(diag["message"], "generic failure")

    def test_operator_not_found_diagnostic(self) -> None:
        err = OperatorNotFoundError("unknown_op", ["box", "cylinder"])
        diag = err.to_diagnostic()
        self.assertEqual(diag["op"], "unknown_op")
        self.assertEqual(diag["closest"], ["box", "cylinder"])

    def test_param_errors_diagnostic(self) -> None:
        t_err = ParamTypeError("radius", "abc", "float")
        self.assertEqual(t_err.to_diagnostic()["param"], "radius")

        r_err = ParamRangeError("radius", -1.0, "0.0..100.0")
        self.assertEqual(r_err.to_diagnostic()["allowed"], "0.0..100.0")

    def test_pre_and_postcondition_errors(self) -> None:
        pre = PreconditionError("Empty journal")
        self.assertEqual(pre.to_diagnostic()["reason"], "Empty journal")

        post = PostconditionError("is_solid", False, True, "Check geometry closure")
        diag = post.to_diagnostic()
        self.assertEqual(diag["actual"], False)
        self.assertEqual(diag["expected"], True)
        self.assertEqual(diag["suggestion"], "Check geometry closure")

    def test_selector_resolution_error(self) -> None:
        err = SelectorResolutionError("faces().top()", 1, ["faces().bottom()"], "no_match")
        diag = err.to_diagnostic()
        self.assertEqual(diag["expr"], "faces().top()")
        self.assertEqual(diag["base_version"], "1")
        self.assertEqual(diag["reason"], "no_match")

        with self.assertRaises(ValueError):
            SelectorResolutionError("f()", 1, reason="invalid_reason_string")


class TestParams(unittest.TestCase):
    def test_param_spec_validation(self) -> None:
        with self.assertRaises(ValueError):
            ParamSpec(ParamKind.FLOAT, choices=("a", "b"))

        spec = ParamSpec(ParamKind.ENUM, default="X", choices=("X", "Y", "Z"))
        self.assertEqual(validate_value(spec, None), "X")
        self.assertEqual(validate_value(spec, "Y"), "Y")
        with self.assertRaises(ParamRangeError):
            validate_value(spec, "W")

    def test_numeric_validation(self) -> None:
        spec = ParamSpec(ParamKind.FLOAT, default=None, min=0.0, max=10.0)
        with self.assertRaises(ParamRangeError):
            validate_value(spec, None)

        with self.assertRaises(ParamTypeError):
            validate_value(spec, True)

        with self.assertRaises(ParamRangeError):
            validate_value(spec, -0.1)

        self.assertEqual(validate_value(spec, 5), 5.0)

    def test_bool_validation(self) -> None:
        spec = ParamSpec(ParamKind.BOOL, default=False)
        self.assertEqual(validate_value(spec, True), True)
        with self.assertRaises(ParamTypeError):
            validate_value(spec, 1)


if __name__ == "__main__":
    unittest.main()
