"""Industrial standard format exporters for STEP, STL, DXF, and CFD metadata dictionaries across single/multi bodies."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Sequence

from backend.core.errors import DomainError
from backend.core.patches import BoundaryPatch


class ExportError(DomainError):
    def __init__(self, format_name: str, message: str) -> None:
        super().__init__(f"Export failure for format '{format_name}': {message}")
        self.format_name = format_name

    def to_diagnostic(self) -> dict[str, Any]:
        diag = super().to_diagnostic()
        diag["format"] = self.format_name
        return diag


def _extract_exportable_geometry(target: Any) -> Any:
    if target is None:
        return None
    if hasattr(target, "bodies") and isinstance(target.bodies, dict):
        if not target.bodies:
            return None
        if len(target.bodies) == 1:
            return next(iter(target.bodies.values()))

        # For multiple bodies, compound or fuse together
        import smlibpy
        parts = [p for p in target.bodies.values() if p is not None]
        if not parts:
            return None
        combined = parts[0]
        for next_p in parts[1:]:
            try:
                combined = combined + next_p
            except Exception:
                continue
        return combined

    return target


def export_step(target: Any, output_path: str | None = None) -> bytes:
    part = _extract_exportable_geometry(target)
    if part is None:
        raise ExportError("step", "No geometry available to export.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = os.path.join(tmp_dir, "model.step")
        try:
            part.export(tmp_file)
            with open(tmp_file, "rb") as f:
                data = f.read()
            if output_path:
                with open(output_path, "wb") as out:
                    out.write(data)
            return data
        except Exception as exc:
            raise ExportError("step", str(exc)) from exc


def export_stl(target: Any, output_path: str | None = None) -> bytes:
    part = _extract_exportable_geometry(target)
    if part is None:
        raise ExportError("stl", "No geometry available to export.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = os.path.join(tmp_dir, "model.stl")
        try:
            part.export(tmp_file)
            with open(tmp_file, "rb") as f:
                data = f.read()
            if output_path:
                with open(output_path, "wb") as out:
                    out.write(data)
            return data
        except Exception as exc:
            raise ExportError("stl", str(exc)) from exc


def export_dxf(target: Any, plane_name: str = "XY", offset: float = 0.0, output_path: str | None = None) -> bytes:
    part = _extract_exportable_geometry(target)
    if part is None:
        raise ExportError("dxf", "No geometry available to extract section from.")

    import smlibpy
    plane_map = {"XY": smlibpy.Plane.XY, "YZ": smlibpy.Plane.YZ, "XZ": smlibpy.Plane.XZ}
    plane = plane_map.get(plane_name.upper(), smlibpy.Plane.XY)
    if abs(offset) > 1e-6:
        plane = plane.offset(offset)

    try:
        sec = part.section(plane)
    except Exception as exc:
        raise ExportError("dxf", f"Failed to compute planar section: {exc}") from exc

    if not sec or not hasattr(sec, "export"):
        raise ExportError("dxf", "Planar section produced no valid 2D contour curves.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = os.path.join(tmp_dir, "section.dxf")
        try:
            sec.export(tmp_file)
            with open(tmp_file, "rb") as f:
                data = f.read()
            if output_path:
                with open(output_path, "wb") as out:
                    out.write(data)
            return data
        except Exception as exc:
            raise ExportError("dxf", str(exc)) from exc


def export_cfd_dict(patches: Sequence[BoundaryPatch]) -> bytes:
    patch_records = []
    for patch in patches:
        patch_records.append({
            "name": patch.name,
            "semantic_type": patch.semantic_type,
            "color_hex": patch.color_hex,
            "area": patch.area,
            "selector": patch.selector_expr,
        })

    payload = {
        "format": "OpenFOAM_Fluent_CFD_Dictionary",
        "version": "1.0",
        "boundary_count": len(patch_records),
        "boundaries": patch_records,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def export_step_ap242(target: Any, patches: Sequence[BoundaryPatch], output_path: str | None = None) -> tuple[bytes, bool]:
    step_bytes = export_step(target, output_path)
    return step_bytes, False
