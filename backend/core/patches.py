"""CFD physical boundary patch data structures, storage, and rebinding."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from backend.selector.errors import SelectorResolutionError
from backend.selector.resolver import SelectorResolver

VALID_SEMANTIC_TYPES = {
    "inlet",
    "outlet",
    "wall",
    "symmetry",
    "interface",
    "internal",
}

SEMANTIC_TYPE_COLORS = {
    "inlet": "#3a86ff",
    "outlet": "#ff006e",
    "wall": "#8d99ae",
    "symmetry": "#06d6a0",
    "interface": "#fb5607",
    "internal": "#ffbe0b",
}


@dataclass(frozen=True)
class BoundaryPatch:
    patch_id: str
    name: str
    semantic_type: str
    selector_expr: str
    color_hex: str
    area: float = 0.0

    def __post_init__(self) -> None:
        if self.semantic_type not in VALID_SEMANTIC_TYPES:
            raise ValueError(
                f"Invalid semantic_type '{self.semantic_type}'. Allowed types: {sorted(VALID_SEMANTIC_TYPES)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PatchStore:
    def __init__(self) -> None:
        self._patches: dict[str, BoundaryPatch] = {}

    def add(self, patch: BoundaryPatch) -> None:
        existing_to_remove = [
            pid for pid, p in self._patches.items()
            if p.selector_expr == patch.selector_expr and pid != patch.patch_id
        ]
        for pid in existing_to_remove:
            self._patches.pop(pid, None)

        self._patches[patch.patch_id] = patch

    def remove(self, patch_id: str) -> None:
        self._patches.pop(patch_id, None)

    def get(self, patch_id: str) -> BoundaryPatch | None:
        return self._patches.get(patch_id)

    def all(self) -> list[BoundaryPatch]:
        return sorted(self._patches.values(), key=lambda p: p.patch_id)

    def clear(self) -> None:
        self._patches.clear()

    def __len__(self) -> int:
        return len(self._patches)


def create_patch(
    patch_id: str,
    name: str,
    semantic_type: str,
    selector_expr: str,
    area: float = 0.0,
) -> BoundaryPatch:
    color = SEMANTIC_TYPE_COLORS.get(semantic_type, "#8d99ae")
    return BoundaryPatch(
        patch_id=patch_id,
        name=name,
        semantic_type=semantic_type,
        selector_expr=selector_expr,
        color_hex=color,
        area=round(float(area), 4),
    )


def rebind(store: PatchStore, part: Any) -> tuple[PatchStore, list[str]]:
    new_store = PatchStore()
    failed_patches: list[str] = []

    if part is None:
        return new_store, [p.name for p in store.all()]

    for patch in store.all():
        try:
            resolved_face = SelectorResolver.resolve(part, patch.selector_expr)
            face_area = round(float(getattr(resolved_face, "area", 0.0)), 4)
            updated_patch = BoundaryPatch(
                patch_id=patch.patch_id,
                name=patch.name,
                semantic_type=patch.semantic_type,
                selector_expr=patch.selector_expr,
                color_hex=patch.color_hex,
                area=face_area,
            )
            new_store.add(updated_patch)
        except SelectorResolutionError:
            failed_patches.append(patch.name)
            new_store.add(patch)

    return new_store, failed_patches
