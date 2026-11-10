"""JSON document store: one file per document, plus bounded undo history."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from cadwork.design.document import (
    Document,
    document_from_json,
    document_to_json,
    new_document,
)

_MAX_HISTORY = 50


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

    # ------------------------------------------------------------ paths
    def _path(self, document_id: str) -> Path:
        return self.root / f"{document_id}.json"

    def _history_path(self, document_id: str) -> Path:
        return self.root / f"{document_id}.history.json"

    def _next_seq(self) -> int:
        """Creation order, independent of file timestamps (coarse on Windows)."""
        highest = 0
        for path in self.root.glob("*.json"):
            if path.name.endswith(".history.json"):
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            highest = max(highest, int(payload.get("seq", 0) or 0))
        return highest + 1

    # ------------------------------------------------------------ queries
    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            entries: list[dict[str, Any]] = []
            for path in self.root.glob("*.json"):
                if path.name.endswith(".history.json"):
                    continue
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
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

    def get(self, document_id: str) -> Document:
        path = self._path(document_id)
        if not path.exists():
            raise StoreError("NOT_FOUND", f"no document {document_id!r}", status=404)
        try:
            return document_from_json(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise StoreError("CORRUPT", f"cannot read {document_id}: {exc}", status=500) from exc

    # ------------------------------------------------------------ writes
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
            self._write_history(document.id, history[-_MAX_HISTORY:])
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

    # ------------------------------------------------------------ internals
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
