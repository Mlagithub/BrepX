"""Measure preview generation, warm validation, and transfer size.

The fixture case runs entirely in a temporary store built from the assembly plan
path. The turbofan case runs on a clone of the real store; the real store is only
copied and never opened as a Store. Cold time includes the scene projection
because the clone excludes derived scene caches, matching the user-visible cold
path. Warm samples separate the public service read, ensure_preview's cache hit,
load_preview's validation, and the raw bundle decode so the cost of full decode
is visible rather than hidden inside one number.
"""

from __future__ import annotations

import argparse
import gc
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

from bench_assembly_preview import (
    _PeakRss,
    _build_fixture,
    _environment,
    _gzip_size,
    _median,
    _rounded,
    _tree_size,
)
from preview_turbofan_acceptance import _clone_store

from cadwork.service.preview import (
    ensure_preview,
    load_preview,
    preview_key,
)
from cadwork.service.preview_format import decode_bundle, decode_header
from cadwork.service.service import CADService
from cadwork.service.store import Store

SCHEMA = "brepx-assembly-preview-performance"
DEFAULT_STORE = "cadwork-data"
DEFAULT_ASSEMBLY = "a_63b4b86b9f"
DEFAULT_OUTPUT = "artifacts/assembly-preview/AP10-performance.json"
DEFAULT_TIMEOUT = 1200.0
WARM_SAMPLES = 3
CONCERNING_WARM_SECONDS = 0.5
CONCERNING_DECODE_SHARE = 0.5


def _samples(function, count: int = WARM_SAMPLES) -> list[float]:
    values: list[float] = []
    for _ in range(count):
        started = time.perf_counter()
        function()
        values.append(_rounded(time.perf_counter() - started))
    return values


def _summary(values: list[float]) -> dict[str, Any]:
    return {
        "samples": values,
        "median": _rounded(_median(values)),
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
    }


