"""Registration and lookup of domain packages."""

from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any

from .base import BriefSchema, DomainError, DomainPack, pack_to_json

_PACK_ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_VERSION = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]{0,63}$")


class DomainRegistry:
    """A small versioned registry; the active version is explicit."""

    def __init__(self) -> None:
        self._packs: OrderedDict[tuple[str, str], DomainPack] = OrderedDict()
        self._active: dict[str, str] = {}

    def register(self, pack: DomainPack, *, active: bool = True) -> None:
        pack_id = str(getattr(pack, "id", ""))
        version = str(getattr(pack, "version", ""))
        if not _PACK_ID.fullmatch(pack_id):
            raise DomainError("INVALID_DOMAIN_ID", f"invalid domain id {pack_id!r}")
        if not _VERSION.fullmatch(version):
            raise DomainError(
                "INVALID_DOMAIN_VERSION", f"invalid domain version {version!r}"
            )
        key = (pack_id, version)
        if key in self._packs:
            raise DomainError(
                "DOMAIN_ALREADY_REGISTERED",
                f"domain {pack_id!r} version {version!r} is already registered",
                status=409,
            )
        self._packs[key] = pack
        if active or pack_id not in self._active:
            self._active[pack_id] = version

    def get(self, pack_id: str, version: str | None = None) -> DomainPack:
        selected = version or self._active.get(pack_id)
        if not selected:
            raise DomainError(
                "DOMAIN_NOT_FOUND", f"unknown domain {pack_id!r}", status=404
            )
        pack = self._packs.get((pack_id, selected))
        if pack is None:
            raise DomainError(
                "DOMAIN_VERSION_NOT_FOUND",
                f"domain {pack_id!r} has no version {selected!r}",
                status=404,
            )
        return pack

    def has(self, pack_id: str, version: str | None = None) -> bool:
        try:
            self.get(pack_id, version)
        except DomainError:
            return False
        return True

    def list(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for pack_id, active_version in self._active.items():
            versions = sorted(
                version
                for candidate, version in self._packs
                if candidate == pack_id
            )
            pack = self._packs[(pack_id, active_version)]
            result.append(
                {
                    **pack_to_json(pack),
                    "active": True,
                    "versions": versions,
                }
            )
        return result

    def brief(self, pack_id: str, version: str | None = None) -> BriefSchema:
        return self.get(pack_id, version).brief_schema()

    def active_version(self, pack_id: str) -> str | None:
        return self._active.get(pack_id)

    def __len__(self) -> int:
        return len(self._packs)


def load_default_registry() -> DomainRegistry:
    """Register the shipped packages selected by ``CADWORK_DOMAIN_PACKS``."""
    import os

    registry = DomainRegistry()
    configured = os.environ.get("CADWORK_DOMAIN_PACKS", "aircraft")
    enabled = {
        item.strip().lower()
        for item in configured.split(",")
        if item.strip()
    }
    if "aircraft" in enabled:
        from .aircraft import AircraftPack

        registry.register(AircraftPack())
    return registry


default_registry = load_default_registry()
