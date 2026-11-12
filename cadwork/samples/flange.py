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
        Feature("plate", "k_cylinder", params={"radius": plate_radius, "height": plate_height}),
        Feature("plate_placed", "k_translate",
                params={"x": 0.0, "y": 0.0, "z": plate_height / 2.0},
                refs={"target": Ref("plate", "self")}),
        Feature("boss", "k_cylinder", params={"radius": boss_radius, "height": boss_height}),
        Feature("boss_placed", "k_translate",
                params={"x": 0.0, "y": 0.0,
                        "z": boss_height / 2.0 - plate_height / 2.0 + 3.0},
                refs={"target": Ref("boss", "self")}),
        Feature("blank", "k_fuse", refs={"target": Ref("plate_placed", "self"),
                                         "others": (Ref("boss_placed", "self"),)}),
        Feature("bore_tool", "k_cylinder",
                params={"radius": bore_radius, "height": plate_height + boss_height + 40.0}),
        Feature("bore_cut", "k_cut", refs={"target": Ref("blank", "self"),
                                           "others": (Ref("bore_tool", "self"),)}),
        Feature("bolt_tool", "k_cylinder",
                params={"radius": bolt_radius, "height": plate_height + 40.0}),
        Feature("bolt_placed", "k_translate",
                params={"x": bolt_pitch, "y": 0.0, "z": plate_height / 2.0},
                refs={"target": Ref("bolt_tool", "self")}),
        Feature("bolt_pattern", "pattern",
                params={"kind": "circular", "count": bolt_count, "radius": 0.0},
                refs={"target": Ref("bolt_placed", "self")}),
        Feature("bolt_holes", "k_cut", refs={"target": Ref("bore_cut", "self"),
                                             "others": (Ref("bolt_pattern", "self"),)}),
        Feature("chamfer", "k_chamfer", params={"length": chamfer_length},
                refs={"target": Ref("bolt_holes", "self"),
                      "edges": Ref("bolt_holes", "edges", (
                          Filter("nearest", args=([plate_radius, 0.0, plate_height / 2.0],)),
                      ))}),
    ]
    document = Document(id="flange", name=name, features=tuple(features))
    validate_layout(document)
    return document
