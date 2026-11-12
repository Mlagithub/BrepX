"""The flange: primitives, a join, a bore, a bolt pattern, a chamfer.

Every step is a generated kernel action; nothing here is flange-specific
machinery.
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
    features = [
        Feature("p1", "k_cylinder", params={"radius": plate_radius, "height": plate_height}),
        Feature("p1t", "k_translate", params={"x": 0.0, "y": 0.0, "z": plate_height / 2.0},
                refs={"target": Ref("p1", "self")}),
        Feature("p2", "k_cylinder", params={"radius": boss_radius, "height": boss_height}),
        Feature("p2t", "k_translate",
                params={"x": 0.0, "y": 0.0,
                        "z": boss_height / 2.0 - plate_height / 2.0 + 3.0},
                refs={"target": Ref("p2", "self")}),
        Feature("p3", "k_fuse", refs={"target": Ref("p1t", "self"),
                                       "others": (Ref("p2t", "self"),)}),
        Feature("p4", "k_cylinder",
                params={"radius": bore_radius, "height": plate_height + boss_height + 40.0}),
        Feature("p5", "k_cut", refs={"target": Ref("p3", "self"),
                                      "others": (Ref("p4", "self"),)}),
        Feature("p6", "k_cylinder",
                params={"radius": bolt_radius, "height": plate_height + 40.0}),
        Feature("p6t", "k_translate",
                params={"x": bolt_pitch, "y": 0.0, "z": plate_height / 2.0},
                refs={"target": Ref("p6", "self")}),
        Feature("p7", "pattern", params={"kind": "circular", "count": bolt_count, "radius": 0.0},
                refs={"target": Ref("p6t", "self")}),
        Feature("p8", "k_cut", refs={"target": Ref("p5", "self"),
                                      "others": (Ref("p7", "self"),)}),
        Feature("p9", "k_chamfer", params={"length": chamfer_length},
                refs={"target": Ref("p8", "self"),
                      "edges": Ref("p8", "edges", (
                          Filter("nearest", args=([plate_radius, 0.0, plate_height / 2.0],)),
                      ))}),
    ]
    document = Document(id="flange", name=name, features=tuple(features))
    validate_layout(document)
    return document
