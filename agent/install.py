"""Install the cad-agent profile and the impeller skill into a dsh home.

    python agent/install.py [--home C:\\Users\\me\\.dsh] [--force]
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install the cadwork dsh profile.")
    parser.add_argument("--home", default=os.environ.get("DSH_HOME"),
                        help="dsh home (default: $DSH_HOME or ~/.dsh)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    home = Path(args.home) if args.home else Path.home() / ".dsh"
    profile = home / "profiles" / "cad-agent"
    profile.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    for name in ("package.json", "cordis.patch.yml"):
        source = HERE / "profile" / name
        target = profile / name
        if target.exists() and not args.force:
            print(f"exists, skipped: {target} (use --force to overwrite)")
            continue
        shutil.copy2(source, target)
        copied.append(target)

    skill_source = HERE / "skills" / "impeller" / "SKILL.md"
    skill_target = home / "skills" / "impeller" / "SKILL.md"
    if skill_source.exists():
        skill_target.parent.mkdir(parents=True, exist_ok=True)
        if not skill_target.exists() or args.force:
            shutil.copy2(skill_source, skill_target)
            copied.append(skill_target)

    for path in copied:
        print(f"installed: {path}")
    print()
    print("next:")
    print("  1. start the CAD service:  python -m cadwork.service --port 8765")
    print("  2. start the agent:        dsh --profile cad-agent")
    print("  check the profile:         dsh --profile cad-agent --dump-config")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
