"""Build the impeller from the command line.

    python -m cadwork.demo
    python -m cadwork.demo --count 11 --export docs/demo
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from cadwork.design import BuildError, build
from cadwork.samples.impeller import impeller_document


def _export(result, directory: str) -> list[str]:
    from cadwork import smlib as S

    os.makedirs(directory, exist_ok=True)
    written: list[str] = []
    solid = result.outputs.get("f5")
    if solid is not None:
        path = os.path.join(directory, "impeller.step")
        S.export_step(solid, path)
        written.append(path)
        path = os.path.join(directory, "impeller.stl")
        S.export_stl(solid, path)
        written.append(path)
    fluid = result.outputs.get("f9")
    if fluid is not None:
        path = os.path.join(directory, "fluid.step")
        S.export_step(fluid, path)
        written.append(path)
    boundaries = [
        {"feature": feature_id, **tag} for feature_id, tag in sorted(result.tags.items())
    ]
    path = os.path.join(directory, "cfd.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"boundaries": boundaries}, handle, ensure_ascii=False, indent=2)
    written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the impeller document.")
    parser.add_argument("--count", type=int, default=9, help="number of blades")
    parser.add_argument("--wrap", type=float, default=30.0, help="wrap angle in degrees")
    parser.add_argument("--fillet", type=float, default=0.3, help="fillet radius in mm")
    parser.add_argument("--export", default=None, help="directory for STEP/STL/CFD output")
    parser.add_argument("--json", action="store_true", help="print the build summary as JSON")
    args = parser.parse_args(argv)

    document = impeller_document(count=args.count, wrap=args.wrap, fillet_radius=args.fillet)
    try:
        result = build(document)
    except BuildError as exc:
        print(json.dumps(exc.to_json(), ensure_ascii=False, indent=2))
        return 1

    summary = result.summary()
    summary["tags"] = result.tags
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"built {len(result.features)} features in {result.seconds:.2f}s "
              f"({result.cache_hits} cache hits)")
        for item in result.features:
            status = "ok" if all(check.ok for check in item.checks) else "FAILED"
            print(f"  {item.feature_id:>3}  {item.seconds:6.3f}s  {status}  "
                  f"cached={item.cached}")
        for feature_id, tag in sorted(result.tags.items()):
            print(f"  tag {feature_id}: {tag['kind']}/{tag['name']} "
                  f"({tag['faces']} face(s))")

    if args.export:
        for path in _export(result, args.export):
            print(f"  wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
