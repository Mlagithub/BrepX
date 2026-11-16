"""Tests for reading nested product structure out of a STEP file."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cadwork.design.step_import import (
    StepAssemblyGraph,
    StepPlacement,
    StepStructureError,
    decode_step_name,
    parse_step_structure,
)

SYNTHETIC_STEP = r"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('nested assembly fixture'),'2;1');
FILE_NAME('assembly.step','',(''),(''),'','','');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));
ENDSEC;
DATA;
#10=APPLICATION_CONTEXT('automotive design');
#11=PRODUCT_CONTEXT('',#10,'mechanical');
#12=PRODUCT_DEFINITION_CONTEXT('part definition',#10,'design');
#20=PRODUCT('root-assembly','\X2\603B\X0\\X2\88C5\X0\\X2\914D\X0\','',(#11));
#21=PRODUCT_DEFINITION_FORMATION('','',#20);
#22=PRODUCT_DEFINITION('','',#21,#12);
#23=PRODUCT_DEFINITION_SHAPE('','',#22);
#24=SHAPE_REPRESENTATION('',(#100,#101,#102),#10);
#25=SHAPE_DEFINITION_REPRESENTATION(#23,#24);
#30=PRODUCT('rotor-assembly','rotor-\X2\8F6C\X0\_01','',(#11));
#31=PRODUCT_DEFINITION_FORMATION('','',#30);
#32=PRODUCT_DEFINITION('','',#31,#12);
#33=PRODUCT_DEFINITION_SHAPE('','',#32);
#34=SHAPE_REPRESENTATION('',(#100,#103,#104,#105),#10);
#35=SHAPE_DEFINITION_REPRESENTATION(#33,#34);
#40=PRODUCT('airfoil_360x1036x394x50x22.5x0.72x57.6x0.11','airfoil_360x1036x394x50x22.5x0.72x57.6x0.11','',(#11));
#41=PRODUCT_DEFINITION_FORMATION('','',#40);
#42=PRODUCT_DEFINITION('','',#41,#12);
#43=PRODUCT_DEFINITION_SHAPE('','',#42);
#44=ADVANCED_BREP_SHAPE_REPRESENTATION('',(#100,#109),#10);
#45=SHAPE_DEFINITION_REPRESENTATION(#43,#44);
#50=PRODUCT('ring_400x80x160','ring_400x80x160','',(#11));
#51=PRODUCT_DEFINITION_FORMATION('','',#50);
#52=PRODUCT_DEFINITION('','',#51,#12);
#53=PRODUCT_DEFINITION_SHAPE('','',#52);
#54=ADVANCED_BREP_SHAPE_REPRESENTATION('',(),#10);
#55=SHAPE_DEFINITION_REPRESENTATION(#53,#54);
#60=PRODUCT('bolt_400x80x160','bolt-\X2\B7A8\X0\','',(#11));
#61=PRODUCT_DEFINITION_FORMATION('','',#60);
#62=PRODUCT_DEFINITION('','',#61,#12);
#63=PRODUCT_DEFINITION_SHAPE('','',#62);
#64=ADVANCED_BREP_SHAPE_REPRESENTATION('',(),#10);
#65=SHAPE_DEFINITION_REPRESENTATION(#63,#64);
#70=PRODUCT('cowl','\X2\00E9\X0\','',(#11));
#71=PRODUCT_DEFINITION_FORMATION('','',#70);
#72=PRODUCT_DEFINITION('','',#71,#12);
#73=PRODUCT_DEFINITION_SHAPE('','',#72);
#74=ADVANCED_BREP_SHAPE_REPRESENTATION('',(),#10);
#75=SHAPE_DEFINITION_REPRESENTATION(#73,#74);
#80=NEXT_ASSEMBLY_USAGE_OCCURRENCE('sub-1','sub-1','',#22,#32,$);
#81=NEXT_ASSEMBLY_USAGE_OCCURRENCE('sub-2','sub-2','',#22,#32,$);
#82=NEXT_ASSEMBLY_USAGE_OCCURRENCE('blade-1','\X2\98CE\X0\\X2\6247\X0\_01','',#32,#42,$);
#83=NEXT_ASSEMBLY_USAGE_OCCURRENCE('blade-2','blade-2','',#32,#42,$);
#84=NEXT_ASSEMBLY_USAGE_OCCURRENCE('blade-3','blade-3','',#32,#42,$);
#85=NEXT_ASSEMBLY_USAGE_OCCURRENCE('ring-1','ring-1','',#32,#52,$);
#86=NEXT_ASSEMBLY_USAGE_OCCURRENCE('bolt-1','bolt-1','',#22,#62,$);
#87=NEXT_ASSEMBLY_USAGE_OCCURRENCE('bolt-2','bolt-2','',#22,#62,$);
#88=NEXT_ASSEMBLY_USAGE_OCCURRENCE('cowl-1','cowl-1','',#22,#72,$);
#90=CARTESIAN_POINT('',(0.0,0.0,0.0));
#91=CARTESIAN_POINT('',(10.0,0.0,0.0));
#92=CARTESIAN_POINT('',(-10.0,0.0,0.0));
#93=CARTESIAN_POINT('',(0.0,20.0,0.0));
#94=CARTESIAN_POINT('',(0.0,-20.0,0.0));
#95=DIRECTION('',(0.0,0.0,1.0));
#96=DIRECTION('',(1.0,0.0,0.0));
#97=DIRECTION('',(0.0,1.0,0.0));
#98=CARTESIAN_POINT('',(1.0,0.0,0.0));
#100=AXIS2_PLACEMENT_3D('',#90,#95,#96);
#101=AXIS2_PLACEMENT_3D('',#91,#95,#96);
#102=AXIS2_PLACEMENT_3D('',#92,#95,#96);
#103=AXIS2_PLACEMENT_3D('',#90,#95,#97);
#104=AXIS2_PLACEMENT_3D('',#93,#95,#96);
#105=AXIS2_PLACEMENT_3D('',#94,#95,#96);
#109=AXIS2_PLACEMENT_3D('',#98,#95,#96);
#200=ITEM_DEFINED_TRANSFORMATION('','',#100,#101);
#201=ITEM_DEFINED_TRANSFORMATION('','',#102,#100);
#202=ITEM_DEFINED_TRANSFORMATION('','',#100,#103);
#203=ITEM_DEFINED_TRANSFORMATION('','',#100,#104);
#204=ITEM_DEFINED_TRANSFORMATION('','',#109,#105);
#210=(REPRESENTATION_RELATIONSHIP('','',#34,#24) REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION(#200) SHAPE_REPRESENTATION_RELATIONSHIP());
#211=(REPRESENTATION_RELATIONSHIP('','',#24,#34) REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION(#201) SHAPE_REPRESENTATION_RELATIONSHIP());
#212=(REPRESENTATION_RELATIONSHIP('','',#44,#34) REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION(#202) SHAPE_REPRESENTATION_RELATIONSHIP());
#213=(REPRESENTATION_RELATIONSHIP('','',#44,#34) REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION(#203) SHAPE_REPRESENTATION_RELATIONSHIP());
#214=(REPRESENTATION_RELATIONSHIP('','',#44,#34) REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION(#204) SHAPE_REPRESENTATION_RELATIONSHIP());
#230=PRODUCT_DEFINITION_SHAPE('Placement','Placement of an item',#80);
#231=PRODUCT_DEFINITION_SHAPE('Placement','Placement of an item',#81);
#232=PRODUCT_DEFINITION_SHAPE('Placement','Placement of an item',#82);
#233=PRODUCT_DEFINITION_SHAPE('Placement','Placement of an item',#83);
#234=PRODUCT_DEFINITION_SHAPE('Placement','Placement of an item',#84);
#240=CONTEXT_DEPENDENT_SHAPE_REPRESENTATION(#210,#230);
#241=CONTEXT_DEPENDENT_SHAPE_REPRESENTATION(#211,#231);
#242=CONTEXT_DEPENDENT_SHAPE_REPRESENTATION(#212,#232);
#243=CONTEXT_DEPENDENT_SHAPE_REPRESENTATION(#213,#233);
#244=CONTEXT_DEPENDENT_SHAPE_REPRESENTATION(#214,#234);
ENDSEC;
END-ISO-10303-21;
"""

