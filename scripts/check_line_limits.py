"""Line count threshold enforcement gate for BrepX codebase."""

from __future__ import annotations

import os
import sys

BACKEND_LIMIT = 400
FRONTEND_LIMIT = 350

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


def check_file(path: str, limit: int) -> bool:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        count = sum(1 for _ in f)
    if count > limit:
        print(f"FAIL: {path}: {count} lines (limit {limit})")
        return False
    return True


def run() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    violations = 0

    backend_dir = os.path.join(root, "backend")
    if os.path.exists(backend_dir):
        for dirpath, dirnames, filenames in os.walk(backend_dir):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fname in filenames:
                if fname.endswith(".py"):
                    full_path = os.path.join(dirpath, fname)
                    rel_path = os.path.relpath(full_path, root)
                    if not check_file(full_path, BACKEND_LIMIT):
                        violations += 1

    static_js_dir = os.path.join(root, "static", "js")
    if os.path.exists(static_js_dir):
        for dirpath, dirnames, filenames in os.walk(static_js_dir):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fname in filenames:
                if fname.endswith(".js"):
                    full_path = os.path.join(dirpath, fname)
                    rel_path = os.path.relpath(full_path, root)
                    if not check_file(full_path, FRONTEND_LIMIT):
                        violations += 1

    app_js = os.path.join(root, "static", "app.js")
    if os.path.exists(app_js):
        if not check_file(app_js, FRONTEND_LIMIT):
            violations += 1

    if violations > 0:
        print(f"\nLine limit gate failed with {violations} violation(s).")
        return 1

    print("OK: Line limits verified.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
