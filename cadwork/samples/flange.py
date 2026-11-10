"""The flange: a fourth part family, built from the everyday CAD operations.

Primitives, a join, a bore, a circular pattern of bolt holes, and a chamfer —
the vocabulary a typical modeller offers, not anything flange-specific.

    python -m cadwork.demo --sample flange
"""

from __future__ import annotations

from cadwork.design.document import Document, Feature, Filter, Ref, validate_layout


def flange_document(
    plate_radius: float = 60.0,
    plate_height: float = 12.0,
    boss_radius: float = 28.0,
    boss_height: float = 34.0,
    bore_radius: float = 14.0,
    bolt_count: int = 8,
    bolt_radius: float = 5.0,
    chamfer_length: float = 1.5,
    name: str = "Flange",
) -> Document:
    bolt_pitch = plate_radius - 15.0
    features = (
        Feature(
            "p1", "solid_cylinder",
            params={"radius": plate_radius, "height": plate_height,
                    "x": 0.0, "y": 0.0, "z": 0.0},
            note="plate",
        ),
        Feature(
            "p2", "solid_cylinder",
            params={"radius": boss_radius, "height": boss_height,
                    "x": 0.0, "y": 0.0, "z": boss_height / 2.0 - plate_height / 2.0 + 3.0},
            note="boss, sunk 3 mm into the plate",
        ),
        Feature(
            "p3", "boolean",
            params={"kind": "join"},
            refs={"target": Ref("p1", "self"), "tool": Ref("p2", "self")},
        ),
        Feature(
            "p4", "solid_cylinder",
            params={"radius": bore_radius, "height": plate_height + boss_height + 40.0,
                    "x": 0.0, "y": 0.0, "z": 0.0},
            note="through bore",
        ),
        Feature(
            "p5", "boolean",
            params={"kind": "cut"},
            refs={"target": Ref("p3", "self"), "tool": Ref("p4", "self")},
        ),
        Feature(
            "p6", "solid_cylinder",
            params={"radius": bolt_radius, "height": plate_height + 20.0,
                    "x": bolt_pitch, "y": 0.0, "z": 0.0},
            note="one bolt hole on the pitch circle",
        ),
        Feature(
            "p7", "pattern_circular",
            params={"count": bolt_count},
            refs={"target": Ref("p6", "self")},
        ),
        Feature(
            "p8", "boolean",
            params={"kind": "cut"},
            refs={"target": Ref("p5", "self"), "tool": Ref("p7", "self")},
        ),
        Feature(
            "p9", "chamfer",
            params={"length": chamfer_length},
            refs={
                "target": Ref("p8", "self"),
                "edges": Ref("p8", "edges", (
                    Filter("nearest", args=([plate_radius, 0.0, plate_height / 2.0],)),
                )),
            },
            note="outer top rim",
        ),
    )
    document = Document(id="flange", name=name, features=features)
    validate_layout(document)
    return document
