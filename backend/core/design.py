"""Design state container and version tracking conventions for BrepX supporting multi-body modeling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.core.command import CommandRecord
from backend.core.snapshot import SnapshotStore

INITIAL_VERSION = 1


def next_version(current: int) -> int:
    return current + 1


@dataclass
class Design:
    version: int
    journal: list[CommandRecord] = field(default_factory=list)
    snapshots: SnapshotStore = field(default_factory=SnapshotStore)
    patches: list[Any] = field(default_factory=list)
    geometry: Any | None = None
    bodies: dict[str, Any] = field(default_factory=dict)
    active_body_id: str | None = None

    @classmethod
    def empty(cls) -> Design:
        return cls(
            version=INITIAL_VERSION,
            journal=[],
            snapshots=SnapshotStore(),
            patches=[],
            geometry=None,
            bodies={},
            active_body_id=None,
        )

    @classmethod
    def with_geometry(cls, part: Any, body_id: str = "body_1") -> Design:
        store = SnapshotStore()
        store.put(INITIAL_VERSION, part)
        bodies = {body_id: part} if part is not None else {}
        return cls(
            version=INITIAL_VERSION,
            journal=[],
            snapshots=store,
            patches=[],
            geometry=part,
            bodies=bodies,
            active_body_id=body_id if part is not None else None,
        )

    def get_body(self, body_id: str | None = None) -> Any | None:
        if body_id is not None:
            return self.bodies.get(body_id)
        if self.active_body_id and self.active_body_id in self.bodies:
            return self.bodies[self.active_body_id]
        if self.geometry is not None:
            return self.geometry
        if self.bodies:
            return next(iter(self.bodies.values()))
        return None
