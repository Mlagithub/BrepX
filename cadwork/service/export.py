"""Export parts and assemblies to bytes. Every format is produced in a temp directory."""

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


def assembly_bom_sidecar(result: Any) -> dict[str, Any]:
    """The machine-readable companion written next to a flat assembly STEP."""
    bbox = None
    if result.bbox_min is not None and result.bbox_max is not None:
        bbox = {"min": list(result.bbox_min), "max": list(result.bbox_max)}
    return {
        "assembly": result.document_id,
        "version": result.version,
        "bom": [entry.summary() for entry in result.bom],
        "instances": len(result.instances),
        "placed_parts": len(result.placed_parts),
        "failures": [
            {"path": item.path, "code": item.error_code, "message": item.error_message}
            for item in result.failures
        ],
        "bbox": bbox,
    }


def export_assembly_bytes(
    result: Any, fmt: str = "step", name: str = "assembly"
) -> tuple[bytes, str, dict[str, Any]]:
    """Export placed part leaves as one flat STEP assembly plus a BOM sidecar."""
    fmt = fmt.lower()
    if fmt != "step":
        raise ValueError(f"unsupported assembly format {fmt!r}; expected step")
    parts = [
        item.part.named(item.path.replace("/", "_") or item.instance_id)
        for item in result.placed_parts
        if item.part is not None
    ]
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "assembly.step")
        S.export_step(parts, path, name=name, assembly=True)
        return Path(path).read_bytes(), MEDIA["step"], assembly_bom_sidecar(result)


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
