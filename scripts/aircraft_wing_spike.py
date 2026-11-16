"""Build one swept, tapered wing segment from the generic CAD core.

This is a validation harness, not a domain package. It uses only existing
feature actions, the generic build pipeline and the generic scene projection.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cadwork.design.build import BuildCache, build
from cadwork.design.document import (
    Document,
    Feature,
    Interface,
    Ref,
    document_from_json,
    document_to_json,
    validate_layout,
)
from cadwork.design.generators import _section_points
from cadwork.service.render import render_png
from cadwork.service.scene import build_scene


def wing_document(
    *,
    span: float = 8000.0,
    root_chord: float = 3600.0,
    tip_chord: float = 1800.0,
    sweep_deg: float = 22.0,
    dihedral_deg: float = 5.0,
    root_twist_deg: float = 3.0,
    tip_twist_deg: float = 0.0,
    sections: int = 5,
) -> Document:
    """Create a wing OML document from a small design brief."""
    if sections < 2:
        raise ValueError("sections must be at least 2")
    if min(span, root_chord, tip_chord) <= 0:
        raise ValueError("wing dimensions must be positive")

    features: list[Feature] = []
    for index in range(sections):
        t = index / (sections - 1)
        chord = root_chord + (tip_chord - root_chord) * t
        thickness_ratio = 0.14 + (0.10 - 0.14) * t
        camber = 0.02 * (1.0 - t)
        points = _section_points(chord, thickness_ratio, camber)
        curve_id = f"s{index}_curve"
        face_id = f"s{index}_face"
        rotated_id = f"s{index}_rotated"
        placed_id = f"s{index}_placed"
        features.extend(
            (
                Feature(
                    curve_id,
                    "k_spline",
                    params={
                        "points": [list(point) for point in points],
                        "closed": True,
                    },
                ),
                Feature(
                    face_id,
                    "k_make_face",
                    refs={"outer": Ref(curve_id, "self"), "holes": ()},
                ),
                Feature(
                    rotated_id,
                    "k_rotate",
                    params={
                        "axis": "Z",
                        "angle": root_twist_deg + (tip_twist_deg - root_twist_deg) * t,
                    },
                    refs={"target": Ref(face_id, "self")},
                ),
                Feature(
                    placed_id,
                    "k_translate",
                    params={
                        "x": math.tan(math.radians(sweep_deg)) * span * t,
                        "y": math.tan(math.radians(dihedral_deg)) * span * t,
                        "z": span * t,
                    },
                    refs={"target": Ref(rotated_id, "self")},
                ),
            )
        )

    features.append(
        Feature(
            "wing_body",
            "k_loft",
            refs={
                "sections": tuple(
                    Ref(f"s{index}_placed", "self") for index in range(sections)
                )
            },
        )
    )
    interface = Interface(
        "wing_root",
        "frame",
        "s0_face",
        params={
            "origin": [0.0, 0.0, 0.0],
            "x_axis": [1.0, 0.0, 0.0],
            "z_axis": [0.0, 0.0, 1.0],
        },
    )
    document = Document(
        id="d_wing_spike",
        name="Swept tapered wing validation",
        version=0,
        features=tuple(features),
        interfaces=(interface,),
    )
    validate_layout(document)
    return document


def _identity(part: Any) -> dict[str, Any]:
    box = part.bbox()
    return {
        "volume": round(float(part.volume), 6),
        "area": round(float(part.area), 6),
        "faces": len(part.faces()),
        "bbox": {
            "min": [round(value, 6) for value in box.min],
            "max": [round(value, 6) for value in box.max],
            "size": [round(value, 6) for value in box.size],
        },
    }


def _check_wing(document: Document, result: Any) -> dict[str, Any]:
    part = result.final
    box = part.bbox()
    size = box.size
    mesh = part.mesh(tolerance=1.0, angle=30.0)

    section_errors = []
    spacing_errors = []
    for index in range(5):
        t = index / 4
        target_chord = 3600.0 + (1800.0 - 3600.0) * t
        target_thickness = target_chord * (0.14 + (0.10 - 0.14) * t)
        section = result.outputs[f"s{index}_face"]
        section_box = section.bbox()
        actual_chord, actual_thickness = section_box.size[0], section_box.size[1]
        section_errors.append(
            {
                "station": index,
                "chord_mm": round(float(actual_chord), 6),
                "chord_target_mm": round(float(target_chord), 6),
                "chord_error_pct": round(
                    abs(float(actual_chord) - target_chord) / target_chord * 100.0, 6
                ),
                "thickness_mm": round(float(actual_thickness), 6),
                "thickness_target_mm": round(float(target_thickness), 6),
                "thickness_error_pct": round(
                    abs(float(actual_thickness) - target_thickness)
                    / target_thickness
                    * 100.0,
                    6,
                ),
            }
        )
        placed = result.outputs[f"s{index}_placed"]
        placed_center = placed.bbox().center[2]
        expected_center = 8000.0 * t
        spacing_errors.append(abs(float(placed_center) - expected_center))

    scene = build_scene(part, "wing_body")
    interface = document.interface("wing_root")
    return {
        "valid": bool(part.is_valid()),
        "solids": len(part.solids()),
        "closed_mesh": bool(mesh.is_closed()),
        "triangles": len(mesh.triangles),
        "bbox_size_mm": [round(float(value), 6) for value in size],
        "span_error_pct": round(abs(float(size[2]) - 8000.0) / 8000.0 * 100.0, 6),
        "envelope_ok": bool(
            abs(float(size[2]) - 8000.0) <= 1.0
            and float(size[0]) >= 3600.0
            and float(size[1]) > 0.0
        ),
        "section_errors": section_errors,
        "max_chord_error_pct": max(item["chord_error_pct"] for item in section_errors),
        "max_thickness_error_pct": max(
            item["thickness_error_pct"] for item in section_errors
        ),
        "max_station_spacing_error_mm": round(max(spacing_errors), 6),
        "scene_faces": len(scene.get("faces") or []),
        "scene_edges": len(scene.get("edges") or []),
        "interface": {
            "name": interface.name,
            "kind": interface.kind,
            "feature": interface.feature_id,
        },
    }


def _build_summary(result: Any) -> dict[str, Any]:
    return {
        "version": result.document_version,
        "seconds": round(result.seconds, 4),
        "cache_hits": result.cache_hits,
        "features": [
            {
                "id": item.feature_id,
                "seconds": round(item.seconds, 4),
                "cached": item.cached,
                "checks": [check.to_json() for check in item.checks],
            }
            for item in result.features
        ],
        "bodies": [result.bodies[key].summary() for key in sorted(result.bodies)],
    }


def run() -> dict[str, Any]:
    started = time.perf_counter()
    baseline = wing_document()
    result = build(baseline, BuildCache())
    checks = _check_wing(baseline, result)
    render_paths = {}
    for view in ("iso", "front", "top"):
        path = ROOT / "artifacts" / "aircraft-domain" / f"wing-spike-{view}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(render_png(result.final, view=view, size=(900, 600)))
        render_paths[view] = path

    variants = []
    for name, kwargs in (
        ("span_plus_10pct", {"span": 8800.0}),
        ("sweep_plus_5deg", {"sweep_deg": 27.0}),
    ):
        variant_document = wing_document(**kwargs)
        variant_result = build(variant_document, BuildCache())
        variants.append(
            {
                "name": name,
                "brief": kwargs,
                "identity": _identity(variant_result.final),
                "valid": bool(variant_result.final.is_valid()),
                "closed_mesh": bool(
                    variant_result.final.mesh(tolerance=1.0, angle=30).is_closed()
                ),
            }
        )

    payload = document_to_json(baseline)
    replayed = document_from_json(payload)
    replay_result = build(replayed, BuildCache())
    replay_identity = _identity(replay_result.final)
    baseline_identity = _identity(result.final)

    negative_case = None
    try:
        wing_document(sections=1)
    except ValueError as exc:
        negative_case = {"code": "INVALID_SECTION_COUNT", "message": str(exc)}

    baseline_ok = (
        checks["valid"]
        and checks["solids"] == 1
        and checks["closed_mesh"]
        and checks["envelope_ok"]
        and checks["max_chord_error_pct"] < 1.0
        and checks["max_thickness_error_pct"] < 1.0
    )
    variants_ok = all(item["valid"] and item["closed_mesh"] for item in variants)
    replay_ok = replay_identity == baseline_identity
    passed = baseline_ok and variants_ok and replay_ok

    return {
        "schema": "aircraft-wing-validation/1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "duration_seconds": round(time.perf_counter() - started, 3),
        "brief": {
            "span_mm": 8000.0,
            "root_chord_mm": 3600.0,
            "tip_chord_mm": 1800.0,
            "sweep_deg": 22.0,
            "dihedral_deg": 5.0,
            "root_twist_deg": 3.0,
            "tip_twist_deg": 0.0,
            "sections": 5,
        },
        "baseline": {
            "identity": baseline_identity,
            "build": _build_summary(result),
            "checks": checks,
        },
        "variants": variants,
        "replay": {
            "document_sha256": hashlib.sha256(
                json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
            "identity": replay_identity,
            "matches_baseline": replay_ok,
        },
        "render": {
            "views": {
                view: {
                    "path": str(path.relative_to(ROOT)),
                    "width": 900,
                    "height": 600,
                }
                for view, path in render_paths.items()
            }
        },
        "negative_case": negative_case,
        "first_pass": baseline_ok,
        "repair_attempts": 0,
        "failure_points": [],
        "gaps": [
            "no reusable wing compiler; section construction and transforms are inline in the spike",
            "no structured design brief or assumption ledger",
            "no domain checks beyond the spike's local assertions",
            "no gate UI or approval record",
        ],
        "decision": "thin_pack_plus_domain_checks" if passed else "compiler_first",
        "passed": passed,
    }


def main() -> int:
    output = ROOT / "artifacts" / "aircraft-domain" / "wing-spike.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    report = run()
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = {
        "passed": report["passed"],
        "decision": report["decision"],
        "first_pass": report["first_pass"],
        "duration_seconds": report["duration_seconds"],
        "bbox_size_mm": report["baseline"]["checks"]["bbox_size_mm"],
        "max_chord_error_pct": report["baseline"]["checks"]["max_chord_error_pct"],
        "max_thickness_error_pct": report["baseline"]["checks"]["max_thickness_error_pct"],
        "variants": [item["name"] for item in report["variants"]],
        "replay_matches": report["replay"]["matches_baseline"],
        "render": report["render"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nwrote {output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
