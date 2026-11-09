"""Fast aggregated quality gate runner for BrepX codebase."""

from __future__ import annotations

import subprocess
import sys
import time

GATES = [
    ("Line limits", ["python", "scripts/check_line_limits.py"]),
    ("No suppression", ["python", "scripts/check_no_suppression.py"]),
    ("Architecture boundaries", ["python", "scripts/check_architecture.py"]),
    ("Comment integrity", ["python", "scripts/check_comment_rules.py"]),
    ("Unit tests", ["python", "-m", "unittest", "discover", "-s", "tests"]),
]


def run() -> int:
    start = time.perf_counter()
    failed = False

    for name, cmd in GATES:
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print(f"FAILED GATE: {name}")
            failed = True
            break

    elapsed = time.perf_counter() - start
    print(f"\nAll gates completed in {elapsed:.2f}s")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
