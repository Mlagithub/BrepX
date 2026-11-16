"""Parameterized part documents assembled from generated kernel actions.

Each public function returns a Document, never geometry: the build replays the
feature list. The public arguments are the dimensions a drawing gives
(diameters, lengths, spans), while feature parameters are the kernel's own
coordinates (radii, axis positions), so every conversion lives here once.

Every feature below is an exact analytic primitive, a boolean of primitives, or
a loft of interpolated profiles; nothing is decided by a tessellation. The
volume each docstring states is therefore arithmetic about the result, not a
snapshot of one.

Part-producing features already carry the kernel validity, solid, watertight
and positive-volume checks, and those checks run before an output can become a
final body. A separate check node would repeat them behind the failure it is
meant to describe, so these documents do not carry one.
"""

from __future__ import annotations

import math

from .document import Document, Feature, ParameterSpec, Ref, validate_layout

# A through-cut tool must be longer than the body it crosses. Scaling by the
# body height keeps the margin useful at every size, and the extra length is
# only on the tool, so the ring's own volume stays exact.
_BORE_TOOL_FACTOR = 3.0

# Chordwise stations of one section. Cosine spacing clusters them at both ends,
# where the leading-edge curvature and the trailing-edge closure are decided;
# 41 stations put the section area within a thousandth of a percent of the
# analytic NACA thickness integral, which is far below what the loft resolves.
_SECTION_STATIONS = 41

# The camber line of a 4-digit section is two parabolic segments meeting at its
# peak. The API exposes one camber number, so the peak position is fixed at 40%
# chord: that is the conventional 4-digit peak, and moving it would not be
# expressible.
_CAMBER_POSITION = 0.4