TURBOFAN_STEP = Path(
    r"C:\Users\keep_\.dsh\attachments\v1\files\da"
    r"\da2b14796b3a77457e6c54d8b42b3b7f8ce2f43f9ea8ccf08da95b309c58bf0d"
    r"\双转子涡扇航空发动机完整三维装配（1_10）.step"
)


def _parse_text(text: str) -> StepAssemblyGraph:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "assembly.step"
        path.write_text(text, encoding="utf-8")
        return parse_step_structure(path)


IDENTITY_ROTATION = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)


def _assert_placement(
    test_case: unittest.TestCase,
    placement: StepPlacement,
    rotation: tuple[tuple[float, float, float], ...],
    translation: tuple[float, float, float],
    places: int = 9,
) -> None:
    for expected_row, actual_row in zip(rotation, placement.rotation):
        for expected, actual in zip(expected_row, actual_row):
            test_case.assertAlmostEqual(actual, expected, places=places)
    for expected, actual in zip(translation, placement.translation):
        test_case.assertAlmostEqual(actual, expected, places=places)


class StepStructureClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = _parse_text(SYNTHETIC_STEP)

    def test_counts_assemblies_parts_and_depth(self) -> None:
        self.assertEqual(self.graph.product_count, 6)
        self.assertEqual(self.graph.assembly_count, 2)
        self.assertEqual(self.graph.part_count, 4)
        self.assertEqual(self.graph.depth, 3)
        self.assertEqual(self.graph.root_definition_ids, (22,))

    def test_node_kind_comes_from_shape_representation(self) -> None:
        self.assertEqual(self.graph.node(22).kind, "assembly")
        self.assertEqual(self.graph.node(32).kind, "assembly")
        self.assertEqual(self.graph.node(42).kind, "part")
        self.assertEqual(self.graph.node(52).kind, "part")
        self.assertEqual(self.graph.node(62).kind, "part")
        self.assertEqual(self.graph.node(72).kind, "part")

    def test_nesting_depth_is_one_based(self) -> None:
        self.assertEqual(self.graph.node(22).depth, 1)
        self.assertEqual(self.graph.node(32).depth, 2)
        self.assertEqual(self.graph.node(42).depth, 3)

    def test_parent_and_child_edges_are_exposed(self) -> None:
        self.assertEqual(self.graph.node(22).parent_definition_ids, ())
        self.assertEqual(self.graph.node(22).child_definition_ids, (32, 62, 72))
        self.assertEqual(self.graph.node(32).parent_definition_ids, (22,))
        self.assertEqual(self.graph.node(32).child_definition_ids, (42, 52))
        self.assertEqual(self.graph.node(42).parent_definition_ids, (32,))
        self.assertEqual(self.graph.node(42).child_definition_ids, ())
        self.assertEqual(len(self.graph.instances), 9)
        self.assertEqual(
            [instance.occurrence_id for instance in self.graph.instances],
            [80, 81, 82, 83, 84, 85, 86, 87, 88],
        )

    def test_leaf_instances_multiply_through_repeated_subassemblies(self) -> None:
        self.assertEqual(self.graph.leaf_instance_count, 11)
        self.assertEqual(self.graph.node(32).instance_count, 2)
        self.assertEqual(self.graph.node(32).leaf_instance_count, 4)
        self.assertEqual(self.graph.node(42).instance_count, 6)
        self.assertEqual(self.graph.node(52).instance_count, 2)
        self.assertEqual(self.graph.node(62).instance_count, 2)
        self.assertEqual(self.graph.node(72).instance_count, 1)
        self.assertEqual(self.graph.node(22).leaf_instance_count, 11)

    def test_missing_definition_is_rejected(self) -> None:
        broken = SYNTHETIC_STEP.replace("#22,#32,$", "#22,#999,$")
        with self.assertRaises(StepStructureError):
            _parse_text(broken)

    def test_file_without_product_definitions_is_rejected(self) -> None:
        with self.assertRaises(StepStructureError):
            _parse_text("ISO-10303-21;HEADER;ENDSEC;DATA;ENDSEC;")


class StepPlacementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = _parse_text(SYNTHETIC_STEP)
        self.instances = {
            instance.occurrence_id: instance for instance in self.graph.instances
        }

    def test_translation_placement_in_both_relationship_orders(self) -> None:
        first = self.instances[80]
        second = self.instances[81]
        _assert_placement(self, first.placement, IDENTITY_ROTATION, (10.0, 0.0, 0.0))
        _assert_placement(self, second.placement, IDENTITY_ROTATION, (-10.0, 0.0, 0.0))
        self.assertEqual(first.placement_source, "step")
        self.assertEqual(second.placement_source, "step")

    def test_ninety_degree_rotation_is_applied(self) -> None:
        instance = self.instances[82]
        _assert_placement(
            self,
            instance.placement,
            ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
            (0.0, 0.0, 0.0),
        )
        self.assertEqual(instance.placement_source, "step")

    def test_child_frame_is_inverted_before_composition(self) -> None:
        instance = self.instances[84]
        _assert_placement(
            self,
            instance.placement,
            IDENTITY_ROTATION,
            (-1.0, -20.0, 0.0),
        )

    def test_repeated_instances_keep_distinct_placements(self) -> None:
        placements = {
            (
                self.instances[occurrence_id].placement.rotation,
                self.instances[occurrence_id].placement.translation,
            )
            for occurrence_id in (82, 83, 84)
        }
        self.assertEqual(len(placements), 3)

    def test_missing_relationship_keeps_explicit_identity(self) -> None:
        for occurrence_id in (85, 86, 87, 88):
            instance = self.instances[occurrence_id]
            self.assertEqual(instance.placement_source, "identity")
            self.assertEqual(instance.placement, StepPlacement())

    def test_unresolvable_relationship_is_explicit(self) -> None:
        broken = SYNTHETIC_STEP.replace(
            "REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION(#200)",
            "REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION(#299)",
        )
        graph = _parse_text(broken)
        instance = next(item for item in graph.instances if item.occurrence_id == 80)
        self.assertEqual(instance.placement_source, "unresolved")
        self.assertEqual(instance.placement, StepPlacement())

    def test_direction_falls_back_to_representation_item_order(self) -> None:
        without_links = SYNTHETIC_STEP.replace(
            "#25=SHAPE_DEFINITION_REPRESENTATION(#23,#24);\n", ""
        ).replace("#35=SHAPE_DEFINITION_REPRESENTATION(#33,#34);\n", "")
        graph = _parse_text(without_links)
        instances = {instance.occurrence_id: instance for instance in graph.instances}
        _assert_placement(
            self, instances[80].placement, IDENTITY_ROTATION, (10.0, 0.0, 0.0)
        )
        _assert_placement(
            self, instances[81].placement, IDENTITY_ROTATION, (-10.0, 0.0, 0.0)
        )

    def test_instance_json_matches_rotation_translation_shape(self) -> None:
        payload = self.graph.json()
        instance = next(
            item for item in payload["instances"] if item["occurrence_id"] == 82
        )
        self.assertEqual(
            instance["placement"],
            {
                "rotation": [
                    [0.0, -1.0, 0.0],
                    [1.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0],
                ],
                "translation": [0.0, 0.0, 0.0],
            },
        )
        self.assertEqual(instance["placement_source"], "step")

    def test_four_by_four_matrix_is_available(self) -> None:
        matrix = StepPlacement(
            rotation=((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
            translation=(1.0, 2.0, 3.0),
        ).matrix
        self.assertEqual(
            matrix[0],
            (0.0, -1.0, 0.0, 1.0),
        )
        self.assertEqual(
            matrix[3],
            (0.0, 0.0, 0.0, 1.0),
        )


class StepNameDecodingTests(unittest.TestCase):
    def test_utf16be_code_units_decode_to_han_text(self) -> None:
        escaped = r"\X2\603B\X0\\X2\88C5\X0\\X2\914D\X0" "\\"
        self.assertEqual(decode_step_name(escaped), "总装配")

    def test_gbk_bytes_inside_x2_escape_decode_to_han_text(self) -> None:
        self.assertEqual(decode_step_name("bolt-" r"\X2\B7A8\X0" "\\"), "bolt-法")

    def test_ascii_and_generator_names_are_preserved_verbatim(self) -> None:
        name = "airfoil_360x1036x394x50x22.5x0.72x57.6x0.11"
        self.assertEqual(decode_step_name(name), name)

    def test_non_cjk_escape_falls_back_to_raw_spelling(self) -> None:
        escaped = r"\X2\00E9\X0" "\\"
        self.assertEqual(decode_step_name(escaped), escaped)

    def test_product_and_occurrence_names_are_decoded(self) -> None:
        graph = _parse_text(SYNTHETIC_STEP)
        self.assertEqual(graph.node(22).name, "总装配")
        self.assertEqual(graph.node(32).name, "rotor-转_01")
        self.assertEqual(graph.node(62).name, "bolt-法")
        self.assertEqual(graph.node(72).name, r"\X2\00E9\X0" "\\")
        self.assertEqual(graph.instances[2].name, "风扇_01")


class StepGraphSerializationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = _parse_text(SYNTHETIC_STEP)

    def test_summary_reports_structure_counts(self) -> None:
        summary = self.graph.summary()
        self.assertEqual(summary["product_count"], 6)
        self.assertEqual(summary["assembly_count"], 2)
        self.assertEqual(summary["part_count"], 4)
        self.assertEqual(summary["leaf_instance_count"], 11)
        self.assertEqual(summary["instance_edge_count"], 9)
        self.assertEqual(summary["placed_instance_count"], 5)
        self.assertEqual(summary["identity_instance_count"], 4)
        self.assertEqual(summary["unresolved_instance_count"], 0)
        self.assertEqual(summary["depth"], 3)
        self.assertEqual(summary["root_product_names"], ["总装配"])

    def test_json_is_plain_and_complete(self) -> None:
        payload = json.loads(json.dumps(self.graph.json(), ensure_ascii=False))
        self.assertEqual(payload["depth"], 3)
        self.assertEqual(len(payload["nodes"]), 6)
        self.assertEqual(len(payload["instances"]), 9)
        root = next(node for node in payload["nodes"] if node["definition_id"] == 22)
        self.assertEqual(root["kind"], "assembly")
        self.assertEqual(root["child_definition_ids"], [32, 62, 72])
        self.assertEqual(root["leaf_instance_count"], 11)
        self.assertEqual(payload["instances"][2]["name"], "风扇_01")

    def test_unknown_definition_lookup_raises(self) -> None:
        with self.assertRaises(KeyError):
            self.graph.node(999)


class TurbofanStepStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not TURBOFAN_STEP.is_file():
            raise unittest.SkipTest("turbofan STEP is not present on this machine")
        cls.graph = parse_step_structure(TURBOFAN_STEP)

    def test_reference_counts_match_the_nested_assembly(self) -> None:
        summary = self.graph.summary()
        self.assertEqual(summary["product_count"], 195)
        self.assertEqual(summary["assembly_count"], 12)
        self.assertEqual(summary["part_count"], 183)
        self.assertEqual(summary["leaf_instance_count"], 1930)
        self.assertEqual(summary["instance_edge_count"], 1941)
        self.assertEqual(summary["depth"], 3)

    def test_every_occurrence_has_a_resolved_placement(self) -> None:
        summary = self.graph.summary()
        self.assertEqual(summary["placed_instance_count"], 1941)
        self.assertEqual(summary["identity_instance_count"], 0)
        self.assertEqual(summary["unresolved_instance_count"], 0)
        for instance in self.graph.instances:
            self.assertEqual(instance.placement_source, "step")

    def test_repeated_instances_keep_distinct_placements(self) -> None:
        groups: dict[tuple[int, int], set[tuple[object, object]]] = {}
        for instance in self.graph.instances:
            key = (instance.parent_definition_id, instance.child_definition_id)
            groups.setdefault(key, set()).add(
                (instance.placement.rotation, instance.placement.translation)
            )
        self.assertTrue(any(len(placements) > 1 for placements in groups.values()))
        non_identity = sum(
            1
            for instance in self.graph.instances
            if instance.placement != StepPlacement()
        )
        self.assertGreater(non_identity, 0)

    def test_known_ring_instance_is_offset_from_its_parent(self) -> None:
        instance = next(
            item for item in self.graph.instances if item.occurrence_id == 9922
        )
        self.assertEqual(instance.placement_source, "step")
        self.assertAlmostEqual(instance.placement.translation[0], -8.0, places=9)
        self.assertAlmostEqual(instance.placement.translation[1], 0.0, places=9)
        self.assertAlmostEqual(instance.placement.translation[2], 0.0, places=9)

    def test_reference_names_keep_escaped_and_generator_spelling(self) -> None:
        root = self.graph.node(self.graph.root_definition_ids[0])
        self.assertEqual(root.name, "双转子涡扇航空发动机完整三维装配（1:10）")
        names = {node.name for node in self.graph.nodes}
        self.assertIn("airfoil_360x1036x394x50x22.5x0.72x57.6x0.11", names)
        self.assertTrue(any(name.startswith("ring_") for name in names))
        self.assertTrue(any(name.startswith("bolt_") for name in names))


if __name__ == "__main__":
    unittest.main()
