"""JSON document store: one file per document, plus bounded undo history."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from cadwork.design.document import (
    Document,
    document_from_json,
    document_to_json,
    ensure_chain,
    new_document,
)
from cadwork.design.plan import ModelingPlan, plan_from_json, plan_to_json

_MAX_HISTORY = 100


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

    def _path(self, document_id: str) -> Path:
        return self.root / f"{document_id}.json"

    def _history_path(self, document_id: str) -> Path:
        return self.root / f"{document_id}.history.json"

    def _plan_path(self, document_id: str) -> Path:
        return self.root / f"{document_id}.plan.json"

    def _document_paths(self) -> list[Path]:
        """Only document files; history/intent/plan sidecars share the suffix."""
        paths: list[Path] = []
        for path in self.root.glob("*.json"):
            if path.name.endswith((".history.json", ".intents.json", ".plan.json")):
                continue
            paths.append(path)
        return paths

    def _next_seq(self) -> int:
        """Creation order, independent of file timestamps (coarse on Windows)."""
        highest = 0
        for path in self._document_paths():
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
                entries.append({
                    "id": payload.get("id", path.stem),
                    "name": payload.get("name", ""),
                    "version": payload.get("version", 1),
                    "features": len(payload.get("features") or []),
                    "seq": int(payload.get("seq", 0) or 0),
                })
            entries.sort(key=lambda entry: entry["seq"], reverse=True)
            return entries

    def exists(self, document_id: str) -> bool:
        return self._path(document_id).exists()

    def delete(self, document_id: str) -> None:
        with self._lock:
            path = self._path(document_id)
            if not path.exists():
                raise StoreError("NOT_FOUND", f"no document {document_id!r}", status=404)
            path.unlink()
            self._history_path(document_id).unlink(missing_ok=True)
            self._plan_path(document_id).unlink(missing_ok=True)

    def get(self, document_id: str) -> Document:
        path = self._path(document_id)
        if not path.exists():
            raise StoreError("NOT_FOUND", f"no document {document_id!r}", status=404)
        try:
            return ensure_chain(document_from_json(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError) as exc:
            raise StoreError("CORRUPT", f"cannot read {document_id}: {exc}", status=500) from exc

    def create(self, name: str = "Untitled") -> Document:
        with self._lock:
            document = new_document(name, seq=self._next_seq())
            while self.exists(document.id):
                document = new_document(name, seq=document.seq)
            self._write(document)
            return document

    def save(self, document: Document) -> Document:
        with self._lock:
            history = self._read_history(document.id)
            if self.exists(document.id):
                current = self.get(document.id)
                history.append(document_to_json(current))
            self._write(document)
            if len(history) > _MAX_HISTORY:
                head = [item for item in history[:1] if int(item.get("version", -1)) == 0]
                history = head + history[-(_MAX_HISTORY - len(head)):]
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
            history = self._read_history(document_id)
            for entry in reversed(history):
                if int(entry.get("version", 0)) == version:
                    return document_from_json(entry)
            raise StoreError("VERSION_NOT_FOUND", f"no version {version} for {document_id!r}", status=404)

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
                raise StoreError("VERSION_NOT_FOUND", f"no version {target_version} for {document_id!r}", status=404)
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

    def add_intent(self, document_id: str, text: str,
                   base_version: int | None = None) -> dict[str, Any]:
        with self._lock:
            if not self.exists(document_id):
                raise StoreError("NOT_FOUND", f"no document {document_id!r}", status=404)
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
                raise StoreError("PLAN_CORRUPT", f"cannot read plan for {document_id}: {exc}",
                                 status=500) from exc

    def save_plan(self, plan: ModelingPlan) -> ModelingPlan:
        with self._lock:
            path = self._plan_path(plan.document_id)
            temp = path.with_suffix(".tmp")
            temp.write_text(json.dumps(plan_to_json(plan), ensure_ascii=False, indent=2),
                            encoding="utf-8")
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
        temp.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)

    def _write(self, document: Document) -> None:
        path = self._path(document.id)
        temp = path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(document_to_json(document), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temp, path)

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
