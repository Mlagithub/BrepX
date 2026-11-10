"""Build one sample document end to end and prove it.

    python scripts/accept_volute.py                 # the volute, into .tmp/accept
    python scripts/accept_volute.py --sample blade  # any registered sample
    python scripts/accept_volute.py --all           # every sample, one run

What "accept" means here, in order:
  1. the document builds and every feature check passes;
  2. the final body is closed and has volume;
  3. STEP and STL export to non-trivial files;
  4. a PNG renders (skipped with --no-render).

Exit code 0 only when all of that holds for every requested sample.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cadwork.design import BuildError, build  # noqa: E402
from cadwork.samples.registry import SAMPLES, build as make_sample  # noqa: E402


def _check_sample(name: str, out_dir: str, render: bool) -> dict:
    started = time.perf_counter()
    document = make_sample(name)
    try:
        result = build(document)
    except BuildError as exc:
        return {"sample": name, "ok": False, "error": exc.to_json()}

    final = result.final
    if final is None:
        return {"sample": name, "ok": False, "error": {"code": "EMPTY", "message": "no output"}}

    checks = [
        {"feature": item.feature_id, "name": check.name, "ok": check.ok,
         "hint": check.hint}
        for item in result.features for check in item.checks
    ]
    failed = [check for check in checks if not check["ok"]]
    report: dict = {
        "sample": name,
        "ok": False,
        "features": len(result.features),
        "faces": len(final.faces()),
        "volume": round(float(final.volume), 1),
        "closed": bool(final.mesh().is_closed()),
        "checks": checks,
        "seconds": round(result.seconds, 2),
    }
    if failed:
        report["error"] = {"code": "CHECK_FAILED", "message": f"{len(failed)} check(s) failed",
                          "checks": failed}
        return report
    if not report["closed"] or report["volume"] <= 0:
        report["error"] = {"code": "NOT_A_SOLID",
                           "message": f"closed={report['closed']} volume={report['volume']}"}
        return report

    from cadwork.service.export import export_bytes

    folder = os.path.join(out_dir, name)
    os.makedirs(folder, exist_ok=True)
    written: list[str] = []
    for fmt in ("step", "stl"):
        payload, _media = export_bytes(final, fmt)
        path = os.path.join(folder, f"{name}.{fmt}")
        with open(path, "wb") as handle:
            handle.write(payload)
        written.append(path)
        if len(payload) < 1024:
            report["error"] = {"code": "EXPORT_TOO_SMALL",
                               "message": f"{fmt} is only {len(payload)} bytes"}
            return report

    if render:
        from cadwork.service.render import render_png

        png = render_png(final, view="iso")
        path = os.path.join(folder, f"{name}.png")
        with open(path, "wb") as handle:
            handle.write(png)
        written.append(path)
        if len(png) < 1024:
            report["error"] = {"code": "RENDER_TOO_SMALL",
                               "message": f"png is only {len(png)} bytes"}
            return report

    report["files"] = written
    report["wall_seconds"] = round(time.perf_counter() - started, 2)
    report["ok"] = True
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and prove one or more sample parts.")
    parser.add_argument("--sample", default="volute", choices=sorted(SAMPLES))
    parser.add_argument("--all", action="store_true", help="check every registered sample")
    parser.add_argument("--out", default=os.path.join(".tmp", "accept"))
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    names = sorted(SAMPLES) if args.all else [args.sample]
    reports = [_check_sample(name, args.out, not args.no_render) for name in names]
    ok = all(item["ok"] for item in reports)

    if args.json:
        print(json.dumps({"ok": ok, "reports": reports}, ensure_ascii=False, indent=2))
    else:
        for item in reports:
            if item["ok"]:
                print(f"ok   {item['sample']:9} {item['features']} features · "
                      f"{item['faces']} faces · {item['volume']} mm³ · "
                      f"{item['seconds']}s · {len(item['checks'])} checks")
                for path in item.get("files", []):
                    print(f"     wrote {path}")
            else:
                error = item.get("error", {})
                print(f"FAIL {item['sample']:9} {error.get('code')}: {error.get('message')}")
                for check in error.get("checks", []):
                    print(f"     {check['feature']}.{check['name']}: {check.get('hint')}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
