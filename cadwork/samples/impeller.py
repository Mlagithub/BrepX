"""The impeller document rebuilt from generated kernel actions.

No part-specific step lives in the registry: the hub is a polygon revolved
about Z, a blade is a rectangle placed on YZ, leaned, translated and wrapped,
the sections are lofted, the blade is patterned, and the fluid domain is the
padded cavity adapter.  This file replaces the old 30-step ``hub_revolve`` /
``blade_loft`` macros.
"""

from __future__ import annotations

from cadwork.design.document import Document, Feature, Filter, Ref, validate_layout


def _feature(fid: str, typ: str, params: dict | None = None,
             refs: dict | None = None, note: str = "") -> Feature:
    return Feature(fid, typ, params=params or {}, refs=refs or {}, note=note)


def impeller_document(
    count: int = 9,
    wrap: float = 30.0,
    fillet_radius: float = 0.3,
    sections: int = 5,
    r_env: float = 2.0,
    z_pad: float = 2.0,
    name: str = "Impeller",
) -> Document:
    features: list[Feature] = [
        _feature("h1", "k_polygon",
                 {"points": [[0.0, 0.0], [45.0, 0.0], [45.0, -4.0], [0.0, -4.0]]},
                 note="back disc profile in the XZ plane"),
        _feature("h1p", "place_on", {"plane": "XZ"}, {"shape": Ref("h1", "self")},
                 note="revolve needs the axis in the sketch plane"),
        _feature("h2", "k_revolve", {"angle": 360.0, "axis": "Z"},
                 {"profile": Ref("h1p", "self")}, note="back disc"),
    ]

    section_ids: list[str] = []
    for index in range(sections):
        u = index / (sections - 1)
        lean = 25.0 + 10.0 * u
        radius = 18.0 + 26.0 * u
        base = f"b{index}"
        features.extend([
            _feature(f"{base}a", "k_rectangle", {"width": 3.0, "height": 20.0}),
            _feature(f"{base}b", "place_on", {"plane": "YZ"}, {"shape": Ref(f"{base}a", "self")}),
            _feature(f"{base}c", "k_rotate", {"axis": "X", "angle": lean},
                     {"target": Ref(f"{base}b", "self")}),
            _feature(f"{base}d", "k_translate", {"x": radius, "y": 0.0, "z": 10.0},
                     {"target": Ref(f"{base}c", "self")}),
            _feature(f"{base}e", "k_rotate", {"axis": "Z", "angle": wrap * u},
                     {"target": Ref(f"{base}d", "self")}),
        ])
        section_ids.append(f"{base}e")

    features.append(_feature(
        "b_loft", "k_loft", {},
        {"sections": tuple(Ref(fid, "self") for fid in section_ids)},
        note="one twisted blade",
    ))
    features.append(_feature(
        "b_pattern", "pattern", {"kind": "circular", "count": count, "radius": 0.0},
        {"target": Ref("b_loft", "self")}, note="blade array",
    ))
    features.append(_feature(
        "b_fuse", "k_fuse", {},
        {"target": Ref("h2", "self"), "others": (Ref("b_pattern", "self"),)},
        note="hub + blades",
    ))
    features.append(_feature(
        "b_fillet", "k_fillet", {"radius": fillet_radius},
        {"target": Ref("b_fuse", "self"),
         "edges": Ref("b_fuse", "edges", (Filter("nearest", args=([44.0, 0.0, 20.0],)),))},
        note="round one blade edge",
    ))
    features.extend([
        _feature("t_in", "tag_boundary", {"name": "inlet", "kind": "inlet"},
                 {"target": Ref("b_fillet", "self"),
                  "faces": Ref("b_fillet", "faces", (Filter("nearest", args=([0.0, 0.0, 0.0],)),))}),
        _feature("t_out", "tag_boundary", {"name": "outlet", "kind": "outlet"},
                 {"target": Ref("b_fillet", "self"),
                  "faces": Ref("b_fillet", "faces", (Filter("largest"),))}),
        _feature("t_wall", "tag_boundary", {"name": "wall", "kind": "wall"},
                 {"target": Ref("b_fillet", "self"),
                  "faces": Ref("b_fillet", "faces", (Filter("planar"),))}),
        _feature("c1", "cavity", {"r_env": r_env, "z_pad": z_pad},
                 {"target": Ref("b_fillet", "self")}, note="fluid domain"),
    ])

    document = Document(id="impeller", name=name, features=tuple(features))
    validate_layout(document)
    return document