def _positive(name: str, value: float) -> float:
    """Reject a dimension that cannot describe solid geometry."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {value!r}")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{name} must be positive and finite, got {value!r}")
    return number


def _section_points(
    chord: float, thickness_ratio: float, camber: float
) -> list[list[float]]:
    """One closed NACA 4-digit section: chord along +X, thickness along Y, mm.

    The trailing-edge coefficient -0.1036 (rather than the classical -0.1015)
    makes the thickness vanish at the trailing edge, so the upper and lower
    surfaces meet at one point and the returned loop is closed instead of having
    a slit there. Points are ordered upper surface from the leading edge to the
    trailing edge, then lower surface back, with the duplicated leading and
    trailing edge points removed.

    Failure mode: a loop that is not simple (self-crossing) cannot be closed
    into a face, so the face feature rejects it at build time rather than the
    loft producing a torn body.
    """
    stations = [
        0.5 * (1.0 - math.cos(math.pi * index / (_SECTION_STATIONS - 1)))
        for index in range(_SECTION_STATIONS)
    ]
    upper: list[list[float]] = []
    lower: list[list[float]] = []
    for x in stations:
        thickness = (
            5.0
            * thickness_ratio
            * (
                0.2969 * math.sqrt(x)
                - 0.1260 * x
                - 0.3516 * x * x
                + 0.2843 * x**3
                - 0.1036 * x**4
            )
        )
        if camber == 0.0:
            line = 0.0
            slope = 0.0
        elif x < _CAMBER_POSITION:
            line = camber / _CAMBER_POSITION**2 * (2.0 * _CAMBER_POSITION * x - x * x)
            slope = 2.0 * camber / _CAMBER_POSITION**2 * (_CAMBER_POSITION - x)
        else:
            line = (
                camber
                / (1.0 - _CAMBER_POSITION) ** 2
                * (1.0 - 2.0 * _CAMBER_POSITION + 2.0 * _CAMBER_POSITION * x - x * x)
            )
            slope = (
                2.0 * camber / (1.0 - _CAMBER_POSITION) ** 2 * (_CAMBER_POSITION - x)
            )
        angle = math.atan(slope)
        # Offsetting along the camber normal is what keeps the thickness
        # perpendicular to the mean line instead of to the chord.
        offset_x = -thickness * math.sin(angle)
        offset_y = thickness * math.cos(angle)
        upper.append([(x + offset_x) * chord, (line + offset_y) * chord, 0.0])
        lower.append([(x - offset_x) * chord, (line - offset_y) * chord, 0.0])
    return upper + lower[-2:0:-1]


def ring(
    outer_diameter: float, inner_diameter: float, height: float, name: str = "ring"
) -> Document:
    """A straight ring: a cylinder minus a coaxial bore of the same height.

    Volume is pi * (R^2 - r^2) * height. The bore tool spans three times the
    ring height, so any height up to that margin still cuts through both faces;
    past it the bore becomes blind, which is the only way this construction can
    degrade.

    Raises ValueError when a dimension is not positive or the bore is at least
    as wide as the ring, since that cut would leave no material.
    """
    outer_radius = _positive("outer_diameter", outer_diameter) / 2.0
    inner_radius = _positive("inner_diameter", inner_diameter) / 2.0
    height = _positive("height", height)
    if inner_radius >= outer_radius:
        raise ValueError(
            "inner_diameter must be smaller than outer_diameter, "
            "otherwise the bore removes the whole ring"
        )
    features = (
        Feature(
            "ring_outer",
            "k_cylinder",
            params={"radius": outer_radius, "height": height},
        ),
        Feature(
            "ring_tool",
            "k_cylinder",
            params={"radius": inner_radius, "height": height * _BORE_TOOL_FACTOR},
        ),
        Feature(
            "ring_body",
            "k_cut",
            refs={
                "target": Ref("ring_outer", "self"),
                "others": (Ref("ring_tool", "self"),),
            },
        ),
    )
    document = Document(
        id="ring",
        name=name,
        features=features,
        parameters=(
            ParameterSpec(
                "outer_radius",
                "ring_outer",
                "radius",
                default=outer_radius,
                unit="mm",
                description="outer radius; the generator takes its diameter",
            ),
            ParameterSpec(
                "inner_radius",
                "ring_tool",
                "radius",
                default=inner_radius,
                unit="mm",
                description="bore radius; the generator takes its diameter",
            ),
            ParameterSpec("height", "ring_outer", "height", default=height, unit="mm"),
        ),
    )
    validate_layout(document)
    return document


def bolt(
    shank_diameter: float,
    length: float,
    head_diameter: float,
    head_height: float,
    name: str = "bolt",
) -> Document:
    """A bolt: a shank cylinder with a head cylinder fused onto one end.

    The shank spans z in [0, length] and the head continues from z = length, so
    the part is length + head_height long; volume is the two cylinders summed,
    pi/4 * (shank_diameter^2 * length + head_diameter^2 * head_height).

    Raises ValueError when a dimension is not positive.
    """
    shank_radius = _positive("shank_diameter", shank_diameter) / 2.0
    length = _positive("length", length)
    head_radius = _positive("head_diameter", head_diameter) / 2.0
    head_height = _positive("head_height", head_height)
    features = (
        Feature(
            "bolt_shank",
            "k_cylinder",
            params={"radius": shank_radius, "height": length},
        ),
        Feature(
            "bolt_shank_placed",
            "k_translate",
            params={"x": 0.0, "y": 0.0, "z": length / 2.0},
            refs={"target": Ref("bolt_shank", "self")},
        ),
        Feature(
            "bolt_head",
            "k_cylinder",
            params={"radius": head_radius, "height": head_height},
        ),
        Feature(
            "bolt_head_placed",
            "k_translate",
            params={"x": 0.0, "y": 0.0, "z": length + head_height / 2.0},
            refs={"target": Ref("bolt_head", "self")},
        ),
        Feature(
            "bolt_body",
            "k_fuse",
            refs={
                "target": Ref("bolt_shank_placed", "self"),
                "others": (Ref("bolt_head_placed", "self"),),
            },
        ),
    )
    # The axial dimensions are not exposed: each is paired with a placement
    # offset (length / 2 and length + head_height / 2), so driving only the
    # cylinder height would detach that end from the other body and split the
    # fuse. A configuration can override the height and its offset together.
    document = Document(
        id="bolt",
        name=name,
        features=features,
        parameters=(
            ParameterSpec(
                "shank_radius",
                "bolt_shank",
                "radius",
                default=shank_radius,
                unit="mm",
                description="shank radius; the generator takes its diameter",
            ),
            ParameterSpec(
                "head_radius",
                "bolt_head",
                "radius",
                default=head_radius,
                unit="mm",
                description="head radius; the generator takes its diameter",
            ),
        ),
    )
    validate_layout(document)
    return document


def airfoil(
    chord: float,
    span: float,
    thickness_ratio: float = 0.12,
    camber: float = 0.0,
    sections: int = 5,
    name: str = "airfoil",
) -> Document:
    """A wing segment: closed airfoil sections lofted across the span.

    Chord runs along +X, thickness along Y and span along +Z, so the body spans
    z in [0, span]. Every station carries the same section, which makes the
    result prismatic: volume equals section area times span.

    The section shape and the station offsets are baked into point coordinates
    and placement values, so changing chord, span, thickness or camber means
    regenerating the document; no single feature parameter carries them. The
    generator therefore exposes no driving parameters, and its input checking
    is the only guard.

    Raises ValueError when a dimension is not positive, camber is not finite, or
    there are fewer than two sections (a loft needs a section at each end).
    """
    chord = _positive("chord", chord)
    span = _positive("span", span)
    thickness_ratio = _positive("thickness_ratio", thickness_ratio)
    camber = float(camber)
    if not math.isfinite(camber):
        raise ValueError(f"camber must be finite, got {camber!r}")
    sections = int(sections)
    if sections < 2:
        raise ValueError(f"sections must be at least 2, got {sections}")

    points = _section_points(chord, thickness_ratio, camber)
    features: list[Feature] = []
    for index in range(sections):
        curve_id = f"section_{index}_curve"
        face_id = f"section_{index}_face"
        placed_id = f"section_{index}_placed"
        station = span * index / (sections - 1)
        features.extend(
            (
                Feature(
                    curve_id,
                    "k_spline",
                    params={
                        "points": [list(point) for point in points],
                        "closed": True,
                    },
                ),
                # A spline is an edge and a loft section is a profile, so the closed
                # loop is closed into a face before it can be lofted. The holes role
                # must be present even when empty: the feature schema requires every
                # declared role, and an absent role is rejected before the build.
                Feature(
                    face_id,
                    "k_make_face",
                    refs={"outer": Ref(curve_id, "self"), "holes": ()},
                ),
                Feature(
                    placed_id,
                    "k_translate",
                    params={"x": 0.0, "y": 0.0, "z": station},
                    refs={"target": Ref(face_id, "self")},
                ),
            )
        )
    features.append(
        Feature(
            "airfoil_body",
            "k_loft",
            refs={
                "sections": tuple(
                    Ref(f"section_{index}_placed", "self") for index in range(sections)
                )
            },
        ),
    )
    document = Document(id="airfoil", name=name, features=tuple(features))
    validate_layout(document)
    return document
