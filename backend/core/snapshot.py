"""In-memory LRU geometry snapshot store for incremental rebuild acceleration."""

from __future__ import annotations

from typing import Any

SNAPSHOT_EVERY = 5
MAX_SNAPSHOTS = 20


def should_snapshot(version: int) -> bool:
    if version == 1:
        return True
    return version % SNAPSHOT_EVERY == 0


class SnapshotStore:
    def __init__(self, capacity: int = MAX_SNAPSHOTS) -> None:
        self.capacity = capacity
        self._data: dict[int, Any] = {}
        self._order: list[int] = []

    def put(self, version: int, geometry: Any) -> None:
        if version in self._data:
            self._order.remove(version)
        elif len(self._order) >= self.capacity:
            oldest_ver = self._order.pop(0)
            self._data.pop(oldest_ver, None)

        self._data[version] = geometry
        self._order.append(version)

    def get_below(self, target_version: int) -> tuple[int, Any] | None:
        candidates = [v for v in self._data.keys() if v <= target_version]
        if not candidates:
            return None

        best_ver = max(candidates)
        self._order.remove(best_ver)
        self._order.append(best_ver)

        return best_ver, self._data[best_ver]

    def __len__(self) -> int:
        return len(self._data)

    def versions(self) -> list[int]:
        return sorted(self._data.keys())