def _wait_for_ready(
    service: CADService,
    assembly_id: str,
    version: int,
    timeout: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    started = time.perf_counter()
    first = service.assembly_preview(assembly_id, version)
    if first["state"] == "ready":
        return first, []
    build_id = first["buildId"]
    job = service.preview_jobs.get(build_id)
    observations: list[dict[str, Any]] = []
    deadline = started + timeout
    last_sample = -1.0
    while job is not None and job.status in {"queued", "running"}:
        now = time.perf_counter()
        if now - last_sample >= 5.0:
            observations.append(
                {
                    "elapsed_seconds": _rounded(now - started),
                    "status": job.status,
                    "progress": job.progress,
                }
            )
            last_sample = now
        if now >= deadline:
            raise RuntimeError(
                f"preview build exceeded {timeout:g} s: "
                f"{job.status} progress {job.progress}"
            )
        time.sleep(0.25)
        job = service.preview_jobs.get(build_id)
    if job is None:
        raise RuntimeError("preview build handle disappeared")
    observations.append(
        {
            "elapsed_seconds": _rounded(time.perf_counter() - started),
            "status": job.status,
            "progress": job.progress,
        }
    )
    if job.status != "done":
        raise RuntimeError(
            f"preview build failed: {job.error_code}: {job.error_message}"
        )
    ready = service.assembly_preview(assembly_id, version)
    if ready["state"] != "ready":
        raise RuntimeError(f"preview did not become ready: {ready['state']}")
    return ready, observations


def _metadata_from_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    assembly = manifest["assembly"]
    generator = manifest["generator"]
    return {
        "assembly_id": assembly["id"],
        "assembly_version": assembly["version"],
        "configuration": assembly["configuration"],
        "name": assembly["name"],
        "overrides": {},
        "generator_version": generator["version"],
        "kernel_version": generator["kernel"],
        "tessellation_profile": generator["tessellationProfile"],
    }


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return _rounded(numerator / denominator)


def _compare(
    baseline_case: dict[str, Any] | None,
    ap08_case: dict[str, Any] | None,
    cold_seconds: float,
    warm_service_median: float,
    warm_load_median: float,
    sizes: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {"baseline": None, "ap08": None}
    if baseline_case:
        scene = baseline_case.get("scene") or {}
        scene_cold = scene.get("cold") or {}
        scene_warm = scene.get("warm") or {}
        export = baseline_case.get("export") or {}
        result["baseline"] = {
            "sceneBytes": scene_cold.get("bytes"),
            "sceneGzipBytes": scene_cold.get("gzip_bytes"),
            "sceneColdSeconds": scene_cold.get("seconds"),
            "sceneWarmSeconds": scene_warm.get("seconds_median"),
            "stepBytes": export.get("output_bytes"),
            "stepSeconds": export.get("seconds"),
            "stepStatus": export.get("status"),
            "bundleOverSceneBytes": _ratio(
                sizes["bundleBytes"], scene_cold.get("bytes")
            ),
            "bundleGzipOverSceneGzip": _ratio(
                sizes["bundleGzipBytes"], scene_cold.get("gzip_bytes")
            ),
            "coldPreviewOverSceneCold": _ratio(
                cold_seconds, scene_cold.get("seconds")
            ),
            "warmPreviewOverSceneWarm": _ratio(
                warm_service_median, scene_warm.get("seconds_median")
            ),
            "bundleOverStepBytes": _ratio(
                sizes["bundleBytes"], export.get("output_bytes")
            ),
            "warmPreviewOverStepExport": _ratio(
                warm_service_median, export.get("seconds")
            ),
        }
    if ap08_case:
        result["ap08"] = {
            "coldSeconds": (ap08_case.get("cold") or {}).get("seconds"),
            "warmSeconds": (ap08_case.get("warm") or {}).get("seconds"),
            "bundleBytes": (ap08_case.get("sizes") or {}).get("bundleBytes"),
            "manifestBytes": (ap08_case.get("sizes") or {}).get(
                "manifestBytes"
            ),
            "coldOverAp08Cold": _ratio(
                cold_seconds, (ap08_case.get("cold") or {}).get("seconds")
            ),
            "warmOverAp08Warm": _ratio(
                warm_load_median, (ap08_case.get("warm") or {}).get("seconds")
            ),
        }
    return result


def _size_record(
    store: Store, key: str, content_key: str, manifest: dict[str, Any]
) -> dict[str, Any]:
    manifest_path = store.preview_manifest_path(key)
    bundle_path = store.preview_bundle_path(content_key)
    manifest_bytes = manifest_path.read_bytes()
    bundle_bytes = bundle_path.read_bytes()
    prototype_sizes = [
        store.preview_prototype_path(str(record["prototypeKey"])).stat().st_size
        for record in manifest.get("prototypes") or []
    ]
    return {
        "manifestBytes": len(manifest_bytes),
        "manifestGzipBytes": _gzip_size(manifest_bytes),
        "bundleKey": content_key,
        "bundleBytes": len(bundle_bytes),
        "bundleGzipBytes": _gzip_size(bundle_bytes),
        "bundleSha256": hashlib.sha256(bundle_bytes).hexdigest(),
        "prototypeFileCount": len(prototype_sizes),
        "prototypeFileBytes": sum(prototype_sizes),
        "prototypeBlobBytes": sum(
            int((item.get("mesh") or {}).get("blobLength") or 0)
            for item in manifest.get("prototypes") or []
        ),
        "smallestPrototypeBytes": min(prototype_sizes) if prototype_sizes else 0,
        "largestPrototypeBytes": max(prototype_sizes) if prototype_sizes else 0,
    }


def _measure_case(
    store: Store,
    assembly_id: str,
    version: int | None,
    timeout: float,
    baseline_case: dict[str, Any] | None,
    ap08_case: dict[str, Any] | None,
) -> dict[str, Any]:
    service = CADService(store)
    document = service.read_assembly(assembly_id, version)
    version = document.version

    gc.collect()
    with _PeakRss() as cold_memory:
        cold_started = time.perf_counter()
        ready, observations = _wait_for_ready(
            service, assembly_id, version, timeout
        )
        cold_seconds = _rounded(time.perf_counter() - cold_started)
    cold_rss = cold_memory.summary()
    key = ready["previewKey"]
    manifest = dict(ready["manifest"])
    bundle = ready["bundle"]
    sizes = _size_record(store, key, ready["bundleKey"], manifest)
    if sizes["bundleBytes"] != len(bundle):
        raise RuntimeError("stored bundle size differs from served bytes")

    scene_cache_key = f"assembly-scene:{assembly_id}:{version}"
    scene = store.get_scene(scene_cache_key)
    if not scene:
        raise RuntimeError("scene cache missing after the cold preview build")
    metadata = _metadata_from_manifest(manifest)
    expected_key = preview_key(
        assembly_id=metadata["assembly_id"],
        assembly_version=metadata["assembly_version"],
        configuration=metadata["configuration"],
        overrides=metadata["overrides"],
        generator_version=metadata["generator_version"],
        kernel_version=metadata["kernel_version"],
        tessellation_profile=metadata["tessellation_profile"],
    )
    if expected_key != key:
        raise RuntimeError("reconstructed preview identity does not match the key")

    warm_service = _samples(
        lambda: service.assembly_preview(assembly_id, version)
    )
    warm_ensure = _samples(
        lambda: ensure_preview(store, scene, **metadata)
    )
    warm_load = _samples(lambda: load_preview(store, key))
    warm_bundle = _samples(lambda: store.get_preview_bundle(key))
    warm_manifest = _samples(lambda: store.get_preview_manifest(key))
    warm_header = _samples(lambda: decode_header(bundle))
    warm_decode = _samples(lambda: decode_bundle(bundle))

    gc.collect()
    with _PeakRss() as warm_memory:
        load_preview(store, key)
    warm_rss = warm_memory.summary()

    service_median = _summary(warm_service)["median"]
    load_median = _summary(warm_load)["median"]
    decode_median = _summary(warm_decode)["median"]
    decode_share = (
        _rounded(decode_median / load_median)
        if decode_median is not None and load_median
        else None
    )
    counts = {
        "prototypes": manifest.get("prototypeCount"),
        "instances": manifest.get("instanceCount"),
        "leafs": manifest.get("leafCount"),
        "sceneInstances": manifest.get("sceneInstanceCount"),
        "frames": manifest.get("frameCount"),
        "failures": manifest.get("failedCount"),
        "suppressed": manifest.get("suppressedCount"),
        "bom": dict(manifest.get("bom") or {}),
        "positionCount": sum(
            int((item.get("mesh") or {}).get("positionCount") or 0)
            for item in manifest.get("prototypes") or []
        ),
        "indexCount": sum(
            int((item.get("mesh") or {}).get("indexCount") or 0)
            for item in manifest.get("prototypes") or []
        ),
        "edgePointCount": sum(
            int((item.get("mesh") or {}).get("edgePointCount") or 0)
            for item in manifest.get("prototypes") or []
        ),
    }
    comparison = _compare(
        baseline_case,
        ap08_case,
        cold_seconds,
        service_median,
        load_median,
        sizes,
    )
    concerning = bool(
        load_median is not None
        and load_median >= CONCERNING_WARM_SECONDS
        and decode_share is not None
        and decode_share >= CONCERNING_DECODE_SHARE
    )
    recommendation = None
    if concerning:
        recommendation = (
            f"Warm load takes {load_median:.4f} s and full bundle decode takes "
            f"{decode_median:.4f} s ({decode_share:.0%} of the load). The measured "
            "bundle is small enough that the current contract is workable, but a "
            "later optimization could persist a bundle digest or verified layout "
            "at write time and use it to serve warm hits without rebuilding every "
            "typed array; full decode would remain the miss and repair path. "
            "The contract is unchanged by this measurement."
        )
    return {
        "assembly": {
            "id": document.id,
            "name": document.name,
            "version": version,
            "previewKey": key,
            "bundleKey": ready["bundleKey"],
        },
        "counts": counts,
        "cold": {
            "seconds": cold_seconds,
            "progressObservations": observations,
            "peakRss": cold_rss,
        },
        "warm": {
            "serviceRead": _summary(warm_service),
            "ensurePreview": _summary(warm_ensure),
            "loadPreview": _summary(warm_load),
            "readBundleBytes": _summary(warm_bundle),
            "readManifestValidated": _summary(warm_manifest),
            "decodeHeader": _summary(warm_header),
            "decodeBundle": _summary(warm_decode),
            "loadPeakRss": warm_rss,
            "decodeShareOfLoad": decode_share,
        },
        "sizes": sizes,
        "comparison": comparison,
        "concerningWarmDecode": concerning,
        "recommendation": recommendation,
    }


def _references() -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    baseline_path = ROOT / "artifacts" / "assembly-preview" / "baseline.json"
    ap08_path = ROOT / "artifacts" / "assembly-preview" / "AP08-turbofan.json"
    baseline = None
    ap08 = None
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        baseline = None
    try:
        ap08 = json.loads(ap08_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        ap08 = None
    return baseline, ap08


def _fixture_case(folder: Path, references: tuple[Any, Any]) -> dict[str, Any]:
    store, assembly_id = _build_fixture(folder)
    baseline, _ap08 = references
    baseline_case = ((baseline or {}).get("cases") or {}).get(
        "seven_instance_fixture"
    )
    return _measure_case(
        store, assembly_id, None, DEFAULT_TIMEOUT, baseline_case, None
    )


def _turbofan_case(
    source: Path, folder: Path, assembly_id: str, version: int | None,
    references: tuple[Any, Any]
) -> dict[str, Any]:
    clone_root = folder / "store"
    clone = _clone_store(source, clone_root)
    baseline, ap08 = references
    baseline_case = ((baseline or {}).get("cases") or {}).get("turbofan")
    ap08_case = ap08 if ap08 and ap08.get("status") == "ok" else None
    measured = _measure_case(
        Store(clone_root),
        assembly_id,
        version,
        DEFAULT_TIMEOUT,
        baseline_case,
        ap08_case,
    )
    measured["clone"] = clone
    return measured


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure assembly preview cold/warm performance and transfer."
    )
    parser.add_argument("--store", default=DEFAULT_STORE)
    parser.add_argument("--assembly", default=DEFAULT_ASSEMBLY)
    parser.add_argument("--version", type=int, default=None)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()

    source = Path(args.store)
    if not source.is_absolute():
        source = ROOT / source
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    references = _references()
    if not source.is_dir():
        print(f"no store at {source}", file=sys.stderr)
        return 2
    if not (source / f"{args.assembly}.assembly.json").is_file():
        print(f"no assembly {args.assembly} under {source}", file=sys.stderr)
        return 2
    real_before_files, real_before_bytes = _tree_size(source)
    real_before_previews = (source / "previews").exists()
    folder = Path(tempfile.mkdtemp(prefix="brepx-preview-performance-"))
    fixture_folder = folder / "fixture"
    fixture_folder.mkdir()
    turbofan_folder = folder / "turbofan"
    turbofan_folder.mkdir()
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "command": "python "
        + " ".join(
            [str(Path(__file__).resolve().relative_to(ROOT)), *sys.argv[1:]]
        ),
        "environment": _environment(source),
        "warmSampleCount": WARM_SAMPLES,
        "thresholds": {
            "concerningWarmSeconds": CONCERNING_WARM_SECONDS,
            "concerningDecodeShare": CONCERNING_DECODE_SHARE,
        },
        "realStore": {
            "root": str(source),
            "filesBefore": real_before_files,
            "bytesBefore": real_before_bytes,
            "previewsBefore": real_before_previews,
            "filesAfter": None,
            "bytesAfter": None,
            "previewsAfter": None,
        },
        "cases": {},
        "limitations": [
            "cold includes the scene projection because the turbofan clone "
            "excludes scenes/ and the fixture is built from scratch",
            "timings are small-sample medians on one desktop under normal load, "
            "not a controlled microbenchmark",
            "peak RSS is sampled from a separate thread and can hide a short "
            "allocation spike that never releases the GIL",
            "no server or browser is started, so network transfer, TLS and "
            "client decode are not measured",
            "the fixture is procedural boxes; it exercises the same code paths "
            "but says nothing about real part complexity",
        ],
        "recommendation": None,
    }
    try:
        print("measuring 7-instance fixture", flush=True)
        fixture = _fixture_case(fixture_folder, references)
        payload["cases"]["seven_instance_fixture"] = fixture
        print(
            f"fixture cold {fixture['cold']['seconds']} s, "
            f"warm load {fixture['warm']['loadPreview']['median']} s",
            flush=True,
        )
        gc.collect()

        if not (source / f"{args.assembly}.assembly.json").is_file():
            raise RuntimeError(f"no assembly {args.assembly} under {source}")
        print(f"cloning {source} -> {turbofan_folder / 'store'}", flush=True)
        turbofan = _turbofan_case(
            source, turbofan_folder, args.assembly, args.version, references
        )
        payload["cases"]["turbofan"] = turbofan
        print(
            f"turbofan cold {turbofan['cold']['seconds']} s, "
            f"warm load {turbofan['warm']['loadPreview']['median']} s",
            flush=True,
        )
        concerning = [
            case
            for case in payload["cases"].values()
            if case["concerningWarmDecode"]
        ]
        if concerning:
            payload["recommendation"] = concerning[0]["recommendation"]
        payload["status"] = "ok"
        _write(output, payload)
        print(f"wrote {output}", flush=True)
        return 0
    except Exception as exc:
        payload["status"] = "failed"
        payload["error"] = {"message": f"{type(exc).__name__}: {exc}"}
        _write(output, payload)
        print(f"failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        print(f"wrote {output}", file=sys.stderr, flush=True)
        return 1
    finally:
        after_files, after_bytes = _tree_size(source)
        payload["realStore"].update(
            {
                "filesAfter": after_files,
                "bytesAfter": after_bytes,
                "previewsAfter": (source / "previews").exists(),
            }
        )
        _write(output, payload)
        if not args.keep_temp:
            shutil.rmtree(folder, ignore_errors=True)
        else:
            print(f"kept temp at {folder}", flush=True)


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(_main())
