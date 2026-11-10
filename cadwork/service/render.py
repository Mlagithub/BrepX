"""Render out of process: three renders in one process slow later builds 5x."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
_TIMEOUT_S = 180


def render_png(part: Any, view: str = "iso", size: tuple[int, int] = (900, 700)) -> bytes:
    from cadwork import smlib as S

    with tempfile.TemporaryDirectory() as folder:
        step_path = os.path.join(folder, "model.step")
        out_path = os.path.join(folder, "view.png")
        S.export_step(part, step_path)
        command = [
            sys.executable, "-m", "cadwork.service.render_worker",
            "--step", step_path, "--out", out_path, "--view", view,
            "--width", str(size[0]), "--height", str(size[1]),
        ]
        completed = subprocess.run(
            command, cwd=str(_ROOT), capture_output=True, text=True, timeout=_TIMEOUT_S,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()[-400:]
            raise RuntimeError(f"render worker failed: {detail}")
        return Path(out_path).read_bytes()
