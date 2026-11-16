"""Component tests for every generated-callable inventory entry.

Each case builds a minimal valid fixture in the real kernel and records the
measured result.  A case passes when the call returns a non-empty shape that
passes the kernel validity check; a small number of calls are contract tests
for a documented refusal.
"""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import smlibpy as K

from cadwork.design.kernel_inventory import inventory

GEN_KEYS = tuple(
    f"{record['owner']}.{record['name']}"
    for record in inventory()
    if record["destination"] == "GEN"
)


def _box() -> Any:
    return K.Box(40, 40, 20)


def _box2() -> Any:
    return K.Box(40, 40, 20).translate(10, 0, 0)


def _cyl() -> Any:
    return K.Cylinder(10, 30)


def _thin() -> Any:
    return K.Box(60, 30, 2, align=(K.Align.CENTER, K.Align.CENTER, K.Align.MIN))


def _rect() -> Any:
    return K.Rectangle(20, 10)


def _rect2() -> Any:
    return K.Rectangle(20, 10).translate(5, 0)


def _face() -> Any:
    return _box().faces().top().one()


def _side() -> Any:
    return _box().faces().right().one()


def _shell() -> Any:
    return _face().to_shell()


def _box_edge() -> Any:
    return list(_box().edges())[0]


def _top_edge(part: Any) -> Any:
    return [edge for edge in part.edges() if abs(edge.center().z - 2.0) < 1e-6][0]


def _bend_line() -> Any:
    return K.Line((-30, 0, 2), (30, 0, 2))


def _bent() -> Any:
    return K.fold(_thin(), _bend_line(), 90, radius=2)


def _split_faces() -> tuple[Any, Any, Any]:
    face = _box().faces().top().one()
    f1, f2 = list(face.split(K.Line((-20, 0, 10), (20, 0, 10))))
    sheet = K.stitch(f1.to_shell(), f2.to_shell())
    return sheet, f1, f2


def _blend_edges() -> tuple[Any, Any]:
    a = K.Box(20, 20, 1).faces().top().one().to_shell()
    b = a.translate(0, 20, 10)
    edge_a = [edge for edge in a.edges() if abs(edge.center().y - 10) < 1e-6][0]
    edge_b = [edge for edge in b.edges() if abs(edge.center().y - 30) < 1e-6][0]
    return edge_a, edge_b


def _profile_xz() -> Any:
    return K.Rectangle(20, 10).translate(20, 0).on(K.Plane.XZ)


def _ring() -> Any:
    return (
        K.Cylinder(52, 40)
        - K.Cylinder(50, 50)
        - K.Box(60, 60, 50, align=(K.Align.MIN, K.Align.MIN, K.Align.CENTER))
    )


def _floor_wall() -> tuple[Any, Any]:
    floor = K.Box(40, 40, 2).faces().top().one()
    wall = K.Box(2, 40, 20).translate(0, 0, 11).faces().right().one()
    return floor, wall


@dataclass(frozen=True)
class Case:
    key: str
    run: Callable[[], Any]
    expect_error: str | None = None
    note: str = ""


