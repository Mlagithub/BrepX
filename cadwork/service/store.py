"""JSON document store: one file per document, plus bounded undo history."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
import time
from pathlib import Path
from typing import Any

from cadwork.design.assembly import (
    AssemblyDocument,
    AssemblyRef,
    PartRef,
    assembly_document_from_json,
    assembly_document_to_json,
    new_assembly_document,
)
from cadwork.design.document import (
    Document,
    document_from_json,
    document_to_json,
    ensure_chain,
    new_document,
)
from cadwork.design.plan import ModelingPlan, plan_from_json, plan_to_json

from .preview_format import (
    PreviewFormatError,
    bundle_key as _bundle_key,
    decode_manifest,
    encode_manifest,
    validate_manifest,
)

_MAX_HISTORY = 100
_PREVIEW_KEY_PATTERN = re.compile(r"[0-9a-f]{64}")
_PREVIEW_BUILD_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")

_ATOMIC_REPLACE_ATTEMPTS = 24
_ATOMIC_REPLACE_INITIAL_DELAY = 0.002
_ATOMIC_REPLACE_MAX_DELAY = 0.05


def _replace_is_busy(exc: OSError) -> bool:
    """Whether a failed replace lost a race with an open reader.

    Windows reports the sharing violation as ERROR_ACCESS_DENIED (5) or
    ERROR_SHARING_VIOLATION (32) and maps both to PermissionError; keeping the
    explicit winerror check also covers platforms that surface a plain OSError.
    """
    return isinstance(exc, PermissionError) or getattr(exc, "winerror", None) in {
        5,
        32,
    }


def _replace_with_retry(temp: Path, path: Path) -> None:
    """Publish staged bytes, waiting out readers that temporarily block rename.

    Retrying is bounded so a genuinely denied destination still fails promptly
    instead of hanging a build thread; once the window is exhausted the original
    error is raised and the staging file is removed by the caller.
    """
    delay = _ATOMIC_REPLACE_INITIAL_DELAY
    for attempt in range(_ATOMIC_REPLACE_ATTEMPTS):
        try:
            os.replace(temp, path)
            return
        except OSError as exc:
            if not _replace_is_busy(exc) or attempt + 1 >= _ATOMIC_REPLACE_ATTEMPTS:
                raise
            time.sleep(delay)
            delay = min(_ATOMIC_REPLACE_MAX_DELAY, delay * 2)


class StoreError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class Store:
    """Documents on disk. Writes are atomic; history lets undo step back."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._preview_build_locks: dict[str, threading.Lock] = {}
        self.preview_cache_lock = threading.RLock()

    def _path(self, document_id: str) -> Path:
        return self.root / f"{document_id}.json"

    def _history_path(self, document_id: str) -> Path:
        return self.root / f"{document_id}.history.json"

    def _plan_path(self, document_id: str) -> Path:
        return self.root / f"{document_id}.plan.json"

    def _versions_dir(self, document_id: str) -> Path:
        return self.root / "versions" / document_id

    def _version_path(self, document_id: str, version: int) -> Path:
        return self._versions_dir(document_id) / f"{int(version)}.json"

    def _assembly_path(self, document_id: str) -> Path:
        return self.root / f"{document_id}.assembly.json"

    def _assembly_version_path(self, document_id: str, version: int) -> Path:
        return self._versions_dir(document_id) / f"assembly-{int(version)}.json"

    def _document_paths(self) -> list[Path]:
        """Only part document files; sidecars and assemblies have their own paths."""
        paths: list[Path] = []
        for path in self.root.glob("*.json"):
            if path.name.endswith(
                (".history.json", ".intents.json", ".plan.json", ".assembly.json")
            ):
                continue
            paths.append(path)
        return paths

    def _assembly_paths(self) -> list[Path]:
        return list(self.root.glob("*.assembly.json"))

    def _next_seq(self) -> int:
        """Creation order, independent of file timestamps (coarse on Windows)."""
        highest = 0
        for path in [*self._document_paths(), *self._assembly_paths()]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            highest = max(highest, int(payload.get("seq", 0) or 0))
        return highest + 1

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            entries: list[dict[str, Any]] = []
            for path in self._document_paths():
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                entries.append(
                    {
                        "id": payload.get("id", path.stem),
                        "name": payload.get("name", ""),
                        "version": payload.get("version", 1),
                        "features": len(payload.get("features") or []),
                        "instances": 0,
                        "kind": "part",
                        "seq": int(payload.get("seq", 0) or 0),
                    }
                )
            for path in self._assembly_paths():
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                entries.append(
                    {
                        "id": payload.get(
                            "id", path.name.removesuffix(".assembly.json")
                        ),
                        "name": payload.get("name", ""),
                        "version": payload.get("version", 1),
                        "features": 0,
                        "instances": len(payload.get("instances") or []),
                        "kind": "assembly",
                        "seq": int(payload.get("seq", 0) or 0),
                    }
                )
            entries.sort(key=lambda entry: entry["seq"], reverse=True)
            return entries

    def exists(self, document_id: str) -> bool:
        return self._path(document_id).exists()

    def delete(self, document_id: str) -> None:
        with self._lock:
            path = self._path(document_id)
            assembly_path = self.root / f"{document_id}.assembly.json"
            if not path.exists() and not assembly_path.exists():
                raise StoreError(
                    "NOT_FOUND", f"no document {document_id!r}", status=404
                )
            path.unlink(missing_ok=True)
            assembly_path.unlink(missing_ok=True)
            self._history_path(document_id).unlink(missing_ok=True)
            self._plan_path(document_id).unlink(missing_ok=True)
            shutil.rmtree(self._versions_dir(document_id), ignore_errors=True)

    def get(self, document_id: str) -> Document:
        with self._lock:
            path = self._path(document_id)
            if not path.exists():
                raise StoreError(
                    "NOT_FOUND", f"no document {document_id!r}", status=404
                )
            try:
                document = ensure_chain(
                    document_from_json(json.loads(path.read_text(encoding="utf-8")))
                )
            except (OSError, json.JSONDecodeError) as exc:
                raise StoreError(
                    "CORRUPT", f"cannot read {document_id}: {exc}", status=500
                ) from exc
            self._write_version(document)
            return document

    def create(self, name: str = "Untitled") -> Document:
        with self._lock:
            document = new_document(name, seq=self._next_seq())
            while self.exists(document.id):
                document = new_document(name, seq=document.seq)
            self._write(document)
            return document

    def exists_assembly(self, assembly_id: str) -> bool:
        return self._assembly_path(assembly_id).exists()

    def create_assembly(self, name: str = "Untitled") -> AssemblyDocument:
        with self._lock:
            document = new_assembly_document(name, seq=self._next_seq())
            while self.exists_assembly(document.id):
                document = new_assembly_document(name, seq=document.seq)
            self._write_assembly(document)
            return document

    def get_assembly(self, assembly_id: str) -> AssemblyDocument:
        with self._lock:
            path = self._assembly_path(assembly_id)
            if not path.exists():
                raise StoreError(
                    "NOT_FOUND", f"no assembly {assembly_id!r}", status=404
                )
            try:
                document = assembly_document_from_json(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            except Exception as exc:
                raise StoreError(
                    "CORRUPT", f"cannot read assembly {assembly_id}: {exc}", status=500
                ) from exc
            self._write_assembly_version(document)
            return document

    def save_assembly(self, document: AssemblyDocument) -> AssemblyDocument:
        with self._lock:
            self.validate_assembly_references(document)
            self._write_assembly(document)
            return document

    def get_assembly_version(self, assembly_id: str, version: int) -> AssemblyDocument:
        with self._lock:
            current_path = self._assembly_path(assembly_id)
            if current_path.exists():
                current = self.get_assembly(assembly_id)
                if current.version == version:
                    return current
            path = self._assembly_version_path(assembly_id, version)
            if not path.is_file():
                raise StoreError(
                    "VERSION_NOT_FOUND",
                    f"no assembly version {version} for {assembly_id!r}",
                    status=404,
                )
            try:
                return assembly_document_from_json(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            except Exception as exc:
                raise StoreError(
                    "VERSION_CORRUPT",
                    f"cannot read assembly version {version} of {assembly_id}: {exc}",
                    status=500,
                ) from exc

    def list_assembly_versions(self, assembly_id: str) -> list[int]:
        with self._lock:
            versions: set[int] = set()
            folder = self._versions_dir(assembly_id)
            if folder.is_dir():
                for path in folder.glob("assembly-*.json"):
                    try:
                        versions.add(int(path.stem.removeprefix("assembly-")))
                    except ValueError:
                        continue
            if self._assembly_path(assembly_id).exists():
                try:
                    versions.add(self.get_assembly(assembly_id).version)
                except StoreError:
                    pass
            return sorted(versions)

    def validate_assembly_references(
        self, document: AssemblyDocument, stack: tuple[str, ...] = ()
    ) -> None:
        """Every pin must resolve; assembly cycles are rejected."""
        stack = (*stack, document.id)
        for instance in document.instances:
            ref = instance.ref
            if isinstance(ref, PartRef):
                if not self.exists(ref.document_id):
                    raise StoreError(
                        "REF_NOT_FOUND",
                        f"instance {instance.id!r} references missing part {ref.document_id!r}",
                        status=409,
                    )
                try:
                    part = self.get_version(ref.document_id, ref.version)
                except StoreError as exc:
                    raise StoreError(
                        "REF_NOT_FOUND",
                        f"instance {instance.id!r} cannot read {ref.document_id}@"
                        f"{ref.version}: {exc.message}",
                        status=409,
                    ) from exc
                if (
                    ref.configuration != "default"
                    and ref.configuration not in part.configurations
                ):
                    raise StoreError(
                        "REF_CONFIG_NOT_FOUND",
                        f"instance {instance.id!r} references missing configuration "
                        f"{ref.configuration!r} of {ref.document_id!r}",
                        status=409,
                    )
                continue
            if not isinstance(ref, AssemblyRef):
                raise StoreError(
                    "REF_INVALID", f"instance {instance.id!r} has unknown reference"
                )
            if not self.exists_assembly(ref.document_id):
                raise StoreError(
                    "REF_NOT_FOUND",
                    f"instance {instance.id!r} references missing assembly {ref.document_id!r}",
                    status=409,
                )
            if ref.document_id in stack:
                raise StoreError(
                    "REF_CYCLE",
                    f"assembly reference cycle: {' -> '.join((*stack, ref.document_id))}",
                    status=409,
                )
            child = self.get_assembly_version(ref.document_id, ref.version)
            self.validate_assembly_references(child, stack)

    def save(self, document: Document) -> Document:
        with self._lock:
            history = self._read_history(document.id)
            if self.exists(document.id):
                current = self.get(document.id)
                history.append(document_to_json(current))
            self._write(document)
            if len(history) > _MAX_HISTORY:
                head = [
                    item for item in history[:1] if int(item.get("version", -1)) == 0
                ]
                history = head + history[-(_MAX_HISTORY - len(head)) :]
            self._write_history(document.id, history)
            return document

    def undo(self, document_id: str) -> Document:
        with self._lock:
            history = self._read_history(document_id)
            if not history:
                raise StoreError("NO_HISTORY", "nothing to undo", status=409)
            previous = document_from_json(history.pop())
            self._write(previous)
            self._write_history(document_id, history)
            return previous

    def get_version(self, document_id: str, version: int) -> Document:
        with self._lock:
            current = self.get(document_id)
            if current.version == version:
                return current
            path = self._version_path(document_id, version)
            if path.is_file():
                return self._read_version(document_id, version)
            # Legacy stores only kept bounded history; migrate the requested
            # version into an immutable snapshot when it is still available.
            history = self._read_history(document_id)
            for entry in reversed(history):
                if int(entry.get("version", 0)) == version:
                    document = ensure_chain(document_from_json(entry))
                    self._write_version(document)
                    return document
            raise StoreError(
                "VERSION_NOT_FOUND",
                f"no version {version} for {document_id!r}",
                status=404,
            )

    def list_versions(self, document_id: str) -> list[int]:
        with self._lock:
            versions: set[int] = set()
            folder = self._versions_dir(document_id)
            if folder.is_dir():
                for path in folder.glob("*.json"):
                    try:
                        versions.add(int(path.stem))
                    except ValueError:
                        continue
            if self._path(document_id).exists():
                versions.add(self.get(document_id).version)
            return sorted(versions)

    def prune_versions(self, document_id: str, keep: set[int]) -> list[int]:
        """Delete version snapshots not in ``keep``; the current version is kept."""
        with self._lock:
            current = self.get(document_id)
            keep = {int(item) for item in keep}
            keep.add(current.version)
            removed: list[int] = []
            folder = self._versions_dir(document_id)
            if folder.is_dir():
                for path in folder.glob("*.json"):
                    try:
                        version = int(path.stem)
                    except ValueError:
                        continue
                    if version not in keep:
                        path.unlink(missing_ok=True)
                        removed.append(version)
            history = self._read_history(document_id)
            retained = [
                entry for entry in history if int(entry.get("version", 0)) in keep
            ]
            if len(retained) != len(history):
                self._write_history(document_id, retained)
            return sorted(removed)

    def revert(self, document_id: str, target_version: int) -> Document:
        with self._lock:
            current = self.get(document_id)
            if current.version == target_version:
                return current
            history = self._read_history(document_id)
            match_index = None
            for index, entry in enumerate(history):
                if int(entry.get("version", 0)) == target_version:
                    match_index = index
            if match_index is None:
                raise StoreError(
                    "VERSION_NOT_FOUND",
                    f"no version {target_version} for {document_id!r}",
                    status=404,
                )
            target = document_from_json(history[match_index])
            self._write(target)
            self._write_history(document_id, history[:match_index])
            return target

    def _steps_dir(self) -> Path:
        path = self.root / "steps"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_step(self, digest: str) -> bytes | None:
        path = self._steps_dir() / f"{digest}.step"
        if not path.is_file():
            return None
        try:
            return path.read_bytes()
        except OSError:
            return None

    def put_step(self, digest: str, payload: bytes) -> Path:
        path = self._steps_dir() / f"{digest}.step"
        if not path.is_file():
            temp = path.with_suffix(".tmp")
            temp.write_bytes(payload)
            os.replace(temp, path)
        return path

    def _analysis_dir(self) -> Path:
        path = self.root / "analysis"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_analysis(self, digest: str) -> dict[str, Any] | None:
        path = self._analysis_dir() / f"{digest}.json"
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def put_analysis(self, digest: str, payload: dict[str, Any]) -> Path:
        with self._lock:
            path = self._analysis_dir() / f"{digest}.json"
            if not path.is_file():
                temp = path.with_suffix(".tmp")
                temp.write_text(
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8",
                )
                os.replace(temp, path)
            return path

    def _scenes_dir(self) -> Path:
        path = self.root / "scenes"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _scene_file(self, key: str) -> Path:
        name = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._scenes_dir() / f"{name}.json"

    def get_scene_bytes(self, key: str) -> bytes | None:
        """The scene file exactly as written, so a hit can be served without parsing it."""
        try:
            return self._scene_file(key).read_bytes()
        except OSError:
            return None

    def put_scene_bytes(self, key: str, payload: bytes) -> Path:
        with self._lock:
            path = self._scene_file(key)
            if not path.is_file():
                temp = path.with_suffix(".tmp")
                temp.write_bytes(payload)
                os.replace(temp, path)
            return path

    def get_scene(self, key: str) -> dict[str, Any] | None:
        raw = self.get_scene_bytes(key)
        if raw is None:
            return None
        try:
            payload = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def put_scene(self, key: str, payload: dict[str, Any]) -> Path:
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        return self.put_scene_bytes(key, raw)

    def _previews_dir(self) -> Path:
        return self.root / "previews"

    def _preview_manifests_dir(self) -> Path:
        return self._previews_dir() / "manifests"

    def _preview_prototypes_dir(self) -> Path:
        return self._previews_dir() / "prototypes"

    def _preview_bundles_dir(self) -> Path:
        return self._previews_dir() / "bundles"

    def _preview_builds_dir(self) -> Path:
        return self._previews_dir() / "builds"

    @staticmethod
    def _preview_key(preview_key: str) -> str:
        if not isinstance(preview_key, str) or _PREVIEW_KEY_PATTERN.fullmatch(
            preview_key
        ) is None:
            raise StoreError(
                "BAD_KEY", "preview key must be 64 lowercase hexadecimal characters"
            )
        return preview_key

    @staticmethod
    def _preview_build_id(build_id: str) -> str:
        if not isinstance(build_id, str) or _PREVIEW_BUILD_ID_PATTERN.fullmatch(
            build_id
        ) is None:
            raise StoreError("BAD_BUILD_ID", "invalid preview build id")
        return build_id

    def preview_manifest_path(self, preview_key: str) -> Path:
        return self._preview_manifests_dir() / f"{self._preview_key(preview_key)}.json"

    def preview_prototype_path(self, prototype_key: str) -> Path:
        return self._preview_prototypes_dir() / f"{self._preview_key(prototype_key)}.bin"

    def preview_bundle_path(self, bundle_key: str) -> Path:
        return self._preview_bundles_dir() / f"{self._preview_key(bundle_key)}.bpx"

    def preview_build_path(self, build_id: str) -> Path:
        return self._preview_builds_dir() / f"{self._preview_build_id(build_id)}.json"

    def preview_build_lock(self, preview_key: str) -> threading.Lock:
        """One build lock per preview key, shared by every caller in this store."""
        preview_key = self._preview_key(preview_key)
        with self._lock:
            lock = self._preview_build_locks.get(preview_key)
            if lock is None:
                lock = threading.Lock()
                self._preview_build_locks[preview_key] = lock
            return lock

    def preview_manifest_paths(self) -> list[Path]:
        return sorted(self._preview_manifests_dir().glob("*.json"))

    def preview_bundle_paths(self) -> list[Path]:
        return sorted(self._preview_bundles_dir().glob("*.bpx"))

    def preview_prototype_paths(self) -> list[Path]:
        return sorted(self._preview_prototypes_dir().glob("*.bin"))

    def remove_preview_file(self, path: Path) -> bool:
        """Unlink one file inside the preview cache; never follow outside it."""
        previews = self._previews_dir().resolve()
        target = path.resolve()
        if previews not in target.parents:
            raise StoreError(
                "BAD_PREVIEW_PATH",
                "preview cache deletion must stay inside the previews directory",
            )
        try:
            target.unlink()
            return True
        except FileNotFoundError:
            return False

    def _atomic_write(self, path: Path, payload: bytes) -> Path:
        """Write a cache file without exposing a partial file to a reader.

        The temporary name is unique per process and thread so two writers that
        target the same content-addressed path cannot truncate each other's
        staging file; the rename is the only step that publishes the bytes.
        Windows denies that rename while a reader holds the destination open, so
        a concurrent cache read must not fail a write that already succeeded on
        disk; the rename is retried for a bounded window instead.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(
            f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        )
        try:
            with temp.open("wb") as handle:
                handle.write(payload)
            _replace_with_retry(temp, path)
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
        return path

    def get_preview_manifest(self, preview_key: str) -> dict[str, Any] | None:
        """A complete manifest, or a miss for any structural or identity defect."""
        if not isinstance(preview_key, str) or _PREVIEW_KEY_PATTERN.fullmatch(
            preview_key
        ) is None:
            return None
        try:
            raw = self.preview_manifest_path(preview_key).read_bytes()
        except OSError:
            return None
        try:
            manifest = decode_manifest(raw)
        except PreviewFormatError:
            return None
        if manifest.get("previewKey") != preview_key:
            return None
        return manifest

    def put_preview_manifest(
        self, preview_key: str, manifest: dict[str, Any]
    ) -> Path:
        preview_key = self._preview_key(preview_key)
        if manifest.get("previewKey") != preview_key:
            raise StoreError(
                "PREVIEW_KEY_MISMATCH",
                "manifest previewKey does not match the cache path",
            )
        validate_manifest(manifest)
        bundle_key_value = manifest.get("bundleKey")
        if bundle_key_value is not None and not self.preview_bundle_path(
            bundle_key_value
        ).is_file():
            raise StoreError(
                "MISSING_BUNDLE",
                "lookup manifest names a bundle that is not on disk",
            )
        with self.preview_cache_lock:
            return self._atomic_write(
                self.preview_manifest_path(preview_key), encode_manifest(manifest)
            )

    def get_preview_prototype(self, prototype_key: str) -> bytes | None:
        if not isinstance(prototype_key, str) or _PREVIEW_KEY_PATTERN.fullmatch(
            prototype_key
        ) is None:
            return None
        try:
            return self.preview_prototype_path(prototype_key).read_bytes()
        except OSError:
            return None

    def put_preview_prototype(self, prototype_key: str, payload: bytes) -> Path:
        path = self.preview_prototype_path(prototype_key)
        with self.preview_cache_lock:
            with self._lock:
                if path.is_file():
                    return path
                return self._atomic_write(path, payload)

    def get_preview_bundle(self, bundle_key: str) -> bytes | None:
        if not isinstance(bundle_key, str) or _PREVIEW_KEY_PATTERN.fullmatch(
            bundle_key
        ) is None:
            return None
        try:
            return self.preview_bundle_path(bundle_key).read_bytes()
        except OSError:
            return None

    def put_preview_bundle(self, bundle_key: str, payload: bytes) -> Path:
        bundle_key = self._preview_key(bundle_key)
        if _bundle_key(payload) != bundle_key:
            raise StoreError(
                "BUNDLE_KEY_MISMATCH",
                "bundle bytes do not hash to the requested bundle key",
            )
        with self.preview_cache_lock:
            return self._atomic_write(
                self.preview_bundle_path(bundle_key), payload
            )

    def get_preview_build(self, build_id: str) -> dict[str, Any] | None:
        if not isinstance(build_id, str) or _PREVIEW_BUILD_ID_PATTERN.fullmatch(
            build_id
        ) is None:
            return None
        try:
            payload = json.loads(self.preview_build_path(build_id).read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def put_preview_build(self, build_id: str, payload: dict[str, Any]) -> Path:
        build_id = self._preview_build_id(build_id)
        return self._atomic_write(
            self.preview_build_path(build_id),
            json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8"),
        )

    def add_intent(
        self, document_id: str, text: str, base_version: int | None = None
    ) -> dict[str, Any]:
        with self._lock:
            if not self.exists(document_id):
                raise StoreError(
                    "NOT_FOUND", f"no document {document_id!r}", status=404
                )
            entries = self._read_intents(document_id)
            entry = {
                "id": f"i_{len(entries) + 1}_{int(time.time() * 1000) % 100000}",
                "text": text,
                "base_version": base_version,
                "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            entries.append(entry)
            self._write_intents(document_id, entries)
            return entry

    def list_intents(self, document_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return self._read_intents(document_id)

    def clear_intents(self, document_id: str) -> int:
        with self._lock:
            entries = self._read_intents(document_id)
            self._write_intents(document_id, [])
            return len(entries)

    def get_plan(self, document_id: str) -> ModelingPlan | None:
        with self._lock:
            path = self._plan_path(document_id)
            if not path.exists():
                return None
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                return plan_from_json(payload)
            except (OSError, json.JSONDecodeError) as exc:
                raise StoreError(
                    "PLAN_CORRUPT",
                    f"cannot read plan for {document_id}: {exc}",
                    status=500,
                ) from exc

    def save_plan(self, plan: ModelingPlan) -> ModelingPlan:
        with self._lock:
            path = self._plan_path(plan.document_id)
            temp = path.with_suffix(".tmp")
            temp.write_text(
                json.dumps(plan_to_json(plan), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temp, path)
            return plan

    def delete_plan(self, document_id: str) -> None:
        with self._lock:
            self._plan_path(document_id).unlink(missing_ok=True)

    def _imports_dir(self) -> Path:
        path = self.root / "imports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def put_import(self, payload: bytes, suffix: str) -> tuple[Path, str]:
        """Freeze imported bytes under their digest; rebuild reads this copy."""
        digest = hashlib.sha256(payload).hexdigest()
        cleaned = "".join(ch for ch in suffix.lower() if ch.isalnum())[:8] or "bin"
        path = self._imports_dir() / f"{digest}.{cleaned}"
        with self._lock:
            if not path.is_file():
                temp = path.with_suffix(".tmp")
                temp.write_bytes(payload)
                os.replace(temp, path)
        return path, digest

    def import_path(self, digest: str, suffix: str = "step") -> Path | None:
        cleaned = "".join(ch for ch in suffix.lower() if ch.isalnum())[:8] or "bin"
        path = self._imports_dir() / f"{digest}.{cleaned}"
        return path if path.is_file() else None

    def _intents_path(self, document_id: str) -> Path:
        return self.root / f"{document_id}.intents.json"

    def _read_intents(self, document_id: str) -> list[dict[str, Any]]:
        path = self._intents_path(document_id)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return list(payload) if isinstance(payload, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _write_intents(self, document_id: str, entries: list[dict[str, Any]]) -> None:
        path = self._intents_path(document_id)
        temp = path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temp, path)

    def _write(self, document: Document) -> None:
        self._write_version(document)
        path = self._path(document.id)
        temp = path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(document_to_json(document), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temp, path)

    def _write_assembly(self, document: AssemblyDocument) -> None:
        self._write_assembly_version(document)
        path = self._assembly_path(document.id)
        temp = path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                assembly_document_to_json(document), ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )
        os.replace(temp, path)

    def _write_assembly_version(self, document: AssemblyDocument) -> Path:
        path = self._assembly_version_path(document.id, document.version)
        if path.is_file():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing != assembly_document_to_json(document):
                raise StoreError(
                    "IMMUTABLE_VERSION",
                    f"assembly {document.id!r} version {document.version} already exists "
                    "with different content",
                    status=409,
                )
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".json.tmp")
        temp.write_text(
            json.dumps(
                assembly_document_to_json(document), ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )
        os.replace(temp, path)
        return path

    def _read_version(self, document_id: str, version: int) -> Document:
        path = self._version_path(document_id, version)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return ensure_chain(document_from_json(payload))
        except (OSError, json.JSONDecodeError) as exc:
            raise StoreError(
                "VERSION_CORRUPT",
                f"cannot read version {version} of {document_id}: {exc}",
                status=500,
            ) from exc

    def _write_version(self, document: Document) -> Path:
        path = self._version_path(document.id, document.version)
        if path.is_file():
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".json.tmp")
        temp.write_text(
            json.dumps(document_to_json(document), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temp, path)
        return path

    def _read_history(self, document_id: str) -> list[dict[str, Any]]:
        path = self._history_path(document_id)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return list(payload) if isinstance(payload, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _write_history(self, document_id: str, history: list[dict[str, Any]]) -> None:
        path = self._history_path(document_id)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, path)
