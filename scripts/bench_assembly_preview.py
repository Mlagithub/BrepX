"""Measure the current assembly scene, BOM and STEP export paths.

The samples come from the same CADService methods the HTTP routes call, so the
byte counts and timings describe the existing behaviour rather than a parallel
implementation. A cold scene is measured on a clone of the source store with its
scene cache removed: the clone has no cached projection, so every definition is
rebuilt. The warm sample runs the same call again on the same service.

BOM is measured in-process; STEP export is measured in a child process. One
process cannot report a per-call peak working set for two calls, and a STEP
export of a large assembly can outlive any sensible wall clock; the parent bounds
the child with a timeout and records the timeout instead of blocking the rest of
the measurement.

Byte counts are compact UTF-8 JSON with non-ASCII preserved, which is the byte
count the HTTP layer serializes for a dict response. Peak working set is sampled
by a separate thread so that sampling does not inflate the reported duration.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cadwork.service.service import CADService
from cadwork.service.store import Store

SCHEMA = "brepx-assembly-preview-baseline"
DEFAULT_STORE = "cadwork-data"
DEFAULT_OUTPUT = "artifacts/assembly-preview/baseline.json"
DEFAULT_ASSEMBLY = "a_63b4b86b9f"
DEFAULT_EXPORT_TIMEOUT = 1800.0
RSS_SAMPLE_SECONDS = 0.02

# The scene cache is a derived projection; dropping it is what makes the cold
# sample cold. Analysis, logs and bytecode caches are unrelated to a build.
_CLONED_STORE_SKIPPED = {"scenes", "analysis", "logs", "__pycache__"}


class _PeakRss:
    """Sample the process working set while a call runs, without timing it."""

    def __init__(self) -> None:
        self.baseline = 0
        self.peak = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._process: Any = None
        self._psutil: Any = None

    def __enter__(self) -> Self:
        try:
            import psutil
        except ImportError:  # memory is optional evidence
            return self
        self._psutil = psutil
        self._process = psutil.Process(os.getpid())
        self.baseline = int(self._process.memory_info().rss)
        self.peak = self.baseline
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> bool:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        return False

    def _sample(self) -> None:
        while not self._stop.is_set():
            try:
                rss = int(self._process.memory_info().rss)
            except (self._psutil.Error, OSError):
                break
            self.peak = max(self.peak, rss)
            self._stop.wait(RSS_SAMPLE_SECONDS)

    def summary(self) -> dict[str, int | None]:
        if self._process is None:
            return {"baseline_rss_bytes": None, "peak_rss_bytes": None}
        return {
            "baseline_rss_bytes": self.baseline,
            "peak_rss_bytes": self.peak,
            "rss_increase_bytes": max(0, self.peak - self.baseline),
        }


class _ByteCounter:
    def __init__(self) -> None:
        self.size = 0

    def write(self, payload: bytes) -> int:
        self.size += len(payload)
        return len(payload)


def _compact_json(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        indent=None,
        separators=(",", ":"),
    ).encode("utf-8")


def _gzip_size(payload: bytes) -> int:
    # mtime=0 keeps the compressed length independent of when the sample ran.
    return len(gzip.compress(payload, compresslevel=6, mtime=0))


def _gzip_file_size(path: Path) -> int:
    counter = _ByteCounter()
    with (
        path.open("rb") as source,
        gzip.GzipFile(fileobj=counter, mode="wb", compresslevel=6, mtime=0) as sink,
    ):
        while True:
            chunk = source.read(1 << 20)
            if not chunk:
                break
            sink.write(chunk)
    return counter.size


def _median(samples: list[float]) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _rounded(value: float | None, digits: int = 4) -> float | None:
    return None if value is None else round(value, digits)


def _tree_size(path: Path) -> tuple[int, int]:
    files = 0
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                files += 1
                total += item.stat().st_size
        except OSError:
            continue
    return files, total


def _environment(store_root: Path) -> dict[str, Any]:
    try:
        import numpy

        numpy_version = numpy.__version__
    except ImportError:
        numpy_version = None
    try:
        import smlibpy

        kernel_version = getattr(smlibpy, "__version__", None)
    except ImportError:
        kernel_version = None
    try:
        import psutil

        memory_total = int(psutil.virtual_memory().total)
    except ImportError:
        memory_total = None
    head, dirty = _git_state()
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "memory_total_bytes": memory_total,
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "numpy": numpy_version,
        "kernel": f"smlibpy {kernel_version}" if kernel_version else None,
        "git_head": head,
        "git_dirty_paths": dirty,
        "store": str(store_root),
    }


def _git_state() -> tuple[str | None, int | None]:
    try:
        head = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
        status = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain"],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None, None
    commit = head.stdout.strip() or None
    changed = len([line for line in status.stdout.splitlines() if line.strip()])
    return commit, changed


def _clone_store(source: Path, target: Path) -> dict[str, Any]:
    started = time.perf_counter()
    shutil.copytree(source, target, ignore=_clone_ignore)
    files, size = _tree_size(target)
    return {
        "seconds": _rounded(time.perf_counter() - started),
        "files": files,
        "bytes": size,
    }


def _clone_ignore(directory: str, names: list[str]) -> set[str]:
    del directory
    return {
        name for name in names if name in _CLONED_STORE_SKIPPED or name.endswith(".tmp")
    }


def _scene_counts(scene: dict[str, Any]) -> dict[str, int]:
    definitions = scene.get("definitions") or {}
    faces = 0
    vertices = 0
    triangles = 0
    edges = 0
    for definition in definitions.values():
        definition_faces = definition.get("faces") or []
        faces += len(definition_faces)
        for face in definition_faces:
            vertices += len(face.get("vertices") or []) // 3
            triangles += len(face.get("triangles") or []) // 3
        edges += len(definition.get("edges") or [])
    instances = scene.get("instances") or []
    leaves = [item for item in instances if item.get("definition_kind") == "part"]
    bom = scene.get("bom") or []
    return {
        "definitions": len(definitions),
        "instances": len(instances),
        "leaf_instances": len(leaves),
        "leaf_instances_with_geometry": sum(
            1 for item in leaves if item.get("error") is None
        ),
        "subassembly_instances": sum(
            1 for item in instances if item.get("definition_kind") == "assembly"
        ),
        "failures": int((scene.get("metrics") or {}).get("failures") or 0),
        "definition_faces": faces,
        "definition_vertices": vertices,
        "definition_triangles": triangles,
        "definition_edges": edges,
        "bom_rows": len(bom),
        "bom_quantity": sum(int(entry.get("quantity") or 0) for entry in bom),
    }


def _bom_counts(payload: dict[str, Any]) -> dict[str, int]:
    rows = payload.get("rows") or []
    summary = payload.get("summary") or []
    return {
        "rows": len(rows),
        "definitions": len(summary),
        "quantity": sum(int(entry.get("quantity") or 0) for entry in summary),
        "part_rows": sum(1 for row in rows if row.get("kind") == "part"),
        "assembly_rows": sum(1 for row in rows if row.get("kind") == "assembly"),
    }


def _measure_scene(
    service: CADService, store: Store, assembly_id: str, version: int, repeats: int
) -> dict[str, Any]:
    with _PeakRss() as memory:
        started = time.perf_counter()
        scene = service.assembly_scene(assembly_id)
        cold_seconds = time.perf_counter() - started
    serialize_started = time.perf_counter()
    payload = _compact_json(scene)
    serialize_seconds = time.perf_counter() - serialize_started
    cold = {
        "seconds": _rounded(cold_seconds),
        "serialize_seconds": _rounded(serialize_seconds),
        "bytes": len(payload),
        "gzip_bytes": _gzip_size(payload),
        **memory.summary(),
    }

    cache_key = f"assembly-scene:{assembly_id}:{version}"
    cached = store.get_scene_bytes(cache_key)

    warm_samples: list[float] = []
    warm_payload: bytes | None = None
    for _ in range(max(1, repeats)):
        started = time.perf_counter()
        warm_scene = service.assembly_scene(assembly_id)
        warm_samples.append(time.perf_counter() - started)
        if warm_payload is None:
            warm_payload = _compact_json(warm_scene)

    warm = {
        "seconds_samples": [_rounded(item) for item in warm_samples],
        "seconds_median": _rounded(_median(warm_samples)),
        "bytes": len(warm_payload) if warm_payload is not None else None,
        "gzip_bytes": _gzip_size(warm_payload) if warm_payload is not None else None,
        "bytes_match_cold": warm_payload == payload,
    }
    return {
        "cache_key": cache_key,
        "cache_bytes_after_cold": len(cached) if cached is not None else None,
        "cold": cold,
        "warm": warm,
        "counts": _scene_counts(scene),
    }


def _measure_bom(service: CADService, assembly_id: str, repeats: int) -> dict[str, Any]:
    samples: list[float] = []
    payload: bytes | None = None
    counts: dict[str, int] | None = None
    with _PeakRss() as memory:
        for _ in range(max(1, repeats)):
            started = time.perf_counter()
            result = service.assembly_bom(assembly_id)
            samples.append(time.perf_counter() - started)
            if payload is None:
                payload = _compact_json(result)
                counts = _bom_counts(result)
        memory_summary = memory.summary()
    return {
        "seconds_samples": [_rounded(item) for item in samples],
        "seconds_median": _rounded(_median(samples)),
        "seconds_first": _rounded(samples[0]),
        "bytes": len(payload) if payload is not None else None,
        "gzip_bytes": _gzip_size(payload) if payload is not None else None,
        "counts": counts,
        **memory_summary,
    }


def _export_worker(args: argparse.Namespace) -> int:
    store = Store(args.store)
    service = CADService(store)
    with _PeakRss() as memory:
        started = time.perf_counter()
        raw, media_type, sidecar = service.assembly_export(args.assembly, "step")
        seconds = time.perf_counter() - started
    memory_summary = memory.summary()
    Path(args.export_file).write_bytes(raw)
    Path(args.export_result).write_text(
        json.dumps(
            {
                "seconds": seconds,
                "media_type": media_type,
                "sidecar": sidecar,
                **memory_summary,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return 0


def _measure_export(
    store_root: Path, assembly_id: str, timeout_seconds: float
) -> dict[str, Any]:
    folder = Path(tempfile.mkdtemp(prefix="brepx-preview-export-"))
    step_path = folder / "assembly.step"
    result_path = folder / "export.json"
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--export-worker",
        "--store",
        str(store_root),
        "--assembly",
        assembly_id,
        "--export-file",
        str(step_path),
        "--export-result",
        str(result_path),
    ]
    started = time.perf_counter()
    timed_out = False
    exit_code: int | None = None
    stderr_tail = ""
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
        exit_code = completed.returncode
        stderr_tail = (completed.stderr or "")[-4000:]
    except subprocess.TimeoutExpired:
        timed_out = True
    wall_seconds = time.perf_counter() - started
    try:
        partial_bytes = step_path.stat().st_size if step_path.is_file() else 0
        if not result_path.is_file():
            # A timed-out child may have left a prefix of the STEP file; that
            # prefix is not the export size, so it is never reported as one.
            return {
                "status": "timeout" if timed_out else "failed",
                "wall_seconds": _rounded(wall_seconds),
                "seconds": None,
                "output_bytes": None,
                "partial_output_bytes": partial_bytes,
                "exit_code": exit_code,
                "stderr_tail": stderr_tail,
            }
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "status": "failed",
                "wall_seconds": _rounded(wall_seconds),
                "seconds": None,
                "output_bytes": None,
                "partial_output_bytes": partial_bytes,
                "exit_code": exit_code,
                "stderr_tail": f"{stderr_tail}\n{exc}".strip(),
            }
        output_bytes = partial_bytes
        try:
            gzip_bytes = _gzip_file_size(step_path) if output_bytes else None
        except OSError:
            gzip_bytes = None
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    sidecar = payload.get("sidecar") or {}
    bom = sidecar.get("bom") or []
    return {
        "status": "ok",
        "seconds": _rounded(payload.get("seconds")),
        "wall_seconds": _rounded(wall_seconds),
        "output_bytes": output_bytes,
        "gzip_bytes": gzip_bytes,
        "media_type": payload.get("media_type"),
        "baseline_rss_bytes": payload.get("baseline_rss_bytes"),
        "peak_rss_bytes": payload.get("peak_rss_bytes"),
        "rss_increase_bytes": payload.get("rss_increase_bytes"),
        "exit_code": exit_code,
        "counts": {
            "instances": sidecar.get("instances"),
            "placed_parts": sidecar.get("placed_parts"),
            "failures": len(sidecar.get("failures") or []),
            "bom_rows": len(bom),
            "bom_quantity": sum(int(entry.get("quantity") or 0) for entry in bom),
            "bbox": sidecar.get("bbox"),
        },
    }


def _measure_case(
    *,
    store: Store,
    assembly_id: str,
    source: str,
    setup: dict[str, Any] | None,
    source_scene_cache_bytes: int | None,
    warm_repeats: int,
    bom_repeats: int,
    measure_export: bool,
    export_timeout: float,
) -> dict[str, Any]:
    document = store.get_assembly(assembly_id)
    service = CADService(store)
    scene = _measure_scene(service, store, assembly_id, document.version, warm_repeats)
    bom = _measure_bom(service, assembly_id, bom_repeats)
    result: dict[str, Any] = {
        "available": True,
        "assembly": {
            "id": document.id,
            "name": document.name,
            "version": document.version,
            "source": source,
        },
        "setup": setup,
        "source_scene_cache_bytes": source_scene_cache_bytes,
        "scene": scene,
        "bom": bom,
        "export": {
            "status": "skipped",
            "reason": "measurement disabled by --skip-export",
        },
        "draw_calls": {
            "measured": False,
            "reason": "no browser renderer is attached to this measurement",
        },
    }
    if measure_export:
        result["export"] = _measure_export(
            Path(store.root), assembly_id, export_timeout
        )
    return result


def _build_fixture(folder: Path) -> tuple[Store, str]:
    from cadwork.design.assembly import PartRef, Transform
    from cadwork.design.assembly_plan import (
        AssemblyPlan,
        Pattern,
        PlanInstance,
        compile_assembly_plan,
    )
    from cadwork.design.document import apply_ops

    store = Store(folder)

    def part(name: str, height: float):
        document = store.create(name)
        document = apply_ops(
            document,
            [
                {
                    "op": "add",
                    "feature": {
                        "id": "base",
                        "type": "k_box",
                        "params": {"length": 10.0, "width": 6.0, "height": height},
                    },
                }
            ],
        )
        return store.save(document)

    blade = part("blade", 4.0)
    disk = part("disk", 6.0)
    plan = AssemblyPlan(
        "assembly_preview_fixture",
        "assembly_preview_fixture",
        (
            PlanInstance("disk", PartRef(disk.id, 1), Transform()),
            PlanInstance(
                "blade",
                PartRef(blade.id, 1),
                placement=Transform(translation=(0.0, 0.0, 3.0)),
                pattern=Pattern("polar", 6, radius=30.0),
            ),
        ),
    )
    assembly = compile_assembly_plan(plan)
    store.save_assembly(assembly)
    return store, assembly.id


def _run(args: argparse.Namespace) -> int:
    store_root = Path(args.store)
    if not store_root.is_absolute():
        store_root = ROOT / store_root
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output

    environment = _environment(store_root)
    cases: dict[str, Any] = {}
    limitations: list[str] = [
        (
            "draw calls are not measured: no browser renderer is attached, so "
            "only server-side payload sizes and timings are recorded"
        ),
        (
            "peak working set is sampled from a separate thread every "
            f"{int(RSS_SAMPLE_SECONDS * 1000)} ms; a C call that never releases "
            "the GIL can hide a short allocation spike, so the value is an "
            "approximate lower bound on the true peak"
        ),
        (
            "timings are single-run cold samples and median warm samples on one "
            "machine; machine load is not controlled"
        ),
        (
            "STEP export runs in a child process with a fresh CADService build "
            "cache, so it does not reuse definitions built by the scene sample"
        ),
    ]

    temp_folders: list[Path] = []
    try:
        if args.cases in {"both", "assembly"}:
            if (store_root / f"{args.assembly}.assembly.json").is_file():
                clone_folder = Path(tempfile.mkdtemp(prefix="brepx-preview-store-"))
                temp_folders.append(clone_folder)
                clone_root = clone_folder / "store"
                clone = _clone_store(store_root, clone_root)
                source_scene = _source_scene_bytes(args.assembly, store_root)
                case = _measure_case(
                    store=Store(clone_root),
                    assembly_id=args.assembly,
                    source="clone of the source store without cached scenes",
                    setup={"store_clone": clone},
                    source_scene_cache_bytes=source_scene,
                    warm_repeats=args.warm_repeats,
                    bom_repeats=args.bom_repeats,
                    measure_export=not args.skip_export,
                    export_timeout=args.export_timeout_seconds,
                )
                cases["turbofan"] = case
                limitations.append(
                    "the turbofan sample runs on a copy of the source store; the "
                    "copy excludes scenes/, so the cold scene rebuilds all 183 "
                    "definitions and the real store is not written to"
                )
            else:
                cases["turbofan"] = {
                    "available": False,
                    "assembly_id": args.assembly,
                    "reason": f"no {args.assembly}.assembly.json under the store",
                }
                limitations.append(
                    f"assembly {args.assembly} is absent from the store, so no "
                    "turbofan-scale sample was recorded; the fixture sample stands "
                    "in for it"
                )

        if args.cases in {"both", "fixture"}:
            fixture_folder = Path(tempfile.mkdtemp(prefix="brepx-preview-fixture-"))
            temp_folders.append(fixture_folder)
            store, assembly_id = _build_fixture(fixture_folder)
            cases["seven_instance_fixture"] = _measure_case(
                store=store,
                assembly_id=assembly_id,
                source="temporary store built from the assembly plan path",
                setup=None,
                source_scene_cache_bytes=None,
                warm_repeats=args.warm_repeats,
                bom_repeats=args.bom_repeats,
                measure_export=not args.skip_export,
                export_timeout=args.export_timeout_seconds,
            )
            limitations.append(
                "the 7-instance fixture is an assembly plan of one disk plus a "
                "six-instance polar blade pattern (7 leaf instances, 2 definitions) "
                "built in a temporary store; it is not a document from the source "
                "store"
            )
    finally:
        if not args.keep_temp:
            for folder in temp_folders:
                shutil.rmtree(folder, ignore_errors=True)

    payload = {
        "schema": SCHEMA,
        "recorded_at": datetime.now(UTC).isoformat(),
        "command": "python "
        + " ".join([str(Path(__file__).resolve().relative_to(ROOT)), *sys.argv[1:]]),
        "environment": environment,
        "cases": cases,
        "limitations": limitations,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"wrote {output}")
    for name, case in cases.items():
        if not case.get("available"):
            print(f"{name}: unavailable ({case.get('reason')})")
            continue
        scene = case["scene"]
        bom = case["bom"]
        export = case["export"]
        print(
            f"{name}: scene cold {scene['cold']['seconds']} s / "
            f"{scene['cold']['bytes']} B, warm {scene['warm']['seconds_median']} s; "
            f"bom {bom['seconds_median']} s / {bom['bytes']} B; "
            f"export {export.get('seconds')} s / {export.get('output_bytes')} B "
            f"({export.get('status')})"
        )
    return 0 if cases else 1


def _source_scene_bytes(assembly_id: str, store_root: Path) -> int | None:
    # Read the assembly file directly: Store.get_assembly would write a version
    # snapshot into the source store, and this measurement only reads from it.
    path = store_root / f"{assembly_id}.assembly.json"
    if not path.is_file():
        return None
    try:
        import hashlib

        version = int(json.loads(path.read_text(encoding="utf-8")).get("version") or 0)
        key = f"assembly-scene:{assembly_id}:{version}"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        scene_path = store_root / "scenes" / f"{digest}.json"
        return scene_path.stat().st_size if scene_path.is_file() else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure assembly scene/BOM/export size and time."
    )
    parser.add_argument("--store", default=DEFAULT_STORE)
    parser.add_argument("--assembly", default=DEFAULT_ASSEMBLY)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--cases", choices=("both", "assembly", "fixture"), default="both"
    )
    parser.add_argument("--warm-repeats", type=int, default=3)
    parser.add_argument("--bom-repeats", type=int, default=3)
    parser.add_argument(
        "--export-timeout-seconds", type=float, default=DEFAULT_EXPORT_TIMEOUT
    )
    parser.add_argument("--skip-export", action="store_true")
    parser.add_argument("--keep-temp", action="store_true")
    parser.add_argument("--export-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--export-file", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--export-result", default=None, help=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.export_worker:
        if not args.export_file or not args.export_result:
            raise SystemExit("--export-worker needs --export-file and --export-result")
        return _export_worker(args)
    return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
