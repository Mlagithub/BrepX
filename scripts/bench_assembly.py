"""Measure assembly save/build/scene with a synthetic large instance set."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cadwork.design.assembly import Instance, PartRef, Transform, new_assembly_document
from cadwork.design.document import apply_ops
from cadwork.service.service import CADService
from cadwork.service.store import Store


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1930)
    parser.add_argument("--grid", type=int, default=50)
    args = parser.parse_args()
    count = max(1, args.count)
    columns = max(1, args.grid)

    with tempfile.TemporaryDirectory() as folder:
        store = Store(folder)
        service = CADService(store)
        part = store.create("bench_part")
        part = apply_ops(
            part,
            [
                {
                    "op": "add",
                    "feature": {
                        "id": "base",
                        "type": "k_box",
                        "params": {"length": 10.0, "width": 6.0, "height": 4.0},
                    },
                }
            ],
        )
        part = store.save(part)

        instances = [
            Instance(
                f"part_{index}",
                PartRef(part.id, 1),
                Transform(
                    translation=(
                        (index % columns) * 12.0,
                        ((index // columns) % 40) * 8.0,
                        0.0,
                    )
                ),
            )
            for index in range(count)
        ]
        assembly = replace(
            new_assembly_document("bench", seq=1), instances=tuple(instances)
        )

        started = time.perf_counter()
        store.save_assembly(assembly)
        save_seconds = time.perf_counter() - started

        started = time.perf_counter()
        result = service.build_assembly(assembly.id)
        build_seconds = time.perf_counter() - started

        started = time.perf_counter()
        scene = service.assembly_scene(assembly.id)
        cold_scene_seconds = time.perf_counter() - started

        started = time.perf_counter()
        service.assembly_scene(assembly.id)
        warm_scene_seconds = time.perf_counter() - started

        payload = {
            "count": count,
            "instances": len(scene["instances"]),
            "definitions": len(scene["definitions"]),
            "ok": result.ok,
            "failures": len(result.failures),
            "save_seconds": round(save_seconds, 3),
            "build_seconds": round(build_seconds, 3),
            "cold_scene_seconds": round(cold_scene_seconds, 3),
            "warm_scene_seconds": round(warm_scene_seconds, 3),
        }
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