def _cases() -> dict[str, Case]:
    cases: dict[str, Case] = {}

    def add(
        key: str,
        run: Callable[[], Any],
        expect_error: str | None = None,
        note: str = "",
    ) -> None:
        cases[key] = Case(key, run, expect_error, note)

    for name, run in {
        "AnnularSector": lambda: K.AnnularSector(10, 20, 5, 180),
        "ArcSlot": lambda: K.ArcSlot(20, 6, 90),
        "Bezier": lambda: K.Bezier((0, 0), (10, 10), (20, 0)),
        "Box": _box,
        "CenterArc": lambda: K.CenterArc((0, 0), 10, 0, 90),
        "Circle": lambda: K.Circle(5),
        "Cone": lambda: K.Cone(10, 5, 20),
        "ConicArc": lambda: K.ConicArc((0, 0), (10, 5), (20, 0)),
        "CounterBoreHole": lambda: K.CounterBoreHole(3, 6, 2, 10),
        "CounterSinkHole": lambda: K.CounterSinkHole(3, 6, 10, 82),
        "Cylinder": lambda: K.Cylinder(10, 20),
        "Ellipse": lambda: K.Ellipse(10, 5),
        "EllipticalArc": lambda: K.EllipticalArc((0, 0), 10, 5, 0, 180),
        "FilletPolyline": lambda: K.FilletPolyline((0, 0), (10, 0), (10, 10), radius=2),
        "Helix": lambda: K.Helix(5, 20, 10),
        "Hole": lambda: K.Hole(3, 10),
        "Hull": lambda: K.Hull(K.Rectangle(10, 10), K.Circle(5).translate(20, 0)),
        "HyperbolicArc": lambda: K.HyperbolicArc((0, 0), 10, 5, 0, 1),
        "Line": lambda: K.Line((0, 0), (10, 10)),
        "ParabolicArc": lambda: K.ParabolicArc((0, 0), 5, 0, 10),
        "PolarLine": lambda: K.PolarLine((0, 0), 10, 45),
        "Polygon": lambda: K.Polygon((0, 0), (10, 0), (10, 10)),
        "Polyline": lambda: K.Polyline((0, 0), (10, 0), (10, 10)),
        "Pyramid": lambda: K.Pyramid(10, 10, 15),
        "RadiusArc": lambda: K.RadiusArc((0, 0), (10, 0), 10),
        "Rectangle": _rect,
        "RegularPolygon": lambda: K.RegularPolygon(10, 6),
        "RoundedRectangle": lambda: K.RoundedRectangle(10, 20, 2),
        "SagittaArc": lambda: K.SagittaArc((0, 0), (10, 0), 2),
        "Slot": lambda: K.Slot(20, 5),
        "Sphere": lambda: K.Sphere(10),
        "Spiral": lambda: K.Spiral(5, 20, 3),
        "Spline": lambda: K.Spline((0, 0), (5, 5), (10, 0)),
        "Stroke": lambda: K.Stroke(K.Line((0, 0), (20, 0)), 2),
        "TangentArc": lambda: K.TangentArc((0, 0), (10, 0), (1, 0)),
        "Text": lambda: K.Text("A", 10),
        "ThreePointArc": lambda: K.ThreePointArc((0, 0), (5, 5), (10, 0)),
        "Torus": lambda: K.Torus(10, 2),
        "Trapezoid": lambda: K.Trapezoid(20, 10, 60, 60),
        "Triangle": lambda: K.Triangle(10, 10),
        "Wedge": lambda: K.Wedge(10, 20, 30, 5),
    }.items():
        add(f"smlibpy.{name}", run)

    add("smlibpy.bend", lambda: K.bend(_box(), 30))
    add("smlibpy.blend", lambda: K.blend(*_blend_edges()))
    add("smlibpy.chamfer", lambda: K.chamfer(_box_edge(), 1))
    add("smlibpy.cut", lambda: K.cut(_box(), _cyl()))
    add("smlibpy.draft", lambda: K.draft(_box(), _side(), 2, K.Plane.XY))
    add("smlibpy.extrude", lambda: K.extrude(_rect(), 5))
    add("smlibpy.extend", lambda: K.extend(_shell(), 5))
    add(
        "smlibpy.fill",
        lambda: K.fill(K.Polyline((0, 0), (20, 0), (20, 20), (0, 20), close=True)),
    )
    add("smlibpy.fillet", lambda: K.fillet(_box_edge(), 1))
    add("smlibpy.fit_curve", lambda: K.fit_curve([(0, 0), (5, 5), (10, 0)]))
    add("smlibpy.flange", lambda: K.flange(_thin(), _top_edge(_thin()), 20, radius=2))
    add("smlibpy.fold", lambda: K.fold(_thin(), _bend_line(), 90, radius=2))
    add("smlibpy.fuse", lambda: K.fuse(_box(), _box2()))
    add("smlibpy.imprint", lambda: K.imprint(_box(), _cyl()))
    add("smlibpy.intersect", lambda: K.intersect(_box(), _box2()))
    add("smlibpy.loft", lambda: K.loft([K.Circle(5), K.Circle(8).translate(0, 0, 10)]))
    add(
        "smlibpy.make_face",
        lambda: K.make_face(
            _face().outer_wire(), K.Circle(3).faces().one().outer_wire()
        ),
    )
    add(
        "smlibpy.match_edge",
        lambda: K.match_edge(
            *_split_faces()[:1],
            list(_split_faces()[0].edges())[0],
            list(_split_faces()[0].edges())[1],
        ),
    )
    add("smlibpy.merge", lambda: K.merge(_box(), K.Box(40, 40, 20).translate(60, 0, 0)))
    add("smlibpy.merge_faces", lambda: K.merge_faces(*_split_faces()))
    add("smlibpy.mirror", lambda: K.mirror(_box(), K.Plane.XY))
    add("smlibpy.move_faces", lambda: K.move_faces(_box(), _face(), (0, 0, 5)))
    add(
        "smlibpy.network",
        lambda: K.network(
            [K.Line((0, y, 0), (20, y, 0)) for y in (0, 10, 20)],
            [K.Line((x, 0, 0), (x, 20, 0)) for x in (0, 10, 20)],
        ),
    )
    add("smlibpy.offset", lambda: K.offset(_box(), 2))
    add("smlibpy.offset_faces", lambda: K.offset_faces(_box(), _face(), 2))
    add("smlibpy.remove_faces", lambda: K.remove_faces(_box(), _face(), partial=True))
    add("smlibpy.remove_fillets", lambda: K.remove_fillets(_box()))
    add("smlibpy.revolve", lambda: K.revolve(_profile_xz(), K.Z))
    add(
        "smlibpy.ruled",
        lambda: K.ruled(
            K.Line((0, 0, 0), (20, 0, 0)), K.Line((0, 10, 10), (20, 10, 10))
        ),
    )
    add("smlibpy.scale", lambda: K.scale(_box(), 2))
    add("smlibpy.section", lambda: K.section(_box(), K.Plane.XY))
    add("smlibpy.shell", lambda: K.shell(_box(), 2))
    add("smlibpy.split", lambda: K.split(_box(), K.Plane.XY))
    add(
        "smlibpy.stitch",
        lambda: K.stitch(
            K.Box(20, 20, 2).faces().top().one().to_shell(),
            K.Box(20, 20, 2).faces().right().one().to_shell(),
        ),
    )
    add("smlibpy.surface_fillet", lambda: K.surface_fillet(*_floor_wall(), 2))
    add("smlibpy.sweep", lambda: K.sweep(_rect(), K.Line((-20, 0, 0), (20, 0, 0))))
    add("smlibpy.swing", lambda: K.swing(_profile_xz(), K.Ellipse(30, 20)))
    add("smlibpy.taper", lambda: K.taper(_cyl(), 0.8))
    add("smlibpy.thicken", lambda: K.thicken(_shell(), 1.0))
    add("smlibpy.twist", lambda: K.twist(_cyl(), 30))
    add("smlibpy.unfold", lambda: _bent().unfold())
    add("smlibpy.unroll", lambda: _ring().unroll(radius=51))
    add("smlibpy.xor", lambda: K.xor(_rect(), _rect2()))

    add("Part.bend", lambda: _box().bend(30))
    add("Part.chamfer", lambda: _box().chamfer(_box_edge(), 1))
    add("Part.cut", lambda: _box().cut(_cyl()))
    add("Part.draft", lambda: _box().draft(_side(), 2, K.Plane.XY))
    add("Part.fillet", lambda: _box().fillet(_box_edge(), 1))
    add("Part.flange", lambda: _thin().flange(_top_edge(_thin()), 20, radius=2))
    add("Part.fold", lambda: _thin().fold(_bend_line(), 90, radius=2))
    add("Part.fuse", lambda: _box().fuse(_box2()))
    add("Part.heal", lambda: _box().heal())
    add("Part.imprint", lambda: _box().imprint(_cyl()))
    add("Part.intersect", lambda: _box().intersect(_box2()))
    add("Part.merge", lambda: _box().merge(K.Box(40, 40, 20).translate(60, 0, 0)))
    add("Part.mirror", lambda: _box().mirror(K.Plane.XY))
    add("Part.move_faces", lambda: _box().move_faces(_face(), (0, 0, 5)))
    add("Part.offset", lambda: _box().offset(2))
    add("Part.offset_faces", lambda: _box().offset_faces(_face(), 2))
    add("Part.remove_faces", lambda: _box().remove_faces(_face(), partial=True))
    add("Part.remove_fillets", lambda: _box().remove_fillets())
    add("Part.rotate", lambda: _box().rotate(K.Z, 30))
    add("Part.scale", lambda: _box().scale(2))
    add("Part.section", lambda: _box().section(K.Plane.XY))
    add("Part.shell", lambda: _box().shell(2))
    add("Part.split", lambda: _box().split(K.Plane.XY))
    add("Part.taper", lambda: _box().taper(0.8))
    add("Part.translate", lambda: _box().translate(5, 0, 0))
    add("Part.twist", lambda: _box().twist(30))
    add("Part.unfold", lambda: _bent().unfold())
    add("Part.unroll", lambda: _ring().unroll(radius=51))

    add("Shape.mirror", lambda: _box().mirror(K.Plane.XY))
    add("Shape.rotate", lambda: _box().rotate(K.Z, 30))
    add("Shape.scale", lambda: _box().scale(2))
    add("Shape.translate", lambda: _box().translate(5, 0, 0))

    add("Sketch.chamfer", lambda: _rect().chamfer(1))
    add("Sketch.cut", lambda: _rect().cut(_rect2()))
    add("Sketch.extend", lambda: _rect().extend(2))
    add("Sketch.extrude", lambda: _rect().extrude(5))
    add("Sketch.fillet", lambda: _rect().fillet(1))
    add("Sketch.flipped", lambda: _rect().flipped())
    add("Sketch.fuse", lambda: _rect().fuse(_rect2()))
    add("Sketch.heal", lambda: _rect().heal())
    add("Sketch.intersect", lambda: _rect().intersect(_rect2()))
    add(
        "Sketch.match_edge",
        lambda: _rect().match_edge(
            list(_rect().edges())[0], K.Line((-15, 0, 0), (15, 0, 0))
        ),
    )
    add("Sketch.merge_faces", lambda: K.Sketch.merge_faces(*_split_faces()))
    add("Sketch.mirror", lambda: _rect().mirror(K.Plane.XZ))
    add("Sketch.offset", lambda: _rect().offset(2))
    add("Sketch.revolve", lambda: _profile_xz().revolve(K.Z))
    add("Sketch.rotate", lambda: _rect().rotate(K.Z, 30))
    add("Sketch.scale", lambda: _rect().scale(2))
    add("Sketch.sweep", lambda: _rect().sweep(K.Line((-20, 0, 0), (20, 0, 0))))
    add("Sketch.swing", lambda: _profile_xz().swing(K.Ellipse(30, 20)))
    add("Sketch.thicken", lambda: _rect().thicken(1.0))
    add("Sketch.translate", lambda: _rect().translate(5, 0, 0))
    add("Sketch.xor", lambda: _rect().xor(_rect2()))

    add("Face.extend", lambda: _face().extend(5))
    add("Face.extrude", lambda: _face().extrude(5))
    add("Face.flipped", lambda: _face().flipped())
    add("Face.iso", lambda: _face().iso(u=0.5))
    add("Face.mirror", lambda: _face().mirror(K.Plane.XZ))
    add("Face.offset", lambda: _face().offset(2))
    add("Face.project", lambda: _face().project(K.Line((-20, 0, 10), (20, 0, 10))))
    add("Face.rotate", lambda: _face().rotate(K.Z, 30))
    add("Face.scale", lambda: _face().scale(2))
    add("Face.split", lambda: _face().split(K.Line((-20, 0, 10), (20, 0, 10))))
    add("Face.to_shell", lambda: _face().to_shell())
    add("Face.to_sketch", lambda: _face().to_sketch())
    add("Face.translate", lambda: _face().translate(5, 0, 0))
    add("Face.untrimmed", lambda: _face().untrimmed())
    add("Face.wrap", lambda: _face().wrap(_rect()))

    return cases


