"""The hollow blade: one twisted loft, then a shell.

All steps are generated kernel actions; the blade-specific numbers live here,
not in the registry.
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
    features: list[Feature] = []
    section_ids: list[str] = []
    for index in range(sections):
        u = index / (sections - 1)
        base = f"s{index}"
        features.extend(
            [
                Feature(
                    f"{base}a", "k_rectangle", params={"width": t, "height": b_out}
                ),
                Feature(
                    f"{base}b",
                    "place_on",
                    params={"plane": "YZ"},
                    refs={"shape": Ref(f"{base}a", "self")},
                ),
                Feature(
                    f"{base}c",
                    "k_rotate",
                    params={"axis": "X", "angle": 25.0 + 10.0 * u},
                    refs={"target": Ref(f"{base}b", "self")},
                ),
                Feature(
                    f"{base}d",
                    "k_translate",
                    params={"x": 18.0 + 26.0 * u, "y": 0.0, "z": b_out / 2.0},
                    refs={"target": Ref(f"{base}c", "self")},
                ),
                Feature(
                    f"{base}e",
                    "k_rotate",
                    params={"axis": "Z", "angle": wrap * u},
                    refs={"target": Ref(f"{base}d", "self")},
                ),
            ]
        )
        section_ids.append(f"{base}e")

    features.extend(
        [
            Feature(
                "b_loft",
                "k_loft",
                {},
                refs={"sections": tuple(Ref(fid, "self") for fid in section_ids)},
            ),
            Feature(
                "b_shell",
                "k_shell",
                params={"thickness": thickness, "outward": False, "corners": "round"},
                refs={"target": Ref("b_loft", "self")},
            ),
        ]
    )
    document = Document(id="blade", name=name, features=tuple(features))
    validate_layout(document)
    return document
