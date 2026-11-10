"""Variant sets: several parameter values built side by side.

A variant is the same document with one feature's parameters replaced: building
it is a pure function, so N of them cost N compiles — and the content-addressed
cache makes everything before the changed feature free. Nothing here writes to
the store; applying a variant does, later, through the normal edit path.
"""

from __future__ import annotations

import itertools
import shutil
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from cadwork.design.build import BuildError, BuildResult
from cadwork.design.document import Document, DocumentError, apply_ops
from cadwork.design.features import FEATURES

MAX_VARIANTS = 4
MAX_SETS = 8
TTL_SECONDS = 1800.0


@dataclass
class Variant:
    index: int
    label: str
    ops: list[dict[str, Any]]
    values: dict[str, Any] = field(default_factory=dict)
    ok: bool = True
    summary: dict[str, Any] = field(default_factory=dict)
    checks: list[dict[str, Any]] = field(default_factory=list)
    error: dict[str, Any] | None = None
    thumb: Path | None = None
    step: Path | None = None

    def to_json(self, set_id: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "index": self.index,
            "label": self.label,
            "ops": self.ops,
            "ok": self.ok,
            "thumb": (f"/api/variants/{set_id}/{self.index}/thumb.png"
                      if self.thumb is not None else None),
            "step": (f"/api/variants/{set_id}/{self.index}/step"
                     if self.ok else None),
            **self.summary,
        }
        if self.values:
            payload["values"] = self.values
        if self.checks:
            payload["checks"] = self.checks
        if self.error:
            payload["error"] = self.error
        return payload


@dataclass
class VariantSet:
    id: str
    document_id: str
    base_version: int
    created: float
    folder: Path
    label: str = ""
    variants: list[Variant] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "set": self.id,
            "document": self.document_id,
            "label": self.label,
            "base_version": self.base_version,
            "variants": [variant.to_json(self.id) for variant in self.variants],
        }


