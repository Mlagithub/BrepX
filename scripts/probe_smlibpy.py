"""M0 probe: validate the smlibpy capabilities the architecture depends on.

Standalone. No project imports. Run:

    python scripts/probe_smlibpy.py

Writes JSON + PNG + STEP under docs/probe/.
"""

from __future__ import annotations

import json
import os
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

import smlibpy as s

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "probe")


# ---------------------------------------------------------------- harness

@dataclass
class Probe:
    name: str
    ok: bool
    seconds: float = 0.0
    detail: Any = None
    error: str | None = None


RESULTS: list[Probe] = []


def run(name: str, fn: Callable[[], Any]) -> Any:
    t0 = time.perf_counter()
    try:
        value = fn()
        RESULTS.append(Probe(name, True, time.perf_counter() - t0))
        print(f"[ok]   {name} ({RESULTS[-1].seconds:.3f}s)")
        return value
    except Exception as exc:  # noqa: BLE001 - probe records every failure
        RESULTS.append(
            Probe(name, False, time.perf_counter() - t0, error=f"{type(exc).__name__}: {exc}")
        )
        print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
        return None


def capability_report() -> dict[str, bool]:
    """Presence of the APIs the design names. Absent is a design input, not a crash."""
    part = s.Part
    edges = s.ShapeList
    faces = s.ShapeList
    checks = {
        # geometry
        "s.revolve": callable(getattr(s, "revolve", None)),
        "s.loft": callable(getattr(s, "loft", None)),
        "s.sweep": callable(getattr(s, "sweep", None)),
        "s.merge": callable(getattr(s, "merge", None)),
        "s.fillet": callable(getattr(s, "fillet", None)),
        "s.render": callable(getattr(s, "render", None)),
        "s.export_step": callable(getattr(s, "export_step", None)),
        "s.export_stl": callable(getattr(s, "export_stl", None)),
        # part
        "Part.is_valid": hasattr(part, "is_valid"),
        "Part.volume": hasattr(part, "volume"),
        "Part.mass_properties": hasattr(part, "mass_properties"),
        "Part.heal": hasattr(part, "heal"),
        "Part.check": hasattr(part, "check"),          # 0.6; may be absent
        "Part.faces/edges/vertices": all(hasattr(part, n) for n in ("faces", "edges", "vertices")),
        "Part.mesh": hasattr(part, "mesh"),
        "Part.solids": hasattr(part, "solids"),
        # selection
        "ShapeList.top": hasattr(edges, "top"),
        "ShapeList.nearest": hasattr(edges, "nearest"),
        "ShapeList.concave": hasattr(edges, "concave"),
        "ShapeList.convex": hasattr(edges, "convex"),
        "ShapeList.cylinders": hasattr(faces, "cylinders"),
        "ShapeList.planar": hasattr(faces, "planar"),
        "ShapeList.largest": hasattr(faces, "largest"),
        "ShapeList.filter_by": hasattr(edges, "filter_by"),
        "ShapeList.new": hasattr(edges, "new"),          # history-based; 0.6
        "ShapeList.derived_from": hasattr(edges, "derived_from"),
        # mesh
        "Mesh.triangles": hasattr(s.Mesh, "triangles"),
        "Mesh.is_closed": hasattr(s.Mesh, "is_closed"),
    }
    return checks


# ---------------------------------------------------------------- features

def hub_revolve(r_out: float = 45.0, z_out: float = 25.0, back_t: float = 4.0) -> Any:
    profile = [(0.0, 0.0), (r_out, z_out), (r_out, z_out - back_t), (0.0, -back_t)]
    return s.revolve(s.Polygon(*profile).on(s.Plane.XZ), s.Z)


def blade_loft(
    r_in: float = 18.0,
    r_out: float = 45.0,
    span: float = 16.0,
    thickness: float = 3.0,
    wrap_deg: float = 30.0,
    sections: int = 5,
    z_root: float = 4.0,
) -> Any:
    shapes = []
    for i in range(sections):
        t = i / (sections - 1)
        radius = r_in + t * (r_out - r_in)
        z = z_root + t * 20.0
        shapes.append(
            s.Rectangle(span, thickness)
            .on(s.Plane.XY)
            .translate(radius, 0.0, z)
            .rotate(s.Z, t * wrap_deg)
        )
    return s.loft(shapes)


def pattern(part: Any, count: int) -> Any:
    return s.merge(s.PolarLocations(0.0, count) * part)


def build_impeller(count: int = 9, wrap_deg: float = 30.0) -> dict[str, Any]:
    marks: dict[str, float] = {}
    t0 = time.perf_counter()
    hub = hub_revolve()
    marks["hub"] = time.perf_counter() - t0
    t1 = time.perf_counter()
    blade = blade_loft(wrap_deg=wrap_deg)
    marks["blade"] = time.perf_counter() - t1
    t2 = time.perf_counter()
    blades = pattern(blade, count)
    marks["pattern"] = time.perf_counter() - t2
    t3 = time.perf_counter()
    impeller = hub.fuse(blades)
    marks["fuse"] = time.perf_counter() - t3
    marks["total"] = time.perf_counter() - t0
    return {"hub": hub, "blade": blade, "blades": blades, "impeller": impeller, "marks": marks}


# ---------------------------------------------------------------- selectors

SELECTORS: dict[str, Callable[[Any], Any]] = {
    "faces().top()": lambda p: p.faces().top(),
    "faces().planar()": lambda p: p.faces().planar(),
    "faces().largest()": lambda p: p.faces().largest(),
    "faces().nearest([0,0,25])": lambda p: p.faces().nearest([0.0, 0.0, 25.0]),
    "edges().concave()": lambda p: p.edges().concave(),
    "edges().convex()": lambda p: p.edges().convex(),
}


def selector_report(part: Any) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for name, fn in SELECTORS.items():
        try:
            value = fn(part)
            n = len(value) if hasattr(value, "__len__") else 1
            report[name] = {"ok": True, "hits": n}
        except Exception as exc:  # noqa: BLE001 - probe records every failure
            report[name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return report


# ---------------------------------------------------------------- main

def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    print(f"smlibpy {getattr(s, '__version__', '?')} @ {s.__file__}")

    caps = capability_report()
    print("\n--- capabilities ---")
    for name, present in caps.items():
        print(f"  {'yes' if present else 'NO '}  {name}")

    print("\n--- build 9 features (count=9) ---")
    t0 = time.perf_counter()
    parts = run("build impeller", lambda: build_impeller(count=9))
    total = time.perf_counter() - t0
    if parts is None:
        write_report({"capabilities": caps, "build": "failed", "probes": [p.__dict__ for p in RESULTS]})
        return 1

    imp = parts["impeller"]
    print(f"  stages: {parts['marks']}")
    print(f"  valid={imp.is_valid()} volume={imp.volume:.1f} "
          f"faces={len(imp.faces())} edges={len(imp.edges())}")

    mesh = run("impeller mesh", lambda: imp.mesh())
    if mesh is not None:
        print(f"  mesh triangles={len(mesh.triangles)} vertices={len(mesh.vertices)} "
              f"closed={mesh.is_closed()}")

    face_mesh = run("per-face mesh", lambda: [(f, f.mesh()) for f in imp.faces()])
    if face_mesh is not None:
        print(f"  {len(face_mesh)} faces meshed, first has {len(face_mesh[0][1].triangles)} triangles")

    print("\n--- selectors on final part ---")
    sel9 = selector_report(imp)
    for name, value in sel9.items():
        print(f"  {name}: {value}")

    print("\n--- fillet ---")
    run(
        "fillet all concave r=2.0 (expected failure)",
        lambda: imp.fillet(imp.edges().concave(), 2.0),
    )
    single = run("fillet one concave edge r=0.3", lambda: imp.fillet(imp.edges().concave().first, 0.3))
    if single is not None:
        print(f"  valid={single.is_valid()} faces={len(single.faces())}")

    print("\n--- topology for flow-domain extraction ---")
    run("solids", lambda: print(f"  solids={len(imp.solids())}"))
    run("cells", lambda: print(f"  cells={len(imp.cells())}"))

    print("\n--- rebuild with count=11 (selector stability, before any render) ---")
    parts11 = run("build impeller count=11", lambda: build_impeller(count=11))
    sel11 = selector_report(parts11["impeller"]) if parts11 else {}
    for name in SELECTORS:
        a, b = sel9.get(name), sel11.get(name)
        print(f"  {name}: 9 -> {a and a.get('hits')} | 11 -> {b and b.get('hits')}")

    print("\n--- visual check ---")
    shots = {
        "iso": dict(view="iso"),
        "drawing": dict(view="front", drawing="first-angle"),
        "section": dict(view="iso", section=s.Plane.XZ),
        "zebra": dict(view="iso", zebra=True),
    }
    for name, kwargs in shots.items():
        run(f"render {name}", lambda kw=kwargs: s.render(imp, path=os.path.join(OUT, f"{name}.png"),
                                                         size=(900, 700), **kw))

    print("\n--- export ---")
    run("export step", lambda: s.export_step(imp, os.path.join(OUT, "impeller.step")))
    run("export stl", lambda: s.export_stl(imp, os.path.join(OUT, "impeller.stl")))

    print("\n--- render side effect on later builds ---")
    clean = parts11["marks"]["total"] if parts11 else float("nan")
    t0 = time.perf_counter()
    build_impeller(count=11)
    warm = time.perf_counter() - t0
    print(f"  rebuild 11 blades: before-renders={clean:.3f}s after-4-renders={warm:.3f}s "
          f"ratio={warm / clean:.1f}x")

    report = {
        "smlibpy": getattr(s, "__version__", "?"),
        "capabilities": caps,
        "build_seconds": total,
        "stages_9": parts["marks"],
        "stages_11": parts11["marks"] if parts11 else None,
        "final": {
            "valid": imp.is_valid(),
            "volume": imp.volume,
            "faces": len(imp.faces()),
            "edges": len(imp.edges()),
        },
        "mesh": None if mesh is None else {
            "triangles": len(mesh.triangles),
            "vertices": len(mesh.vertices),
            "closed": bool(mesh.is_closed()),
        },
        "selectors_9": sel9,
        "selectors_11": sel11,
        "render_side_effect": {"clean": clean, "after_4_renders": warm,
                               "ratio": warm / clean if clean else None},
        "probes": [p.__dict__ for p in RESULTS],
    }
    write_report(report)
    print(f"\nreport -> {os.path.join(OUT, 'report.json')}")
    return 0


def write_report(report: dict[str, Any]) -> None:
    path = os.path.join(OUT, "report.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, default=str)


if __name__ == "__main__":
    raise SystemExit(main())
