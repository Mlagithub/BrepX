"""Version history stack and milestone navigation for parametric documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .document import (
    Document,
    DocumentError,
    document_from_json,
    document_to_json,
)

_MAX_SNAPSHOTS = 50


@dataclass
class HistoryStack:
    """In-memory or serialisable snapshot stack supporting arbitrary version jumps."""

    snapshots: list[dict[str, Any]] = field(default_factory=list)

    def push(self, document: Document) -> None:
        payload = document_to_json(document)
        self.snapshots = [
            item for item in self.snapshots if int(item.get("version", 0)) != document.version
        ]
        self.snapshots.append(payload)
        if len(self.snapshots) > _MAX_SNAPSHOTS:
            self.snapshots = self.snapshots[-_MAX_SNAPSHOTS:]

    def get_version(self, version: int) -> Document:
        for item in reversed(self.snapshots):
            if int(item.get("version", 0)) == version:
                return document_from_json(item)
        raise DocumentError("VERSION_NOT_FOUND", f"no snapshot at version {version}")

    def revert_to(self, current: Document, target_version: int) -> Document:
        if current.version == target_version:
            return current
        target = self.get_version(target_version)
        self.snapshots = [
            item for item in self.snapshots if int(item.get("version", 0)) < target_version
        ]
        return target

    def list_versions(self) -> list[int]:
        return sorted(int(item.get("version", 0)) for item in self.snapshots)

    def to_json(self) -> list[dict[str, Any]]:
        return list(self.snapshots)

    @classmethod
    def from_json(cls, payload: list[Mapping[str, Any]] | None) -> "HistoryStack":
        if not payload:
            return cls()
        return cls([dict(item) for item in payload])
