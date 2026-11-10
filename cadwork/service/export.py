"""Export a part to bytes. Every format is produced in a temp directory."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from cadwork import smlib as S

MEDIA = {
    "step": "application/step",
    "stl": "application/sla",
    "glb": "model/gltf-binary",
    "dxf": "application/dxf",
}


def export_bytes(part: Any, fmt: str, plane: str = "XZ") -> tuple[bytes, str]:
    fmt = fmt.lower()
    if fmt not in MEDIA:
        raise ValueError(f"unsupported format {fmt!r}; expected {', '.join(MEDIA)}")
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, f"model.{fmt}")
        if fmt == "step":
            S.export_step(part, path)
        elif fmt == "stl":
            S.export_stl(part, path)
        elif fmt == "glb":
            S.export_glb(part, path)
        else:
            plane_obj = getattr(S.Plane, plane.upper(), None)
            if plane_obj is None:
                raise ValueError(f"unknown section plane {plane!r}")
            S.export_dxf(part.section(plane_obj), path)
        return Path(path).read_bytes(), MEDIA[fmt]
