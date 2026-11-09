"""Architecture layering and boundary gate for BrepX codebase."""

from __future__ import annotations

import ast
import os
import re
import sys

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

FORBIDDEN_INDEX_LITERAL = re.compile(r"(faces\(\)\[|edges\(\)\[)")


def check_core_dependencies(core_dir: str) -> list[str]:
    violations: list[str] = []
    for dirpath, dirnames, filenames in os.walk(core_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(dirpath, fname)
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("smlibpy") or alias.name.startswith("backend.kernel"):
                            violations.append(
                                f"{path}:{node.lineno}: backend/core must not import {alias.name}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if mod.startswith("smlibpy") or mod.startswith("backend.kernel"):
                        violations.append(
                            f"{path}:{node.lineno}: backend/core must not import from {mod}"
                        )
    return violations


def check_agent_isolation(agent_dir: str) -> list[str]:
    violations: list[str] = []
    if not os.path.exists(agent_dir):
        return violations

    forbidden_prefixes = ("backend.core", "backend.kernel", "smlibpy")

    for dirpath, dirnames, filenames in os.walk(agent_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(dirpath, fname)
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(alias.name.startswith(p) for p in forbidden_prefixes):
                            violations.append(
                                f"{path}:{node.lineno}: Agent adapter must not import {alias.name}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if any(mod.startswith(p) for p in forbidden_prefixes):
                        violations.append(
                            f"{path}:{node.lineno}: Agent adapter must not import from {mod}"
                        )
    return violations


def check_operator_direct_calls(root: str) -> list[str]:
    violations: list[str] = []
    allowed_dirs = {
        os.path.abspath(os.path.join(root, "backend", "kernel")),
        os.path.abspath(os.path.join(root, "tests", "kernel")),
    }
    allowed_files = {
        os.path.abspath(os.path.join(root, "backend", "session.py")),
        os.path.abspath(os.path.join(root, "tests", "core", "test_pipeline.py")),
        os.path.abspath(os.path.join(root, "tests", "core", "test_rebuild.py")),
        os.path.abspath(os.path.join(root, "tests", "core", "test_snapshot.py")),
    }

    backend_dir = os.path.join(root, "backend")
    if not os.path.exists(backend_dir):
        return violations

    for dirpath, dirnames, filenames in os.walk(backend_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(dirpath, fname)
            abs_path = os.path.abspath(path)
            if any(abs_path.startswith(d) for d in allowed_dirs) or abs_path in allowed_files:
                continue

            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if "ops_" in alias.name:
                            violations.append(
                                f"{path}:{node.lineno}: Direct operator import '{alias.name}' forbidden outside kernel/session"
                            )
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if "ops_" in mod:
                        violations.append(
                            f"{path}:{node.lineno}: Direct operator import from '{mod}' forbidden outside kernel/session"
                        )
    return violations


def check_forbidden_index_syntax(root: str) -> list[str]:
    violations: list[str] = []
    backend_dir = os.path.join(root, "backend")
    if not os.path.exists(backend_dir):
        return violations

    for dirpath, dirnames, filenames in os.walk(backend_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(dirpath, fname)
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line_no, line in enumerate(f, start=1):
                    if FORBIDDEN_INDEX_LITERAL.search(line):
                        violations.append(
                            f"{path}:{line_no}: Forbidden raw integer index literal '{line.strip()}'"
                        )
    return violations


def run() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    violations: list[str] = []

    core_dir = os.path.join(root, "backend", "core")
    if os.path.exists(core_dir):
        violations.extend(check_core_dependencies(core_dir))

    agent_dir = os.path.join(root, "backend", "adapters", "agent")
    violations.extend(check_agent_isolation(agent_dir))

    violations.extend(check_operator_direct_calls(root))
    violations.extend(check_forbidden_index_syntax(root))

    if violations:
        print("FAIL: Architecture layering or isolation violations detected:")
        for v in violations:
            print(f"  {v}")
        return 1

    print("OK: Architecture layering and isolation constraints verified.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
