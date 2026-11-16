"""Aircraft domain package.

The first release owns the wing segment contract. Geometry compilers are added
by the wing stage; this package currently exposes only its design brief and
acceptance gates.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from cadwork.domains.base import BriefSchema, DomainError, FieldSpec, GateSpec


class AircraftPack:
    id = "aircraft"
    version = "0.1.0"

    def brief_schema(self) -> BriefSchema:
        return BriefSchema(
            id="aircraft-wing",
            title="外翼段设计简报",
            description="首版只覆盖翼段 OML 与主结构接口。",
            fields=(
                FieldSpec(
                    "span_mm",
                    "number",
                    required=True,
                    unit="mm",
                    minimum=1000.0,
                    description="外翼段展长",
                ),
                FieldSpec(
                    "root_chord_mm",
                    "number",
                    required=True,
                    unit="mm",
                    minimum=100.0,
                    description="翼根弦长",
                ),
                FieldSpec(
                    "tip_chord_mm",
                    "number",
                    required=True,
                    unit="mm",
                    minimum=50.0,
                    description="翼尖弦长",
                ),
                FieldSpec(
                    "sweep_deg",
                    "number",
                    required=True,
                    unit="deg",
                    minimum=-45.0,
                    maximum=45.0,
                    description="后掠角",
                ),
                FieldSpec(
                    "dihedral_deg",
                    "number",
                    unit="deg",
                    minimum=-15.0,
                    maximum=15.0,
                    default=5.0,
                    description="上反角",
                ),
                FieldSpec(
                    "root_twist_deg",
                    "number",
                    unit="deg",
                    minimum=-15.0,
                    maximum=15.0,
                    default=0.0,
                    description="翼根扭转",
                ),
                FieldSpec(
                    "tip_twist_deg",
                    "number",
                    unit="deg",
                    minimum=-15.0,
                    maximum=15.0,
                    default=0.0,
                    description="翼尖扭转",
                ),
                FieldSpec(
                    "airfoil_family",
                    "enum",
                    required=True,
                    choices=("naca4",),
                    default="naca4",
                    description="翼型族",
                ),
                FieldSpec(
                    "root_thickness_ratio",
                    "number",
                    minimum=0.04,
                    maximum=0.30,
                    default=0.14,
                    description="翼根相对厚度",
                ),
                FieldSpec(
                    "tip_thickness_ratio",
                    "number",
                    minimum=0.04,
                    maximum=0.30,
                    default=0.10,
                    description="翼尖相对厚度",
                ),
            ),
        )

    def node_kinds(self) -> Sequence[Any]:
        return ()

    def compile(
        self, node: Mapping[str, Any], context: Mapping[str, Any] | None = None
    ) -> Sequence[Mapping[str, Any]]:
        raise DomainError(
            "DOMAIN_NOT_IMPLEMENTED",
            "aircraft geometry compilers start with the wing stage",
            status=501,
        )

    def validate(
        self, document: Any, context: Mapping[str, Any] | None = None
    ) -> Sequence[Any]:
        return ()

    def components(self) -> Sequence[Any]:
        return ()

    def gates(self) -> Sequence[GateSpec]:
        return (
            GateSpec(
                id="W1",
                title="翼段 OML",
                required_checks=(
                    "valid",
                    "solid",
                    "watertight",
                    "airfoil",
                    "envelope",
                    "interface",
                ),
                approval_role="owner",
            ),
            GateSpec(
                id="W2",
                title="翼段主结构",
                required_checks=(
                    "interference",
                    "interface_alignment",
                    "mass",
                    "bom",
                ),
                approval_role="owner",
            ),
        )
