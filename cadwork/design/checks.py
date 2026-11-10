"""Feature checks. A failed check blocks the build and the edit.

`hint` is written for a model to read; `name` and `observed` are for programs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    observed: dict[str, Any] = field(default_factory=dict)
    expected: str | None = None
    hint: str | None = None


def _guard(name: str, expected: str | None, action) -> CheckResult:
    try:
        observed = action()
        ok = bool(observed.pop("_ok"))
        return CheckResult(name, ok, observed, expected, None if ok else expected)
    except Exception as exc:  # a check that cannot run is a failed check
        return CheckResult(name, False, {"error": str(exc)}, expected, str(exc))


def valid(part: Any) -> CheckResult:
    return _guard("valid", "shape must pass the kernel validity check",
                  lambda: {"_ok": part.is_valid()})


def solid(part: Any) -> CheckResult:
    def action() -> dict[str, Any]:
        count = len(part.solids())
        return {"_ok": count >= 1, "solids": count}

    return _guard("solid", "at least one solid body", action)


def watertight(part: Any) -> CheckResult:
    def action() -> dict[str, Any]:
        mesh = part.mesh()
        closed = bool(mesh.is_closed())
        return {"_ok": closed, "closed": closed, "triangles": len(mesh.triangles)}

    return _guard("watertight", "closed mesh, no free edges", action)


def volume_gt(part: Any, minimum: float) -> CheckResult:
    def action() -> dict[str, Any]:
        volume = float(part.volume)
        return {"_ok": volume > minimum, "volume": volume, "min": minimum}

    return _guard("volume", f"volume > {minimum}", action)


def min_edge(part: Any, minimum: float) -> CheckResult:
    def action() -> dict[str, Any]:
        lengths = [float(edge.length) for edge in part.edges()]
        shortest = min(lengths) if lengths else 0.0
        return {"_ok": shortest >= minimum, "min_edge": shortest, "min": minimum}

    return _guard("no_degenerate", f"every edge >= {minimum} mm", action)


def face_count(part: Any, minimum: int | None = None, maximum: int | None = None) -> CheckResult:
    def action() -> dict[str, Any]:
        count = len(part.faces())
        ok = (minimum is None or count >= minimum) and (maximum is None or count <= maximum)
        return {"_ok": ok, "faces": count, "min": minimum, "max": maximum}

    return _guard("face_count", "face count within the feature's expected range", action)


def thickness_param(params: dict[str, Any], key: str, minimum: float) -> CheckResult:
    value = float(params.get(key, 0.0))
    return CheckResult(
        "thickness",
        value >= minimum,
        {"thickness": value, "min": minimum},
        f"{key} >= {minimum} mm",
        None if value >= minimum else f"increase {key} to at least {minimum} mm",
    )


def volume_ratio(part: Any, expected: float, tolerance: float) -> CheckResult:
    def action() -> dict[str, Any]:
        volume = float(part.volume)
        ok = abs(volume - expected) <= abs(expected) * tolerance + 1e-9
        return {"_ok": ok, "volume": volume, "expected": expected, "tolerance": tolerance}

    return _guard("volume_ratio", f"volume within {tolerance:.0%} of {expected:.1f}", action)


def volume_between(part: Any, low: float, high: float) -> CheckResult:
    def action() -> dict[str, Any]:
        volume = float(part.volume)
        lower = low * (1.0 - 1e-6) - 1e-9
        upper = high * (1.0 + 1e-6) + 1e-9
        return {"_ok": lower <= volume <= upper, "volume": volume,
                "low": low, "high": high}

    return _guard("volume_range", "volume between the operand bounds", action)
