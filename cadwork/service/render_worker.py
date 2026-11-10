"""Render worker: imports a STEP file and writes a PNG. One process, one image."""

from __future__ import annotations

import argparse
import sys

from cadwork import smlib as S


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a STEP file to PNG.")
    parser.add_argument("--step", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--view", default="iso")
    parser.add_argument("--width", type=int, default=900)
    parser.add_argument("--height", type=int, default=700)
    parser.add_argument("--section", default=None, help="XZ | XY | YZ")
    parser.add_argument("--zebra", action="store_true")
    args = parser.parse_args(argv)

    part = S.import_step(args.step)
    options: dict = {
        "path": args.out,
        "view": args.view,
        "size": (args.width, args.height),
    }
    if args.section:
        options["section"] = getattr(S.Plane, args.section.upper())
    if args.zebra:
        options["zebra"] = True
    S.render(part, **options)
    return 0


if __name__ == "__main__":
    sys.exit(main())
