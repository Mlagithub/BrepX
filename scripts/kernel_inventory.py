"""Generate or check the smlibpy kernel inventory artifacts.

Usage::

    python scripts/kernel_inventory.py --check   # fail if any callable is unclassified
    python scripts/kernel_inventory.py --write   # regenerate the markdown inventory and the baseline JSON
    python scripts/kernel_inventory.py --check --write

``--write`` refuses to generate artifacts while any public callable is still
unclassified, so the baseline can never hide a kernel addition.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cadwork.design import kernel_inventory

DOCS_PATH = ROOT / "docs" / "kernel-inventory.md"
BASELINE_PATH = ROOT / "cadwork" / "design" / "kernel_actions.baseline.json"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_outputs() -> int:
    """Write the generated documentation and the baseline JSON."""

    missing = kernel_inventory.unclassified()
    if missing:
        print(f"refusing to write: {len(missing)} unclassified callable(s):")
        for record in missing:
            print(f"  {record['owner']}.{record['name']}")
        return 1

    _write(DOCS_PATH, kernel_inventory.render_markdown())
    _write(BASELINE_PATH, kernel_inventory.baseline_json())
    counts = kernel_inventory.destination_counts()
    summary = ", ".join(
        f"{destination}={counts[destination]}"
        for destination in kernel_inventory.DESTINATIONS
        if counts[destination]
    )
    print(f"wrote {DOCS_PATH.relative_to(ROOT)}")
    print(f"wrote {BASELINE_PATH.relative_to(ROOT)}")
    print(f"smlibpy {kernel_inventory.kernel_version()}: {summary}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/kernel_inventory.py",
        description="Check or regenerate the smlibpy kernel inventory.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when any public callable is unclassified",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="regenerate the markdown inventory and the baseline JSON",
    )
    args = parser.parse_args(argv)
    if not (args.check or args.write):
        parser.print_help()
        return 2

    status = 0
    if args.write:
        status = write_outputs()
    if args.check:
        print("kernel inventory check")
        check_status = kernel_inventory.check()
        status = status or check_status
    return status


if __name__ == "__main__":
    raise SystemExit(main())
