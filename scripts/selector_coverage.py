"""Topological canonical selector coverage evaluation script (Assumption A1)."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from smlibpy import Box, Cylinder, Hole
from backend.selector.canonicalizer import canonicalize_face


def build_evaluation_parts() -> list[tuple[str, object]]:
    parts = []
    parts.append(("Box", Box(60, 40, 20)))
    parts.append(("Cylinder", Cylinder(20, 50)))
    flange = Box(80, 80, 20)
    top_f = list(flange.faces().top())[0]
    holed = flange - Hole(10, 40).on(top_f)
    parts.append(("Holed_Flange", holed))
    return parts


def evaluate_coverage() -> int:
    parts = build_evaluation_parts()
    total_faces = 0
    high_priority_faces = 0

    print("=== Selector Coverage Audit (Threshold >= 90%) ===")

    for name, part in parts:
        faces = list(part.faces())
        p_total = len(faces)
        p_high = 0
        fallback_details = []

        for face in faces:
            sel = canonicalize_face(face, part)
            if "nearest" not in sel:
                p_high += 1
            else:
                fallback_details.append((face.geom_type, sel))

        total_faces += p_total
        high_priority_faces += p_high
        ratio = (p_high / p_total) * 100.0 if p_total else 100.0
        print(f"Part [{name}]: {p_high}/{p_total} ({ratio:.1f}%) non-fallback rules")
        if fallback_details:
            for gt, sel in fallback_details:
                print(f"  Fallback: {gt} -> {sel}")

    overall_ratio = (high_priority_faces / total_faces) * 100.0 if total_faces else 100.0
    print(f"\nOverall Coverage: {high_priority_faces}/{total_faces} ({overall_ratio:.2f}%)")

    if overall_ratio < 90.0:
        print(f"FAIL: Coverage {overall_ratio:.2f}% is below 90% threshold.")
        return 1

    print("OK: Selector coverage meets or exceeds 90% target.")
    return 0


if __name__ == "__main__":
    sys.exit(evaluate_coverage())
