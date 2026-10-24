"""Unified Workspace Session Engine for BrepX.

Maintains the persistent Python modeling namespace, AST security sandbox,
history steps, Undo/Redo stack, and Adjust Last Operation replay.
"""

from __future__ import annotations

import ast
import os
import tempfile
import time
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any

import smlibpy
from smlibpy import Edge, Face, Part, Shape, ShapeList, Shell, Sketch, StepModel, Vertex, Wire

from .brep_graphic import serialize_scene

ALLOWED_IMPORTS = {"smlibpy", "math", "numpy"}
FORBIDDEN_CALLS = {
    "eval", "exec", "compile", "__import__", "open", "input",
    "getattr", "setattr", "delattr", "globals", "locals", "vars",
}
FORBIDDEN_ATTRS = {
    "__subclasses__", "__bases__", "__globals__", "__code__",
    "__closure__", "__builtins__", "__dict__", "system", "popen",
}

TEMP_EXPORT_DIR = os.path.join(tempfile.gettempdir(), "smlib_studio_next")
os.makedirs(TEMP_EXPORT_DIR, exist_ok=True)


class SecurityViolationError(ValueError):
    """Raised when user or Agent code violates the AST sandbox policy."""


def validate_code_ast(code: str) -> ast.Module:
    """Parse and audit Python code against the AST security whitelist."""
    try:
        tree = ast.parse(code, filename="<workspace>", mode="exec")
    except SyntaxError as exc:
        raise ValueError(f"语法错误 (line {exc.lineno}): {exc.msg}") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_mod = alias.name.split(".")[0]
                if root_mod not in ALLOWED_IMPORTS:
                    raise SecurityViolationError(f"安全沙盒拦截: 禁止导入模块 '{alias.name}'")
        elif isinstance(node, ast.ImportFrom):
            mod_name = (node.module or "").split(".")[0]
            if mod_name not in ALLOWED_IMPORTS:
                raise SecurityViolationError(f"安全沙盒拦截: 禁止从模块 '{node.module}' 导入")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                raise SecurityViolationError(f"安全沙盒拦截: 禁止调用内置函数 '{node.func.id}()'")
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRS:
                raise SecurityViolationError(f"安全沙盒拦截: 禁止访问受限属性 '{node.attr}'")
    return tree


@dataclass
class HistoryStep:
    step_id: str
    label: str
    code: str
    operator_id: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    selections: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0


