"""Install the cad-agent profile and the CAD skills into a dsh home.

    python agent/install.py [--home C:\\Users\\me\\.dsh] [--force] [--no-smlibpy]

Copies the profile (package.json + cordis.patch.yml) and every skill directory
under ``agent/skills`` into ``$DSH_HOME/skills``.  With ``--force`` it also
refreshes the vendored smlibpy reference tree from the installed wheel.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _copy_file(source: Path, target: Path, force: bool, copied: list[Path]) -> None:
    if target.exists() and not force:
        print(f"exists, skipped: {target} (use --force to overwrite)")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    copied.append(target)


def _copy_tree(source: Path, target: Path, force: bool, copied: list[Path]) -> None:
    if target.exists() and not force:
        print(f"exists, skipped: {target} (use --force to overwrite)")
        return
    shutil.copytree(source, target, dirs_exist_ok=True)
    copied.append(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install the cadwork dsh profile.")
    parser.add_argument("--home", default=os.environ.get("DSH_HOME"),
                        help="dsh home (default: $DSH_HOME or ~/.dsh)")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-smlibpy", action="store_true",
                        help="do not copy the smlibpy skill from the installed wheel")
    args = parser.parse_args(argv)

    home = Path(args.home) if args.home else Path.home() / ".dsh"
    profile = home / "profiles" / "cad-agent"
    profile.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    for name in ("package.json", "cordis.patch.yml"):
        _copy_file(HERE / "profile" / name, profile / name, args.force, copied)

    skills_root = home / "skills"
    for source in sorted((HERE / "skills").iterdir()):
        if source.is_dir() and (source / "SKILL.md").is_file():
            _copy_tree(source, skills_root / source.name, args.force, copied)

    if not args.no_smlibpy:
        spec = importlib.util.find_spec("smlibpy")
        if spec is None or spec.origin is None:
            print("warning: smlibpy is not installed in this Python; skill references not copied")
        else:
            vendor = Path(spec.origin).parent / "skill"
            if (vendor / "SKILL.md").is_file():
                _copy_tree(vendor, skills_root / "smlibpy", args.force, copied)
            else:
                print(f"warning: {vendor} has no SKILL.md; skill references not copied")

    for path in copied:
        print(f"installed: {path}")
    print()
    print("next:")
    print("  1. start the CAD service:  python -m cadwork.service --port 8765")
    print("  2. start the agent:        dsh --profile cad-agent")
    print("  check the profile:         dsh --profile cad-agent --dump-config")
    print("  list installed skills:     ls $DSH_HOME/skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
