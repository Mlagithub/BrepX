"""Suppression and empty stub detection gate for BrepX codebase."""

from __future__ import annotations

import os
import re
import sys

TARGET_DIRS = ["backend", "tests", "scripts", "static/js"]
TARGET_FILES = ["static/app.js"]

EXCLUDE_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    "vendor",
    "utils",
    "__pycache__",
    "test_outputs",
}

PATTERNS = [
    (r"#\s*type:\s*ignore", "Type ignore suppression (# type: ignore)"),
    (r"#\s*noqa", "Linter suppression (# noqa)"),
    (r"@ts-ignore", "TypeScript suppression (@ts-ignore)"),
    (r"eslint-disable", "ESLint suppression (eslint-disable)"),
    (r"raise\s+NotImplementedError", "Unimplemented stub (raise NotImplementedError)"),
    (r"except[^:]*:\s*pass\b", "Silent exception swallow (except: pass)"),
    (r"catch\s*\([^)]*\)\s*\{\s*\}", "Silent catch swallow (catch {})"),
]


def scan_file(path: str) -> list[str]:
    findings: list[str] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    for pattern, desc in PATTERNS:
        matches = list(re.finditer(pattern, content))
        for m in matches:
            line_no = content.count("\n", 0, m.start()) + 1
            findings.append(f"{path}:{line_no}: {desc}")

    return findings


def run() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    this_script = os.path.abspath(__file__)
    all_findings: list[str] = []

    for tdir in TARGET_DIRS:
        full_dir = os.path.join(root, tdir.replace("/", os.sep))
        if not os.path.exists(full_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(full_dir):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fname in filenames:
                if not (fname.endswith(".py") or fname.endswith(".js")):
                    continue
                full_path = os.path.join(dirpath, fname)
                if os.path.abspath(full_path) == this_script:
                    continue
                all_findings.extend(scan_file(full_path))

    for tfile in TARGET_FILES:
        full_path = os.path.join(root, tfile.replace("/", os.sep))
        if os.path.exists(full_path):
            all_findings.extend(scan_file(full_path))

    if all_findings:
        print("FAIL: Suppression comments or stubs detected:")
        for finding in all_findings:
            print(f"  {finding}")
        return 1

    print("OK: No suppression comments or empty stubs found.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