class WorkspaceSession:
    """Single source of truth for CAD geometry state, history, and B-Rep scene."""

    def __init__(self) -> None:
        self.ns: dict[str, Any] = {}
        self.shown_names: list[str] | None = None
        self.history: list[HistoryStep] = []
        self.redo_stack: list[HistoryStep] = []
        self.last_compute_ms: float = 0.0
        self._reset_namespace()

    def _reset_namespace(self) -> None:
        self.ns = {"__name__": "__workspace__", "__builtins__": __builtins__}
        exec("from smlibpy import *\nimport math\nimport numpy as np", self.ns)
        self.ns["show"] = self._show_hook
        self.shown_names = None

    def _show_hook(self, *shapes: Any, **_kwargs: Any) -> None:
        names: list[str] = []
        for s in shapes:
            for k, v in self.ns.items():
                if v is s and not k.startswith("_"):
                    names.append(k)
        self.shown_names = names or None

    def clear(self) -> None:
        """Reset workspace to an empty scene."""
        self._reset_namespace()
        self.history.clear()
        self.redo_stack.clear()
        self.last_compute_ms = 0.0

    def _rebuild_from_history(self, steps: list[HistoryStep]) -> None:
        """Replay a sequence of validated history steps from a clean namespace."""
        self._reset_namespace()
        for step in steps:
            tree = validate_code_ast(step.code)
            exec(compile(tree, "<workspace>", "exec"), self.ns)

    def execute_step(
        self,
        code: str,
        label: str = "Script Execution",
        operator_id: str | None = None,
        params: dict[str, Any] | None = None,
        selections: list[str] | None = None,
        replace_all: bool = False,
    ) -> dict[str, Any]:
        """Validate and execute a modeling step, recording it in history."""
        code = code.strip()
        if not code:
            raise ValueError("执行的建模代码不能为空")

        tree = validate_code_ast(code)
        t0 = time.perf_counter()

        prev_history = list(self.history)
        try:
            if replace_all:
                self._reset_namespace()
                self.history.clear()
            exec(compile(tree, "<workspace>", "exec"), self.ns)
            items = self.active_items()
            if not items:
                raise ValueError("执行后未生成有效的几何对象（请将模型赋值给 `part` 或其他几何变量）")
            # Validate manifold solid integrity for Parts
            for _, _, obj in items:
                if isinstance(obj, Part) and not obj.is_valid():
                    raise ValueError("生成的实体未通过流形封闭性检验 (non-manifold or invalid solid)")
        except Exception as exc:
            self._rebuild_from_history(prev_history)
            self.history = prev_history
            raise ValueError(f"{type(exc).__name__}: {exc}") from exc

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        self.last_compute_ms = elapsed_ms
        step = HistoryStep(
            step_id=f"step_{uuid.uuid4().hex[:8]}",
            label=label,
            code=code,
            operator_id=operator_id,
            params=params or {},
            selections=selections or [],
            elapsed_ms=elapsed_ms,
        )
        self.history.append(step)
        self.redo_stack.clear()
        return self.get_state()

    def adjust_last_step(
        self,
        new_code: str,
        new_params: dict[str, Any],
        label: str | None = None,
    ) -> dict[str, Any]:
        """Roll back the last step and re-execute with updated operator parameters (Blender F9)."""
        if not self.history:
            raise ValueError("当前没有可微调的上一步操作")

        last = self.history[-1]
        base_steps = self.history[:-1]
        tree = validate_code_ast(new_code)

        t0 = time.perf_counter()
        try:
            self._rebuild_from_history(base_steps)
            exec(compile(tree, "<workspace>", "exec"), self.ns)
            items = self.active_items()
            if not items:
                raise ValueError("参数微调后未产生有效几何体")
            for _, _, obj in items:
                if isinstance(obj, Part) and not obj.is_valid():
                    raise ValueError("该参数值导致几何拓扑自交或无效，请尝试更合理的数值")
        except Exception as exc:
            self._rebuild_from_history(base_steps + [last])
            raise ValueError(f"参数调整失败: {exc}") from exc

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        self.last_compute_ms = elapsed_ms
        last.code = new_code.strip()
        last.params = new_params
        if label:
            last.label = label
        last.elapsed_ms = elapsed_ms
        return self.get_state()

    def undo(self) -> dict[str, Any]:
        """Undo the most recent modeling step."""
        if len(self.history) <= 1:
            raise ValueError("已到达初始状态，无法继续撤销")
        popped = self.history.pop()
        self.redo_stack.append(popped)
        self._rebuild_from_history(self.history)
        return self.get_state()

    def redo(self) -> dict[str, Any]:
        """Redo the most recently undone modeling step."""
        if not self.redo_stack:
            raise ValueError("没有可重做的操作")
        step = self.redo_stack.pop()
        self.history.append(step)
        self._rebuild_from_history(self.history)
        return self.get_state()

    def active_items(self) -> list[tuple[str, str, Any]]:
        """Return (name, expr, shape) of active geometry objects in the workspace.

        If `part` exists, it is prioritized as the primary active body alongside
        any active sketches (`sketch*`), preventing intermediate helper variables
        (like `base`, `cut_out`, `bore`) from cluttering the viewport.
        """
        if self.shown_names:
            out = []
            for n in self.shown_names:
                if n in self.ns and isinstance(self.ns[n], Shape):
                    out.append((n, n, self.ns[n]))
            if out:
                return out

        if "part" in self.ns and isinstance(self.ns["part"], (Part, Shell, Sketch)):
            result: list[tuple[str, str, Any]] = [("part", "part", self.ns["part"])]
            for k, v in self.ns.items():
                if k.startswith("sketch") and isinstance(v, (Sketch, Wire, Edge)) and v is not self.ns["part"]:
                    result.append((k, k, v))
            return result

        # Fallback: find the last defined Part/Shell/Sketch
        candidates: list[tuple[str, str, Any]] = []
        for k, v in self.ns.items():
            if k.startswith("_") or k in ("X", "Y", "Z") or isinstance(v, type):
                continue
            if isinstance(v, (Part, Shell, Sketch, Wire, Edge)):
                candidates.append((k, k, v))
            elif isinstance(v, ShapeList) and len(v) > 0:
                for i, s in enumerate(v):
                    if isinstance(s, (Part, Shell)):
                        candidates.append((f"{k}_{i}", f"{k}[{i}]", s))
        return candidates[-1:] if candidates else []

    def primary_part(self) -> Part | Shell | Sketch | None:
        items = self.active_items()
        if not items:
            return None
        return items[0][2]

    def full_script(self) -> str:
        """Compile the full reproducible Python script from history steps."""
        lines = ["from smlibpy import *", "import math", ""]
        for idx, step in enumerate(self.history, 1):
            clean = "\n".join(
                ln for ln in step.code.splitlines()
                if not ln.strip().startswith("from smlibpy import") and ln.strip() != "import math"
            ).strip()
            if clean:
                lines.append(f"# --- Step {idx}: {step.label} ---")
                lines.append(clean)
                lines.append("")
        return "\n".join(lines).strip() + "\n"

    def evaluate_expression(self, expr: str) -> Any:
        """Safely evaluate a topological expression (e.g. 'part.faces()[2]') in the workspace."""
        validate_code_ast(expr)
        return eval(expr, self.ns)

    def get_state(self) -> dict[str, Any]:
        """Build the complete workspace state including serialized B-Rep containers and history."""
        items = self.active_items()
        scene_data = serialize_scene(items)
        last_step = self.history[-1] if self.history else None

        return {
            "ok": True,
            "scene": scene_data,
            "script": self.full_script(),
            "compute_ms": self.last_compute_ms,
            "can_undo": len(self.history) > 1,
            "can_redo": len(self.redo_stack) > 0,
            "history": [
                {
                    "step_id": s.step_id,
                    "label": s.label,
                    "operator_id": s.operator_id,
                    "params": s.params,
                    "elapsed_ms": s.elapsed_ms,
                }
                for s in self.history
            ],
            "last_operation": {
                "step_id": last_step.step_id,
                "label": last_step.label,
                "operator_id": last_step.operator_id,
                "params": last_step.params,
                "selections": last_step.selections,
            } if last_step and last_step.operator_id else None,
        }

    def export_bytes(self, fmt: str) -> tuple[bytes, str, str]:
        """Export active geometry to STEP, STL, glTF, DXF, or Python script."""
        fmt = fmt.lower()
        if fmt == "py":
            return self.full_script().encode("utf-8"), "text/x-python", "model_script.py"

        part = self.primary_part()
        if part is None:
            raise ValueError("当前工作区没有可导出的几何模型")

        ext_map = {
            "step": (".step", "application/step"),
            "stp": (".step", "application/step"),
            "stl": (".stl", "model/stl"),
            "gltf": (".gltf", "model/gltf+json"),
            "dxf": (".dxf", "application/dxf"),
        }
        if fmt not in ext_map:
            raise ValueError(f"不支持的导出格式: {fmt}")

        ext_suffix, mime = ext_map[fmt]
        out_path = os.path.join(TEMP_EXPORT_DIR, f"export_{uuid.uuid4().hex[:8]}{ext_suffix}")
        try:
            if fmt == "dxf":
                target = part.section(smlibpy.Plane.XY) if isinstance(part, Part) else part
                smlibpy.export_dxf([target], out_path)
            else:
                part.export(out_path)
            with open(out_path, "rb") as f:
                data = f.read()
            return data, mime, f"smlib_model{ext_suffix}"
        finally:
            if os.path.exists(out_path):
                try:
                    os.remove(out_path)
                except OSError:
                    pass


workspace_session = WorkspaceSession()
