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
from cadwork.samples.registry import SAMPLES
from cadwork.samples.registry import build as make_sample


def _export_part(result, directory: str, stem: str, feature_id: str) -> list[str]:
    from cadwork import smlib as S

    os.makedirs(directory, exist_ok=True)
    part = result.outputs.get(feature_id)
    if part is None:
        return []
    written: list[str] = []
    for suffix, exporter in (("step", S.export_step), ("stl", S.export_stl)):
        path = os.path.join(directory, f"{stem}.{suffix}")
        exporter(part, path)
        written.append(path)
    return written


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
    parser = argparse.ArgumentParser(description="Build a sample document.")
    parser.add_argument("--sample", default="impeller", choices=tuple(sorted(SAMPLES)),
                        help="which sample document to build")
    parser.add_argument("--count", type=int, default=9, help="number of blades (impeller)")
    parser.add_argument("--wrap", type=float, default=30.0, help="wrap angle in degrees (impeller)")
    parser.add_argument("--fillet", type=float, default=0.3, help="fillet radius in mm (impeller)")
    parser.add_argument("--export", default=None, help="directory for STEP/STL/CFD output")
    parser.add_argument("--json", action="store_true", help="print the build summary as JSON")
    args = parser.parse_args(argv)

    if args.sample == "impeller":
        document = make_sample("impeller", {"count": args.count, "wrap": args.wrap,
                                           "fillet_radius": args.fillet})
    else:
        document = make_sample(args.sample)
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
        if args.sample == "impeller":
            written = _export(result, args.export)
        else:
            final_id = document.features[-1].id
            written = _export_part(result, args.export, args.sample, final_id)
        for path in written:
            print(f"  wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
