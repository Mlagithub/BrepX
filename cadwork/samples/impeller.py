"""The impeller document: nine features, the demo's single vertical slice."""

from __future__ import annotations

from cadwork.design.document import Document, Feature, Filter, Ref, validate_layout


def impeller_document(
    count: int = 9,
    wrap: float = 30.0,
    fillet_radius: float = 0.3,
    name: str = "Impeller",
) -> Document:
    features = (
        Feature(
            "f1", "hub_revolve",
            params={"r_in": 0.0, "r_out": 45.0, "z_in": 0.0, "z_out": 0.0,
                    "back_t": 4.0, "fillet_r": 0.0},
            note="back disc",
        ),
        Feature(
            "f2", "blade_loft",
            params={"r_in": 18.0, "r_out": 44.0, "b_out": 20.0, "beta_in": 25.0,
                    "beta_out": 35.0, "wrap": wrap, "t": 3.0, "sections": 5},
            note="one twisted blade",
        ),
        Feature(
            "f3", "pattern_circular",
            params={"count": count},
            refs={"target": Ref("f2", "self")},
            note="blade array",
        ),
        Feature(
            "f4", "boolean",
            params={"kind": "join"},
            refs={"target": Ref("f1", "self"), "tool": Ref("f3", "self")},
            note="hub + blades",
        ),
        Feature(
            "f5", "fillet",
            params={"radius": fillet_radius},
            refs={
                "target": Ref("f4", "self"),
                # One vertical blade edge. 2 mm fails (3 mm thick blade), 0.3 mm passes.
                "edges": Ref("f4", "edges", (Filter("nearest", args=([44.0, 0.0, 20.0],)),)),
            },
            note="round one blade edge",
        ),
        Feature(
            "f6", "tag_boundary",
            params={"name": "inlet", "kind": "inlet"},
            refs={
                "target": Ref("f5", "self"),
                "faces": Ref("f5", "faces", (Filter("nearest", args=([0.0, 0.0, 0.0],)),)),
            },
        ),
        Feature(
            "f7", "tag_boundary",
            params={"name": "outlet", "kind": "outlet"},
            refs={
                "target": Ref("f5", "self"),
                "faces": Ref("f5", "faces", (Filter("largest"),)),
            },
        ),
        Feature(
            "f8", "tag_boundary",
            params={"name": "hub_wall", "kind": "wall"},
            refs={
                "target": Ref("f5", "self"),
                "faces": Ref("f5", "faces", (Filter("planar"),)),
            },
        ),
        Feature(
            "f9", "cavity_extraction",
            params={"r_env": 0.0, "z_pad": 2.0},
            refs={"target": Ref("f5", "self")},
            note="fluid volume",
        ),
    )
    document = Document(id="impeller", name=name, features=features)
    validate_layout(document)
    return document