class VariantBook:
    """Live variant sets, bounded in count and age; thumbnails live in temp dirs."""

    def __init__(
        self,
        build_document: Callable[[Document], BuildResult],
        render: Callable[[Any], bytes] | None = None,
        export: Callable[[Any], bytes] | None = None,
        root: Path | None = None,
    ) -> None:
        self._build = build_document
        self._render = render
        self._export = export
        self._root = root or Path(tempfile.mkdtemp(prefix="cadwork-variants-"))
        self._sets: dict[str, VariantSet] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ query
    def get(self, set_id: str) -> VariantSet:
        with self._lock:
            entry = self._sets.get(set_id)
            if entry is None:
                raise KeyError(set_id)
            return entry

    # ------------------------------------------------------------------ create
    def create(
        self,
        document: Document,
        specs: list[dict[str, Any]],
        include_base: bool = False,
        label: str = "",
        thumbs: bool = True,
    ) -> VariantSet:
        """Build one card per candidate document delta.

        A variant is any edit to the document — a parameter, a feature switched
        off, a step added — so nothing here knows about holes or walls.
        """
        if not isinstance(specs, list) or not specs:
            raise ValueError("give at least one variant")
        total = len(specs) + (1 if include_base else 0)
        if total > MAX_VARIANTS:
            raise ValueError(f"{total} variants requested, at most {MAX_VARIANTS} at a time")

        prepared: list[dict[str, Any]] = []
        if include_base:
            prepared.append({"label": "当前", "ops": [], "values": {}})
        for spec in specs:
            if not isinstance(spec, dict):
                raise ValueError("each variant is an object with `ops`")
            ops = spec.get("ops") or []
            if not isinstance(ops, list) or any(not isinstance(op, dict) for op in ops):
                raise ValueError("`ops` must be a list of operations")
            prepared.append({
                "label": str(spec.get("label") or "").strip() or _auto_label(ops),
                "ops": ops,
                "values": spec.get("values") or {},
            })

        set_id = f"vs_{uuid.uuid4().hex[:10]}"
        folder = self._root / set_id
        folder.mkdir(parents=True, exist_ok=True)
        entry = VariantSet(
            id=set_id,
            document_id=document.id,
            base_version=document.version,
            created=time.time(),
            folder=folder,
            label=str(label or ""),
        )
        for index, item in enumerate(prepared):
            variant = Variant(index=index, label=item["label"], ops=item["ops"],
                              values=item["values"])
            self._build_variant(document, variant, folder, thumbs)
            entry.variants.append(variant)

        with self._lock:
            self._evict_locked()
            self._sets[set_id] = entry
        return entry

    def create_sweep(
        self,
        document: Document,
        feature_id: str,
        params: dict[str, list[Any]],
        include_base: bool = False,
        thumbs: bool = True,
    ) -> VariantSet:
        """Sugar: one dimension per parameter, cartesian product as the cards."""
        feature = next((item for item in document.features if item.id == feature_id), None)
        if feature is None:
            raise ValueError(f"no feature {feature_id!r} in this document")
        spec = FEATURES.get(feature.type)
        unknown = [name for name in params if spec is None or name not in spec.params]
        if unknown:
            raise ValueError(
                f"{feature.type} has no parameter {', '.join(sorted(unknown))}"
                + (f"; it has {', '.join(sorted(spec.params))}" if spec else "")
            )
        names = sorted(params)
        for name in names:
            values = params[name]
            if not isinstance(values, list) or not values:
                raise ValueError(f"values for {name} must be a non-empty list")
        combos = list(itertools.product(*(params[name] for name in names)))
        specs = []
        for combo in combos:
            values = dict(zip(names, combo))
            specs.append({
                "label": " · ".join(f"{name} {_number(value)}" for name, value in values.items()),
                "values": values,
                "ops": [{"op": "update", "id": feature_id, "params": values}],
            })
        return self.create(document, specs, include_base=include_base, label=feature_id,
                           thumbs=thumbs)

    def _build_variant(self, document: Document, variant: Variant, folder: Path,
                       thumbs: bool = True) -> None:
        try:
            # No base_version: this is a copy of the document we were handed.
            candidate = apply_ops(document, variant.ops) if variant.ops else document
            result = self._build(candidate)
            final = result.final
            variant.summary = {
                "faces": len(final.faces()) if final is not None else 0,
                "volume": round(float(final.volume), 1) if final is not None else 0.0,
                "seconds": round(getattr(result, "seconds", 0.0), 2),
                "cache_hits": getattr(result, "cache_hits", 0),
            }
            variant.checks = [
                {"name": check.name, "ok": check.ok, "hint": check.hint,
                 "expected": check.expected}
                for item in result.features for check in item.checks
            ]
            if thumbs and final is not None and self._render is not None:
                try:
                    png = self._render(final)
                except Exception:  # a picture must never lose the numbers
                    png = b""
                if png:
                    path = folder / f"{variant.index}.png"
                    path.write_bytes(png)
                    variant.thumb = path
        except (BuildError, DocumentError) as exc:
            variant.ok = False
            variant.error = {"code": exc.code, "message": exc.message,
                             "hint": getattr(exc, "hint", None),
                             "feature_id": getattr(exc, "feature_id", None)}
            variant.checks = [
                {"name": check.name, "ok": check.ok, "hint": check.hint,
                 "expected": check.expected}
                for check in getattr(exc, "checks", ())
            ]

    # ------------------------------------------------------------------ housekeeping
    def _evict_locked(self) -> None:
        now = time.time()
        stale = [key for key, item in self._sets.items()
                 if now - item.created > TTL_SECONDS]
        for key in stale:
            self._drop_locked(key)
        while len(self._sets) >= MAX_SETS:
            oldest = min(self._sets.values(), key=lambda item: item.created)
            self._drop_locked(oldest.id)

    def _drop_locked(self, set_id: str) -> None:
        entry = self._sets.pop(set_id, None)
        if entry is not None:
            shutil.rmtree(entry.folder, ignore_errors=True)

    def close(self) -> None:
        with self._lock:
            for key in list(self._sets):
                self._drop_locked(key)
            shutil.rmtree(self._root, ignore_errors=True)

    # ------------------------------------------------------------------ contact sheet
    def sheet(self, set_id: str) -> bytes:
        """One picture of the whole set: every variant side by side, labelled.

        A contact sheet is what makes a variant set reviewable at a glance — on
        screen and on a slide — without the workbench open.
        """
        entry = self.get(set_id)
        pictures = [(variant, variant.thumb) for variant in entry.variants]
        drawn = [(variant, path) for variant, path in pictures if path is not None]
        if not drawn:
            raise LookupError("no variant pictures to compose")

        from PIL import Image, ImageDraw, ImageFont

        font = _load_font(15)
        small = _load_font(13)
        card_w, gap, margin, bar = 460, 18, 22, 54
        width = margin * 2 + len(drawn) * card_w + (len(drawn) - 1) * gap
        tiles = []
        for variant, path in drawn:
            image = Image.open(path).convert("RGB")
            ratio = card_w / image.width
            tiles.append((variant, image.resize((card_w, max(1, int(image.height * ratio))),
                                                Image.LANCZOS)))
        height = margin * 2 + bar + max(tile.height for _, tile in tiles)
        sheet = Image.new("RGB", (width, height), (255, 255, 255))
        canvas = ImageDraw.Draw(sheet)

        x = margin
        for variant, tile in tiles:
            top = margin + bar
            sheet.paste(tile, (x, top))
            canvas.rectangle([x, top, x + card_w - 1, top + tile.height - 1],
                             outline=(214, 220, 228))
            label = variant.label
            canvas.text((x, margin), label, fill=(26, 32, 42), font=font)
            if variant.ok:
                numbers = (f"{variant.summary.get('faces', 0)} faces · "
                           f"{_number(variant.summary.get('volume', 0))} mm³ · "
                           f"{variant.summary.get('seconds', 0)} s")
                canvas.text((x, margin + 22), numbers, fill=(96, 108, 124), font=small)
            else:
                reason = (variant.error or {}).get("message", "does not build")
                canvas.text((x, margin + 22), f"FAILED · {reason}"[:60],
                            fill=(196, 60, 80), font=small)
            x += card_w + gap

        import io

        buffer = io.BytesIO()
        sheet.save(buffer, format="PNG")
        return buffer.getvalue()


def _auto_label(ops: list[dict[str, Any]]) -> str:
    """A readable name for a candidate delta, when the caller did not give one."""
    parts: list[str] = []
    for op in ops:
        kind = op.get("op")
        if kind == "update":
            params = op.get("params") or {}
            if params:
                parts.append(" · ".join(f"{name} {_number(value)}"
                                        for name, value in params.items()))
            elif op.get("enabled") is False:
                parts.append(f"{op.get('id')} 关闭")
            elif op.get("enabled") is True:
                parts.append(f"{op.get('id')} 开启")
            else:
                parts.append(f"改 {op.get('id')}")
        elif kind == "add":
            feature = op.get("feature") or {}
            parts.append(f"+{feature.get('type', 'feature')}")
        elif kind == "remove":
            parts.append(f"−{op.get('id')}")
        else:
            parts.append(str(kind))
    return " / ".join(parts) or "当前"


def _number(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        if float(value).is_integer():
            return f"{int(value):,}"
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return str(value)


def _load_font(size: int):
    from PIL import ImageFont

    for candidate in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\segoeui.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()
