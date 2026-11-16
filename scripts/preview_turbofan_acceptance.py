"""Measure the turbofan assembly preview on an isolated copy of the real store.

The real store is read once by a directory copy and is never opened as a Store:
the cold sample then rebuilds every part, packs prototypes, writes the bundle,
and measures a warm read on the copy only. The JSON record keeps stage timings
so a slow or failed run names the stage that dominated instead of collapsing
everything into one wall-clock number.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bench_assembly_preview import _environment, _gzip_size, _rounded, _tree_size

from cadwork.service import preview as preview_module
from cadwork.service.preview import is_preview_key
from cadwork.service.preview_format import decode_bundle, encode_manifest
from cadwork.service.service import CADService
from cadwork.service.store import Store

SCHEMA = "brepx-assembly-preview-acceptance"
DEFAULT_STORE = "cadwork-data"
DEFAULT_ASSEMBLY = "a_63b4b86b9f"
DEFAULT_OUTPUT = "artifacts/assembly-preview/AP08-turbofan.json"
DEFAULT_TIMEOUT = 1200.0
POLL_SECONDS = 0.5

# A derived scene, preview, analysis or log directory must not make the cold
# sample warm; the clone is the isolation boundary, not a second cache layer.
_CLONE_SKIPPED = {"scenes", "previews", "analysis", "logs", "__pycache__"}


class AcceptanceError(Exception):
    def __init__(self, status: str, message: str, detail: dict[str, Any]) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.detail = detail


def _clone_ignore(directory: str, names: list[str]) -> set[str]:
    del directory
    return {
        name
        for name in names
        if name in _CLONE_SKIPPED or name.endswith(".tmp")
    }


def _clone_store(source: Path, target: Path) -> dict[str, Any]:
    started = time.perf_counter()
    shutil.copytree(source, target, ignore=_clone_ignore)
    files, size = _tree_size(target)
    return {
        "seconds": _rounded(time.perf_counter() - started),
        "files": files,
        "bytes": size,
    }


def _scene_counts(scene: dict[str, Any]) -> dict[str, int]:
    definitions = scene.get("definitions") or {}
    instances = scene.get("instances") or []
    bom = scene.get("bom") or []
    return {
        "definitions": len(definitions),
        "instances": len(instances),
        "leaves": sum(
            1 for item in instances if item.get("definition_kind") == "part"
        ),
        "frames": sum(
            1
            for item in instances
            if item.get("definition_kind") == "assembly"
        ),
        "failed": sum(1 for item in instances if item.get("error") is not None),
        "bom_rows": len(bom),
        "bom_quantity": sum(int(row.get("quantity") or 0) for row in bom),
    }


def _manifest_counts(manifest: dict[str, Any]) -> dict[str, Any]:
    prototypes = manifest.get("prototypes") or []
    instances = manifest.get("instances") or []
    keys = {record.get("prototypeKey") for record in prototypes}
    return {
        "prototypeCount": manifest.get("prototypeCount"),
        "instanceCount": manifest.get("instanceCount"),
        "leafCount": manifest.get("leafCount"),
        "sceneInstanceCount": manifest.get("sceneInstanceCount"),
        "frameCount": manifest.get("frameCount"),
        "failedCount": manifest.get("failedCount"),
        "suppressedCount": manifest.get("suppressedCount"),
        "bom": dict(manifest.get("bom") or {}),
        "prototypeRecords": len(prototypes),
        "instanceRecords": len(instances),
        "instanceKeysResolve": all(
            item.get("prototypeKey") in keys for item in instances
        ),
        "positionCount": sum(
            int((item.get("mesh") or {}).get("positionCount") or 0)
            for item in prototypes
        ),
        "indexCount": sum(
            int((item.get("mesh") or {}).get("indexCount") or 0)
            for item in prototypes
        ),
        "faceCount": sum(
            int((item.get("mesh") or {}).get("faceCount") or 0)
            for item in prototypes
        ),
        "edgePointCount": sum(
            int((item.get("mesh") or {}).get("edgePointCount") or 0)
            for item in prototypes
        ),
    }


def _prototype_files(store: Store, manifest: dict[str, Any]) -> dict[str, Any]:
    sizes: list[int] = []
    paths: list[str] = []
    for record in manifest.get("prototypes") or []:
        path = store.preview_prototype_path(str(record["prototypeKey"]))
        paths.append(str(path.relative_to(store.root)))
        sizes.append(path.stat().st_size)
    return {
        "count": len(sizes),
        "bytes": sum(sizes),
        "smallestBytes": min(sizes) if sizes else 0,
        "largestBytes": max(sizes) if sizes else 0,
        "files": paths,
    }


def _check_expected(counts: dict[str, Any], scene_counts: dict[str, int]) -> None:
    expected = {
        "scene.definitions": (scene_counts["definitions"], 183),
        "scene.instances": (scene_counts["instances"], 1941),
        "scene.leaves": (scene_counts["leaves"], 1930),
        "scene.frames": (scene_counts["frames"], 11),
        "scene.failed": (scene_counts["failed"], 0),
        "manifest.prototypeCount": (counts["prototypeCount"], 183),
        "manifest.instanceCount": (counts["instanceCount"], 1930),
        "manifest.leafCount": (counts["leafCount"], 1930),
        "manifest.sceneInstanceCount": (counts["sceneInstanceCount"], 1941),
        "manifest.frameCount": (counts["frameCount"], 11),
        "manifest.failedCount": (counts["failedCount"], 0),
        "manifest.bom.rows": ((counts["bom"] or {}).get("rows"), 183),
        "manifest.bom.quantity": ((counts["bom"] or {}).get("quantity"), 1930),
        "manifest.bom.definitions": ((counts["bom"] or {}).get("definitions"), 183),
    }
    mismatched = {
        name: {"observed": observed, "expected": wanted}
        for name, (observed, wanted) in expected.items()
        if observed != wanted
    }
    if mismatched:
        raise AcceptanceError(
            "failed",
            f"preview counts disagree with the turbofan contract: {mismatched}",
            {"mismatched": mismatched},
        )


def _measure(
    store: Store,
    assembly_id: str,
    version: int | None,
    timeout: float,
) -> dict[str, Any]:
    service = CADService(store)
    document = service.read_assembly(assembly_id, version)
    version = document.version
    stages: dict[str, float] = {}
    captured: dict[str, dict[str, Any]] = {}

    original_scene = service.assembly_scene
    original_plan = preview_module.plan_preview
    original_write = preview_module.write_preview

    def timed_scene(*args: Any, **kwargs: Any) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            scene = original_scene(*args, **kwargs)
            captured["scene"] = scene
            return scene
        finally:
            stages["scene_seconds"] = _rounded(time.perf_counter() - started)

    def timed_plan(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return original_plan(*args, **kwargs)
        finally:
            stages["pack_seconds"] = _rounded(time.perf_counter() - started)

    def timed_write(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return original_write(*args, **kwargs)
        finally:
            stages["write_seconds"] = _rounded(time.perf_counter() - started)

    service.assembly_scene = timed_scene  # type: ignore[method-assign]
    preview_module.plan_preview = timed_plan
    preview_module.write_preview = timed_write

    observations: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        first = service.assembly_preview(assembly_id, version)
        if first["state"] == "building":
            build_id = first["buildId"]
            key = first["previewKey"]
            job = service.preview_jobs.get(build_id)
            deadline = started + timeout
            while (
                job is not None
                and job.status in {"queued", "running"}
                and time.perf_counter() < deadline
            ):
                observations.append(
                    {
                        "elapsed_seconds": _rounded(time.perf_counter() - started),
                        "status": job.status,
                        "progress": job.progress,
                    }
                )
                time.sleep(POLL_SECONDS)
                job = service.preview_jobs.get(build_id)
            if job is None:
                raise AcceptanceError(
                    "failed",
                    "preview build handle disappeared",
                    {"buildId": build_id},
                )
            observations.append(
                {
                    "elapsed_seconds": _rounded(time.perf_counter() - started),
                    "status": job.status,
                    "progress": job.progress,
                }
            )
            if job.status in {"queued", "running"}:
                raise AcceptanceError(
                    "timeout",
                    f"preview build exceeded {timeout:g} s",
                    {
                        "buildId": build_id,
                        "stage": job.status,
                        "progress": job.progress,
                        "stages": dict(stages),
                        "observations": observations,
                    },
                )
            if job.status == "failed":
                raise AcceptanceError(
                    "failed",
                    f"{job.error_code}: {job.error_message}",
                    {
                        "buildId": build_id,
                        "stage": "build",
                        "stages": dict(stages),
                        "error": {
                            "code": job.error_code,
                            "message": job.error_message,
                        },
                    },
                )
            ready = service.assembly_preview(assembly_id, version)
        else:
            ready = first
        if ready["state"] != "ready":
            raise AcceptanceError(
                "failed",
                f"preview did not become ready: {ready.get('state')}",
                {"stages": dict(stages)},
            )
        cold_seconds = time.perf_counter() - started
        key = ready["previewKey"]
        bundle = ready["bundle"]
        if not is_preview_key(key):
            raise AcceptanceError(
                "failed", "preview key is not 64 lowercase hex", {"key": key}
            )

        scene = captured.get("scene")
        if not scene:
            raise AcceptanceError(
                "failed",
                "the preview build did not expose its scene projection",
                {"stages": dict(stages)},
            )
        scene_counts = _scene_counts(scene)
        manifest = dict(ready["manifest"])
        counts = _manifest_counts(manifest)
        _check_expected(counts, scene_counts)

        manifest_path = store.preview_manifest_path(key)
        content_key = ready["bundleKey"]
        bundle_path = store.preview_bundle_path(content_key)
        manifest_bytes = manifest_path.read_bytes()
        bundle_bytes = bundle_path.read_bytes()
        if bundle_bytes != bundle:
            raise AcceptanceError(
                "failed",
                "bundle file differs from the served bytes",
                {"bundlePath": str(bundle_path)},
            )
        lookup = dict(manifest)
        lookup["bundleKey"] = content_key
        if manifest_bytes != encode_manifest(lookup):
            raise AcceptanceError(
                "failed",
                "stored lookup is not the canonical encoding of the served manifest",
                {"manifestPath": str(manifest_path)},
            )
        decode_started = time.perf_counter()
        decoded = decode_bundle(bundle)
        decode_seconds = _rounded(time.perf_counter() - decode_started)
        if len(decoded.prototypes) != counts["prototypeCount"]:
            raise AcceptanceError(
                "failed",
                "decoded prototype count disagrees with the manifest",
                {
                    "decoded": len(decoded.prototypes),
                    "manifest": counts["prototypeCount"],
                },
            )

        prototypes = _prototype_files(store, manifest)
        temp_files = list((store.root / "previews").rglob("*.tmp"))
        if temp_files:
            raise AcceptanceError(
                "failed",
                "temporary preview files were left behind",
                {"files": [str(item) for item in temp_files]},
            )

        sizes = {
            "manifestBytes": len(manifest_bytes),
            "manifestGzipBytes": _gzip_size(manifest_bytes),
            "bundleBytes": len(bundle_bytes),
            "bundleGzipBytes": _gzip_size(bundle_bytes),
            "bundleSha256": hashlib.sha256(bundle_bytes).hexdigest(),
            "dataBase": decoded.data_base,
            "headerManifestBytes": decoded.header.manifest_length,
            "prototypeFiles": prototypes,
            "prototypeBlobBytes": sum(
                int((item.get("mesh") or {}).get("blobLength") or 0)
                for item in manifest.get("prototypes") or []
            ),
        }

        warm_started = time.perf_counter()
        warm = service.assembly_preview(assembly_id, version)
        warm_seconds = time.perf_counter() - warm_started
        if warm["state"] != "ready" or warm["bundle"] != bundle:
            raise AcceptanceError(
                "failed",
                "warm preview read did not return the cold bytes",
                {"state": warm.get("state")},
            )

        return {
            "status": "ok",
            "assembly": {
                "id": document.id,
                "name": document.name,
                "version": version,
                "previewKey": key,
                "bundleKey": content_key,
                "buildId": first.get("buildId"),
            },
            "scene": scene_counts,
            "manifest": counts,
            "cold": {
                "seconds": _rounded(cold_seconds),
                "stageSeconds": dict(stages),
                "pollObservations": observations,
            },
            "warm": {
                "seconds": _rounded(warm_seconds),
                "bytesMatchCold": True,
            },
            "sizes": sizes,
            "validation": {
                "bundleDecodeSeconds": decode_seconds,
                "prototypeFilesMatchManifest": (
                    prototypes["count"] == counts["prototypeCount"]
                ),
                "instanceKeysResolve": counts["instanceKeysResolve"],
                "bundleBytesMatchServed": True,
                "manifestCanonical": True,
            },
        }
    except AcceptanceError as exc:
        exc.detail.update(
            {
                "assemblyId": assembly_id,
                "version": version,
                "stageSeconds": dict(stages),
                "pollObservations": observations,
            }
        )
        raise
    finally:
        service.assembly_scene = original_scene  # type: ignore[method-assign]
        preview_module.plan_preview = original_plan
        preview_module.write_preview = original_write


def _write_output(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure the turbofan assembly preview on a store clone."
    )
    parser.add_argument("--store", default=DEFAULT_STORE)
    parser.add_argument("--assembly", default=DEFAULT_ASSEMBLY)
    parser.add_argument("--version", type=int, default=None)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()

    store_root = Path(args.store)
    if not store_root.is_absolute():
        store_root = ROOT / store_root
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    if not store_root.is_dir():
        print(f"no store at {store_root}", file=sys.stderr)
        return 2
    if not (store_root / f"{args.assembly}.assembly.json").is_file():
        print(f"no assembly {args.assembly} under {store_root}", file=sys.stderr)
        return 2

    before_files, before_bytes = _tree_size(store_root)
    before_previews = (store_root / "previews").exists()
    environment = _environment(store_root)
    folder = Path(tempfile.mkdtemp(prefix="brepx-preview-acceptance-"))
    clone_root = folder / "store"
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "command": "python "
        + " ".join(
            [str(Path(__file__).resolve().relative_to(ROOT)), *sys.argv[1:]]
        ),
        "environment": environment,
        "realStore": {
            "root": str(store_root),
            "filesBefore": before_files,
            "bytesBefore": before_bytes,
            "previewsBefore": before_previews,
            "previewsAfter": None,
            "filesAfter": None,
            "bytesAfter": None,
        },
        "clone": None,
        "assembly": {"id": args.assembly, "requestedVersion": args.version},
        "limitations": [
            "the turbofan runs on a copy of the real store without scenes/, "
            "previews/, analysis/ or logs/, so the cold scene rebuilds every "
            "definition and the real store is never opened as a Store",
            "timings are single-run samples on one desktop under normal load; "
            "the copy itself is measured separately from the preview",
            "draw calls are not measured: no browser renderer or server is started",
        ],
    }
    keep_temp = args.keep_temp
    try:
        print(f"cloning {store_root} -> {clone_root}", flush=True)
        payload["clone"] = _clone_store(store_root, clone_root)
        print(
            f"clone {payload['clone']['seconds']} s, "
            f"{payload['clone']['files']} files",
            flush=True,
        )
        clone_store = Store(clone_root)
        print("building cold preview", flush=True)
        measured = _measure(
            clone_store, args.assembly, args.version, args.timeout_seconds
        )
        payload.update(measured)
        print("cold preview ready", flush=True)
        _write_output(output, payload)
        print(f"wrote {output}", flush=True)
    except AcceptanceError as exc:
        keep_temp = keep_temp or exc.status != "ok"
        payload.update(
            {
                "status": exc.status,
                "error": {"message": exc.message, **exc.detail},
            }
        )
        _write_output(output, payload)
        print(f"{exc.status}: {exc.message}", file=sys.stderr, flush=True)
        print(f"wrote {output}", file=sys.stderr, flush=True)
        result = 2 if exc.status == "timeout" else 1
    except Exception as exc:
        keep_temp = True
        payload.update(
            {
                "status": "error",
                "error": {
                    "message": f"{type(exc).__name__}: {exc}",
                    "assemblyId": args.assembly,
                    "version": args.version,
                },
            }
        )
        _write_output(output, payload)
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        print(f"wrote {output}", file=sys.stderr, flush=True)
        result = 1
    else:
        result = 0
    finally:
        after_files, after_bytes = _tree_size(store_root)
        payload["realStore"].update(
            {
                "previewsAfter": (store_root / "previews").exists(),
                "filesAfter": after_files,
                "bytesAfter": after_bytes,
            }
        )
        _write_output(output, payload)
        if not keep_temp:
            shutil.rmtree(folder, ignore_errors=True)
        else:
            print(f"kept clone at {folder}", flush=True)
    print(json.dumps(payload.get("status")), flush=True)
    return result


if __name__ == "__main__":
    raise SystemExit(_main())
