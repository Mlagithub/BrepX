"""Run the four acceptance criteria and print a transcript.

    python scripts/demo.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cadwork.service.acceptance import run_acceptance  # noqa: E402


def main() -> int:
    folder = tempfile.mkdtemp(prefix="cadwork-demo-")
    report = run_acceptance(folder)
    for step in report["steps"]:
        print(step)
    print(json.dumps({
        "ok": report["ok"],
        "folder": report["folder"],
        "final_version": report.get("final_version"),
    }, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
