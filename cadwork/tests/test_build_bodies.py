"""Every feature output is exposed as an editable body with metrics."""

from __future__ import annotations

import unittest
from dataclasses import replace

from cadwork.design import BuildCache, BuildResult, build
from cadwork.design.document import apply_ops, new_document


class BodyTreeTests(unittest.TestCase):
    def _document(self):
        document = new_document("bodies", "d_bodies")
        document = apply_ops(
            document,
            [
                {
                    "op": "add",
                    "feature": {
                        "id": "base",
                        "type": "k_box",
                        "params": {"length": 20.0, "width": 10.0, "height": 5.0},
                    },
                }
            ],
        )
        document = apply_ops(
            document,
            [
                {
                    "op": "add",
                    "feature": {
                        "id": "boss",
                        "type": "k_cylinder",
                        "params": {"radius": 3.0, "height": 10.0},
                    },
                }
            ],
        )
        document = apply_ops(
            document,
            [
                {
                    "op": "add",
                    "feature": {
                        "id": "joined",
                        "type": "k_fuse",
                        "refs": {
                            "target": {"source": "base", "select": "self"},
                            "others": [{"source": "boss", "select": "self"}],
                        },
                    },
                }
            ],
        )
        return document

    def test_body_tree_covers_features_and_metrics(self) -> None:
        result = build(self._document(), BuildCache())
        self.assertIsInstance(result, BuildResult)
        self.assertEqual(set(result.bodies), {"base", "boss", "joined"})
        self.assertEqual(result.final_feature_id, "joined")
        self.assertTrue(result.bodies["joined"].is_final)
        self.assertFalse(result.bodies["base"].is_final)
        self.assertEqual(result.bodies["joined"].inputs, ("base", "boss"))
        self.assertEqual(result.bodies["joined"].metrics["faces"], 10)
        self.assertGreater(result.bodies["joined"].metrics["volume"], 0.0)
        self.assertEqual(len(result.bodies["base"].metrics["bbox_size"]), 3)

    def test_configuration_params_are_recorded_on_the_body(self) -> None:
        document = replace(
            self._document(),
            configurations={"long": {"base": {"length": 40.0}}},
        )
        result = build(document, BuildCache(), configuration="long")
        self.assertEqual(result.bodies["base"].params["length"], 40.0)
        self.assertEqual(result.configuration, "long")

    def test_summary_contains_bodies(self) -> None:
        summary = build(self._document(), BuildCache()).summary()
        self.assertEqual(
            [item["feature_id"] for item in summary["bodies"]],
            ["base", "boss", "joined"],
        )
        self.assertTrue(summary["bodies"][-1]["is_final"])


if __name__ == "__main__":
    unittest.main()
