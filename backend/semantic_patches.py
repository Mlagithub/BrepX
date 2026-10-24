"""CFD Boundary Surface Semantic Patch Manager for BrepX.

Binds physical CFD boundary conditions (inlet, outlet, wall, symmetry,
interface, internal) to B-Rep topological faces with geometric fingerprint
tracking (center, normal, area, geom_type) for automatic re-anchoring and
STEP AP242 / CFD dictionary export.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from enum import Enum
from typing import Any

import smlibpy
from smlibpy import Part, Shell


class BoundarySemanticType(str, Enum):
    INLET = "inlet"
    OUTLET = "outlet"
    WALL = "wall"
    SYMMETRY = "symmetry"
    INTERFACE = "interface"
    INTERNAL = "internal"


SEMANTIC_COLORS: dict[BoundarySemanticType, str] = {
    BoundarySemanticType.INLET: "#3a86ff",      # Deep Blue
    BoundarySemanticType.OUTLET: "#ff006e",     # Magenta Red
    BoundarySemanticType.WALL: "#8d99ae",       # Slate Gray
    BoundarySemanticType.SYMMETRY: "#06d6a0",   # Cyan Green
    BoundarySemanticType.INTERFACE: "#fb5607",  # Warm Orange
    BoundarySemanticType.INTERNAL: "#ffbe0b",   # Amber Yellow
}


class SemanticPatchManager:
    """Manages CFD surface semantic patches bound to B-Rep faces."""

    def __init__(self) -> None:
        self.patches: dict[str, dict[str, Any]] = {}

    def clear(self) -> None:
        self.patches.clear()

    def set_patch(
        self,
        face_indices: list[int],
        semantic_type: str,
        name: str | None = None,
        part: Any = None,
    ) -> dict[str, Any]:
        """Bind one or more B-Rep face indices to a named CFD boundary patch."""
        try:
            sem_enum = BoundarySemanticType(semantic_type.lower())
        except ValueError:
            sem_enum = BoundarySemanticType.WALL

        clean_indices = sorted({int(i) for i in face_indices if int(i) >= 0})
        if not clean_indices:
            raise ValueError("必须至少指定一个有效的 B-Rep 拓扑面索引")

        # Remove these face_indices from any previously assigned patches
        empty_ids: list[str] = []
        for pid, existing in self.patches.items():
            existing["face_indices"] = [idx for idx in existing["face_indices"] if idx not in clean_indices]
            if not existing["face_indices"]:
                empty_ids.append(pid)
        for pid in empty_ids:
            del self.patches[pid]

        if not name or not name.strip():
            count = sum(1 for p in self.patches.values() if p["semantic_type"] == sem_enum.value) + 1
            name = f"{sem_enum.value}_{count}"

        fingerprints: list[dict[str, Any]] = []
        total_area = 0.0
        avg_normal = [0.0, 0.0, 1.0]

        if part is not None and hasattr(part, "faces"):
            faces_list = list(part.faces())
            normals_acc = [0.0, 0.0, 0.0]
            valid_n = 0
            for idx in clean_indices:
                if 0 <= idx < len(faces_list):
                    f = faces_list[idx]
                    f_area = float(getattr(f, "area", 0.0))
                    total_area += f_area
                    c = list(f.center().to_tuple())
                    try:
                        n = list(f.normal_at().to_tuple())
                        for k in range(3):
                            normals_acc[k] += n[k]
                        valid_n += 1
                    except Exception:
                        n = [0.0, 0.0, 1.0]
                    fingerprints.append({
                        "face_index": idx,
                        "geom_type": getattr(f, "geom_type", "nurbs"),
                        "center": [round(x, 3) for x in c],
                        "normal": [round(x, 3) for x in n],
                        "area": round(f_area, 2),
                    })
            if valid_n > 0:
                avg_normal = [round(x / valid_n, 3) for x in normals_acc]

        patch_id = f"patch_{uuid.uuid4().hex[:6]}"
        patch_data = {
            "id": patch_id,
            "name": name.strip(),
            "semantic_type": sem_enum.value,
            "face_indices": clean_indices,
            "color_hex": SEMANTIC_COLORS.get(sem_enum, "#3a86ff"),
            "area": round(total_area, 2),
            "normal": avg_normal,
            "fingerprints": fingerprints,
        }
        self.patches[patch_id] = patch_data
        return patch_data

    def rebind_to_part(self, part: Any) -> None:
        """Re-anchor patches by geometric fingerprint (center + normal) when topology changes."""
        if part is None or not hasattr(part, "faces") or not self.patches:
            return
        faces_list = list(part.faces())
        if not faces_list:
            return

        for patch in self.patches.values():
            fps = patch.get("fingerprints") or []
            if not fps:
                patch["face_indices"] = [i for i in patch["face_indices"] if 0 <= i < len(faces_list)]
                continue

            matched_indices: list[int] = []
            total_area = 0.0
            for fp in fps:
                best_idx = None
                best_dist = 1e9
                fp_c = fp.get("center", [0.0, 0.0, 0.0])
                for j, cand in enumerate(faces_list):
                    c = cand.center().to_tuple()
                    dist = sum((c[k] - fp_c[k]) ** 2 for k in range(3)) ** 0.5
                    if dist < best_dist and dist < 25.0:
                        best_dist = dist
                        best_idx = j
                if best_idx is not None and best_idx not in matched_indices:
                    matched_indices.append(best_idx)
                    total_area += float(getattr(faces_list[best_idx], "area", 0.0))

            if matched_indices:
                patch["face_indices"] = sorted(matched_indices)
                patch["area"] = round(total_area, 2)

    def remove_patch(self, patch_id: str) -> bool:
        if patch_id in self.patches:
            del self.patches[patch_id]
            return True
        return False

    def get_all_patches(self) -> list[dict[str, Any]]:
        return list(self.patches.values())

    def export_cfd_metadata(self) -> dict[str, Any]:
        """Export OpenFOAM / Fluent compatible boundary dictionary JSON."""
        boundaries: dict[str, Any] = {}
        for p in self.patches.values():
            boundaries[p["name"]] = {
                "type": p["semantic_type"],
                "face_indices": p["face_indices"],
                "area_mm2": p["area"],
                "normal": p["normal"],
                "color": p["color_hex"],
            }
        return {
            "format": "SMLib-CFD-Boundary-Specification-v2",
            "unit": "mm",
            "patches_count": len(self.patches),
            "boundaries": boundaries,
        }

    def export_step_with_semantics(self, part: Any) -> bytes:
        """Export STEP AP242 carrying both the solid body and named semantic boundary shells."""
        if part is None:
            raise ValueError("当前没有可导出的几何实体")

        shapes_to_export: list[Any] = [part.named("solid_domain") if hasattr(part, "named") else part]
        if hasattr(part, "faces") and self.patches:
            faces_list = list(part.faces())
            for p in self.patches.values():
                for k_idx, f_idx in enumerate(p["face_indices"]):
                    if 0 <= f_idx < len(faces_list):
                        try:
                            sh = faces_list[f_idx].to_shell()
                            tag_name = f"{p['semantic_type'].upper()}_{p['name']}"
                            if len(p["face_indices"]) > 1:
                                tag_name += f"_{k_idx}"
                            shapes_to_export.append(sh.named(tag_name).colored(p["color_hex"]))
                        except Exception:
                            continue

        out_path = os.path.join(tempfile.gettempdir(), f"cfd_semantic_{uuid.uuid4().hex[:8]}.step")
        try:
            smlibpy.export(shapes_to_export, out_path)
            with open(out_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(out_path):
                try:
                    os.remove(out_path)
                except OSError:
                    pass


semantic_patch_manager = SemanticPatchManager()
