"""The sample documents the workbench can build, with their editable parameters.

One table, so the API and the browser never hardcode a part: the client renders
whatever parameters the server declares, and adding a part family means adding
an entry here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from cadwork.design.document import Document

from .blade import blade_document
from .flange import flange_document
from .impeller import impeller_document
from .volute import volute_document


@dataclass(frozen=True)
class SampleParam:
    name: str
    default: float | int
    minimum: float
    maximum: float
    kind: str = "float"
    unit: str | None = None
    description: str = ""


@dataclass(frozen=True)
class SampleSpec:
    name: str
    title: str
    summary: str
    params: tuple[SampleParam, ...]
    build: Callable[..., Document]


SAMPLES: dict[str, SampleSpec] = {
    "impeller": SampleSpec(
        name="impeller",
        title="Impeller",
        summary="Back disc, twisted blades on a circular pattern, one fillet.",
        params=(
            SampleParam("count", 9, 5, 24, "int", "blades"),
            SampleParam("wrap", 30.0, 10.0, 60.0, "float", "deg"),
            SampleParam("fillet_radius", 0.3, 0.0, 1.0, "float", "mm"),
        ),
        build=lambda count=9, wrap=30.0, fillet_radius=0.3, name="Impeller": impeller_document(
            count=int(count), wrap=float(wrap), fillet_radius=float(fillet_radius), name=name,
        ),
    ),
    "volute": SampleSpec(
        name="volute",
        title="Volute casing",
        summary="Spiral centre line, growing section, swept and shelled.",
        params=(
            SampleParam("turns", 1.25, 0.75, 3.0, "float", "turn"),
            SampleParam("r_end", 70.0, 40.0, 120.0, "float", "mm"),
            SampleParam("wall", 1.0, 0.5, 1.2, "float", "mm"),
        ),
        build=lambda turns=1.25, r_end=70.0, wall=1.0, name="Volute": volute_document(
            turns=float(turns), r_end=float(r_end), wall=float(wall), name=name,
        ),
    ),
    "blade": SampleSpec(
        name="blade",
        title="Hollow blade",
        summary="One twisted loft, hollowed by a shell.",
        params=(
            SampleParam("wrap", 60.0, 20.0, 90.0, "float", "deg"),
            SampleParam("b_out", 22.0, 10.0, 40.0, "float", "mm"),
            SampleParam("thickness", 1.0, 0.5, 1.3, "float", "mm"),
        ),
        build=lambda wrap=60.0, b_out=22.0, thickness=1.0, name="Hollow blade": blade_document(
            wrap=float(wrap), b_out=float(b_out), thickness=float(thickness), name=name,
        ),
    ),
    "flange": SampleSpec(
        name="flange",
        title="Flange",
        summary="Plate and boss, through bore, bolt circle, chamfered rim.",
        params=(
            SampleParam("plate_radius", 60.0, 40.0, 120.0, "float", "mm"),
            SampleParam("boss_height", 34.0, 10.0, 60.0, "float", "mm"),
            SampleParam("bolt_count", 8, 3, 16, "int", "holes"),
            SampleParam("chamfer_length", 1.5, 0.2, 4.0, "float", "mm"),
        ),
        build=lambda plate_radius=60.0, boss_height=34.0, bolt_count=8,
        chamfer_length=1.5, name="Flange": flange_document(
            plate_radius=float(plate_radius),
            boss_height=float(boss_height),
            bolt_count=int(bolt_count),
            chamfer_length=float(chamfer_length),
            name=name,
        ),
    ),
}


def catalog() -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "title": spec.title,
            "summary": spec.summary,
            "params": [
                {
                    "name": param.name,
                    "default": param.default,
                    "min": param.minimum,
                    "max": param.maximum,
                    "kind": param.kind,
                    "unit": param.unit,
                    "description": param.description,
                }
                for param in spec.params
            ],
        }
        for spec in SAMPLES.values()
    ]


def build(name: str, params: dict[str, Any] | None = None) -> Document:
    """Build a sample document, with the declared parameters checked."""
    spec = SAMPLES.get(name)
    if spec is None:
        raise KeyError(name)
    given = dict(params or {})
    unknown = set(given) - {param.name for param in spec.params}
    if unknown:
        raise ValueError(f"unknown parameters for {name}: {', '.join(sorted(unknown))}")
    values: dict[str, Any] = {}
    for param in spec.params:
        raw = given.get(param.name, param.default)
        if param.kind == "int":
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise ValueError(f"{param.name} must be an integer")
            value: Any = int(raw)
        else:
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise ValueError(f"{param.name} must be a number")
            value = float(raw)
        if not (param.minimum <= value <= param.maximum):
            raise ValueError(
                f"{param.name} must be within {param.minimum}..{param.maximum}, got {value}"
            )
        values[param.name] = value
    return spec.build(**values)
