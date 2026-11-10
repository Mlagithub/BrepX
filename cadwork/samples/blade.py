"""The hollow blade: a third part family, again only generic steps.

One twisted loft, then a shell. Nothing here is blade-specific machinery — it
is the same `blade_loft` and `shell` an impeller or a duct would use.

    python -m cadwork.demo --sample blade
"""

from __future__ import annotations

from cadwork.design.document import Document, Feature, Ref, validate_layout


def blade_document(
    wrap: float = 60.0,
    thickness: float = 1.0,
    b_out: float = 22.0,
    t: float = 3.0,
    sections: int = 6,
    name: str = "Hollow blade",
) -> Document:
    features = (
        Feature(
            "b1", "blade_loft",
            params={"r_in": 18.0, "r_out": 44.0, "b_out": b_out, "beta_in": 25.0,
                    "beta_out": 35.0, "wrap": wrap, "t": t, "sections": sections},
            note="twisted blade section",
        ),
        Feature(
            "b2", "shell",
            params={"thickness": thickness, "outward": False, "corners": "round"},
            refs={"target": Ref("b1", "self")},
            note="hollow interior",
        ),
    )
    document = Document(id="blade", name=name, features=features)
    validate_layout(document)
    return document