CASES: dict[str, Case] = _cases()
MISSING = [key for key in GEN_KEYS if key not in CASES]
EXTRA = [key for key in CASES if key not in GEN_KEYS]


def _metrics(value: Any) -> dict[str, Any]:
    if isinstance(value, tuple):
        value = value[0]
    if value is None:
        raise AssertionError("the call returned None")
    metrics: dict[str, Any] = {"type": type(value).__name__}
    for name in ("volume", "area", "length"):
        if hasattr(value, name):
            metrics[name] = float(getattr(value, name))
            break
    for name, method in (
        ("faces", "faces"),
        ("edges", "edges"),
        ("solids", "solids"),
        ("vertices", "vertices"),
    ):
        accessor = getattr(value, method, None)
        if callable(accessor):
            try:
                metrics[name] = len(accessor())
            except Exception:
                pass
    if hasattr(value, "__len__") and not isinstance(value, (str, bytes)):
        metrics["items"] = len(value)
    check = getattr(value, "is_valid", None)
    if callable(check):
        metrics["valid"] = bool(check())
        if not metrics["valid"]:
            raise AssertionError("the result is not valid")
    if "area" in metrics and metrics["area"] <= 0:
        raise AssertionError("the result has no area")
    if "length" in metrics and metrics["length"] <= 0:
        raise AssertionError("the result has no length")
    if "items" in metrics and metrics["items"] <= 0:
        raise AssertionError("the result is empty")
    return metrics


