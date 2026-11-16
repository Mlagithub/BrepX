"""The volute: a spiral centre line, a growing section, a swept casing.

Nothing in the registry knows what a volute is.  If this stops building, the
generated action set lost generality.
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
            "spiral",
            "k_spiral",
            params={
                "start_radius": r_start,
                "end_radius": r_end,
                "turns": turns,
                "plane": "XY",
                "clockwise": False,
            },
        ),
        Feature(
            "section",
            "k_rectangle",
            params={"width": width, "height": height, "fillet": 0.0},
        ),
        Feature(
            "sweep",
            "k_sweep",
            params={
                "twist": 0.0,
                "scale_start": 0.35,
                "scale_end": 1.0,
                "orient": True,
                "translational": False,
            },
            refs={"profile": Ref("section", "self"), "path": Ref("spiral", "self")},
        ),
        Feature(
            "shell",
            "k_shell",
            params={"thickness": wall, "outward": False, "corners": "round"},
            refs={"target": Ref("sweep", "self")},
        ),
    )
    document = Document(id="volute", name=name, features=features)
    validate_layout(document)
    return document
