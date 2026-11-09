"""Session coordinator and wiring root for BrepX application."""

from __future__ import annotations

from typing import Any

import backend.kernel.ops_cfd
import backend.kernel.ops_features
import backend.kernel.ops_patterns
import backend.kernel.ops_primitives
import backend.kernel.ops_surfaces
import backend.kernel.ops_transforms
import backend.kernel.ops_turbomachinery
from backend.adapters.viewport.projector import project_scene
from backend.core.command import Command
from backend.core.design import Design
from backend.core.pipeline import redo as pipeline_redo
from backend.core.pipeline import submit as pipeline_submit
from backend.core.pipeline import undo as pipeline_undo
from backend.core.rebuild import RebuildResult, rebuild
from backend.kernel.registry import OperatorRegistry, default_registry
from backend.query.builder import BodyInfo, build_body


class Session:
    def __init__(self, registry: OperatorRegistry | None = None) -> None:
        self.registry = registry if registry is not None else default_registry()
        self.design = Design.empty()

    def submit(self, cmd: Command) -> Design:
        self.design = pipeline_submit(self.design, cmd, self.registry)
        return self.design

    def undo(self) -> Design:
        self.design = pipeline_undo(self.design, self.registry)
        return self.design

    def redo(self) -> Design:
        self.design = pipeline_redo(self.design, self.registry)
        return self.design

    def update_params(self, command_id: str, new_params: dict[str, Any]) -> RebuildResult:
        result = rebuild(self.design, command_id, self.registry, new_params=new_params)
        if result.ok and result.design is not None:
            self.design = result.design
        return result

    def query(self) -> BodyInfo:
        return build_body(self.design)

    def scene(self) -> dict[str, Any]:
        return project_scene(self.design)


session = Session()