def _artifact(value: Any, path: Path) -> str | None:
    if isinstance(value, tuple):
        value = value[0]
    if not hasattr(value, "is_valid"):
        return None
    try:
        K.export_step(value, str(path))
    except Exception:
        return None
    return str(path) if path.is_file() else None


def run_case(
    key: str, evidence_dir: str | os.PathLike[str], run_id: str = ""
) -> dict[str, Any]:
    case = CASES[key]
    folder = Path(evidence_dir) / (run_id or "manual")
    folder.mkdir(parents=True, exist_ok=True)
    stem = key.replace(".", "_")
    started = time.perf_counter()
    result: dict[str, Any] = {"key": key, "run_id": run_id, "note": case.note}
    try:
        value = case.run()
        if case.expect_error:
            result.update(
                status="failed",
                error=f"expected error containing {case.expect_error!r}",
            )
        else:
            result.update(status="passed", metrics=_metrics(value))
            artifact = _artifact(value, folder / f"{stem}.step")
            if artifact:
                result["artifact"] = artifact
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        if case.expect_error and case.expect_error.lower() in message.lower():
            result.update(status="passed", expected_error=message)
        else:
            result.update(status="failed", error=message)
    result["seconds"] = round(time.perf_counter() - started, 4)
    (folder / f"{stem}.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return result


def run_all(
    evidence_dir: str | os.PathLike[str], run_id: str | None = None
) -> dict[str, Any]:
    run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
    started = time.perf_counter()
    results = [run_case(key, evidence_dir, run_id) for key in GEN_KEYS]
    summary = {
        "run_id": run_id,
        "total": len(results),
        "passed": sum(1 for item in results if item["status"] == "passed"),
        "failed": [item for item in results if item["status"] != "passed"],
        "seconds": round(time.perf_counter() - started, 2),
        "evidence_dir": str(Path(evidence_dir) / run_id),
    }
    folder = Path(evidence_dir) / run_id
    (folder / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


def _render_shape(value: Any) -> Any:
    if isinstance(value, tuple):
        value = value[0]
    if type(value).__name__ == "ShapeList":
        return list(value)
    return value


def _nonwhite_bbox(path: Path) -> tuple[int, int, int, int, int]:
    from PIL import Image

    image = Image.open(path).convert("RGB")
    pixels = image.load()
    width, height = image.size
    left, top, right, bottom = width, height, -1, -1
    total = 0
    for y in range(height):
        for x in range(width):
            red, green, blue = pixels[x, y]
            if red < 248 or green < 248 or blue < 248:
                total += 1
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)
    if right < left:
        return 0, 0, 0, 0, 0
    return right - left + 1, bottom - top + 1, total, width, height


def _render_best(shape: Any, png: Path) -> str:
    best = None
    for view in ("iso", "top", "front", "right"):
        candidate = png.with_name(f"{png.stem}.{view}.png")
        K.render(
            shape,
            path=str(candidate),
            view=view,
            size=(640, 480),
            zoom=1.15,
            edges=True,
            background="white",
        )
        bbox_w, bbox_h, total, width, height = _nonwhite_bbox(candidate)
        score = total
        if best is None or score > best[0]:
            best = (score, candidate, view, bbox_w, bbox_h, width, height)
        if view == "iso" and total > width * height * 0.05:
            best = (score, candidate, view, bbox_w, bbox_h, width, height)
            break
    assert best is not None
    _score, source, view, _bw, _bh, _width, _height = best
    shutil.copyfile(source, png)
    for view_name in ("iso", "top", "front", "right"):
        png.with_name(f"{png.stem}.{view_name}.png").unlink(missing_ok=True)
    return view


def render_case(
    key: str, evidence_dir: str | os.PathLike[str], run_id: str = ""
) -> dict[str, Any]:
    """Run one GEN case again and keep a rendered PNG of its result."""
    from PIL import Image

    case = CASES[key]
    folder = Path(evidence_dir) / (run_id or "manual")
    render_dir = folder / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    stem = key.replace(".", "_")
    png = render_dir / f"{stem}.png"
    result: dict[str, Any] = {"key": key, "run_id": run_id, "png": png.name}
    try:
        value = case.run()
        if value is None:
            raise AssertionError("the call returned None")
        shape = _render_shape(value)
        view = _render_best(shape, png)
        image = Image.open(png).convert("RGB")
        pixels = list(image.getdata())
        nonwhite = sum(
            1 for red, green, blue in pixels if red < 248 or green < 248 or blue < 248
        )
        result.update(
            status="passed",
            view=view,
            width=image.width,
            height=image.height,
            nonwhite=nonwhite,
            ratio=round(nonwhite / max(1, len(pixels)), 5),
        )
        if nonwhite < 64:
            result.update(status="failed", error="the render is blank")
    except Exception as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    (folder / f"{stem}.render.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return result


def render_all(
    evidence_dir: str | os.PathLike[str], run_id: str | None = None
) -> dict[str, Any]:
    run_id = run_id or f"render-{uuid.uuid4().hex[:8]}"
    started = time.perf_counter()
    results = [render_case(key, evidence_dir, run_id) for key in GEN_KEYS]
    summary = {
        "run_id": run_id,
        "total": len(results),
        "passed": sum(1 for item in results if item["status"] == "passed"),
        "failed": [item for item in results if item["status"] != "passed"],
        "seconds": round(time.perf_counter() - started, 2),
        "render_dir": str(Path(evidence_dir) / run_id / "render"),
    }
    folder = Path(evidence_dir) / run_id
    (folder / "renders.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary
