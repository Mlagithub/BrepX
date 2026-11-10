"""The volute: a different part family, built only from generic steps.

Nothing in the step registry knows what a volute is. If this file stops
building, the registry lost generality — not just a parameter.

    python -m cadwork.demo --sample volute
"""

from __future__ import annotations

from cadwork.design.document import Document, Feature, Ref, validate_layout


def volute_document(
    turns: float = 1.25,
    r_start: float = 30.0,
    r_end: float = 70.0,
    width: float = 8.0,
    height: float = 20.0,
    wall: float = 1.0,
    name: str = "Volute",
) -> Document:
    features = (
        Feature(
            "v1", "curve_spiral",
            params={"r_start": r_start, "r_end": r_end, "turns": turns,
                    "plane": "XY", "clockwise": False},
            note="casing centre line",
        ),
        Feature(
            "v2", "profile_rect",
            params={"width": width, "height": height, "fillet": 0.0},
            note="section at the start of the wrap",
        ),
        Feature(
            "v3", "sweep",
            params={"twist": 0.0, "scale_start": 0.35, "scale_end": 1.0,
                    "orient": True, "translational": False},
            refs={"profile": Ref("v2", "self"), "path": Ref("v1", "self")},
            note="section grows along the wrap",
        ),
        Feature(
            "v4", "shell",
            params={"thickness": wall, "outward": False, "corners": "round"},
            refs={"target": Ref("v3", "self")},
            note="casing walls; the void is the flow passage",
        ),
    )
    document = Document(id="volute", name=name, features=features)
    validate_layout(document)
    return document
