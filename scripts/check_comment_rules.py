"""Comment integrity enforcement gate for BrepX codebase."""

from __future__ import annotations

import os
import re
import sys

TARGET_DIRS = ["backend", "tests", "static/js"]
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

FORBIDDEN_COMMENT_PATTERNS = [
    (r"\bADR-\d+\b", "ADR reference in comment"),
    (r"\bSPEC-\w+\b", "SPEC reference in comment"),
    (r"\b(?:PR|Pull Request)\s*#\d+\b", "PR reference in comment"),
    (r"\b(?:Issue)\s*#\d+\b", "Issue reference in comment"),
    (r"https?://\S+", "External URL link in comment"),
    (r"\b(?:Step|Phase)\s*\d+\b", "Procedural step or phase marker in comment"),
    (r"\b(?:TODO|FIXME|HACK|XXX)\b", "Task planning marker in comment"),
]


def extract_comments_python(path: str) -> list[tuple[int, str]]:
    comments: list[tuple[int, str]] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for idx, line in enumerate(f, start=1):
            stripped = line.strip()
            if "#" in stripped:
                comment_part = stripped[stripped.index("#") :]
                comments.append((idx, comment_part))
    return comments


def extract_comments_js(path: str) -> list[tuple[int, str]]:
    comments: list[tuple[int, str]] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for idx, line in enumerate(f, start=1):
            stripped = line.strip()
            if "//" in stripped:
                comment_part = stripped[stripped.index("//") :]
                comments.append((idx, comment_part))
            elif "/*" in stripped:
                comment_part = stripped[stripped.index("/*") :]
                comments.append((idx, comment_part))
    return comments


def scan_file(path: str) -> list[str]:
    violations: list[str] = []
    if path.endswith(".py"):
        comments = extract_comments_python(path)
    elif path.endswith(".js"):
        comments = extract_comments_js(path)
    else:
        return violations

    for line_no, text in comments:
        for pattern, desc in FORBIDDEN_COMMENT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(f"{path}:{line_no}: {desc} -> {text.strip()}")
    return violations


def run() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    this_script = os.path.abspath(__file__)
    all_violations: list[str] = []

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
                all_violations.extend(scan_file(full_path))

    for tfile in TARGET_FILES:
        full_path = os.path.join(root, tfile.replace("/", os.sep))
        if os.path.exists(full_path):
            all_violations.extend(scan_file(full_path))

    if all_violations:
        print("FAIL: Comment integrity violations detected:")
        for v in all_violations:
            print(f"  {v}")
        return 1

    print("OK: Comment integrity verified.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
