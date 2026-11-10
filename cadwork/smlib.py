"""The only module that imports smlibpy.

Every other module imports `cadwork.smlib`. Upgrading the kernel is therefore
one file, and an accidental deep import is a review finding rather than a
latent coupling.
"""

from __future__ import annotations

from typing import Any

import smlibpy
from smlibpy import (
    Box,
    Circle,
    Cone,
    Cylinder,
    Edge,
    Face,
    Helix,
    Part,
    Plane,
    PolarLocations,
    Polygon,
    Rectangle,
    RegularPolygon,
    ShapeList,
    Sketch,
    Sphere,
    Spiral,
    X,
    Y,
    Z,
    Wire,
    export_dxf,
    export_glb,
    export_step,
    export_stl,
    extrude,
    import_step,
    loft,
    GridLocations,
    merge,
    mirror,
    render,
    revolve,
    shell,
    split,
    sweep,
    thicken,
)

VERSION = getattr(smlibpy, "__version__", "unknown")


class AxisName:
    """Resolve a serialised axis name ("X" | "Y" | "Z") to a kernel axis."""

    _axes = {"X": X, "Y": Y, "Z": Z}

    @classmethod
    def get(cls, name: str) -> Any:
        try:
            return cls._axes[str(name).upper()]
        except KeyError as exc:
            raise ValueError(f"unknown axis {name!r}; expected X, Y or Z") from exc


def error_text(exc: BaseException) -> str:
    """Stable one-line kernel failure text for hints and diagnostics."""
    message = str(exc).strip().replace("\n", " ")
    return message or exc.__class__.__name__
