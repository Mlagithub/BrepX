"""Materialize a nested STEP file as part and assembly documents.

The parser owns structure and placements; this module only maps each unique
product name to its local geometry and creates the document instances. Bodies
returned by the kernel are already placed, so each definition is returned to its
local frame by the inverse of the placement of the occurrence it came from.
"""

from __future__ import annotations

import tempfile
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import smlibpy as s
from smlibpy import Location

from cadwork.design.assembly import (
    AssemblyDocument,
    AssemblyRef,
    Instance,
    PartRef,
    Transform,
    new_assembly_document,
)
from cadwork.design.step_import import StepAssemblyGraph, StepNode, parse_step_structure


def _location(placement: Any) -> Location:
    matrix = np.eye(4)
    matrix[:3, :3] = np.array(placement.rotation, dtype=float)
    matrix[:3, 3] = np.array(placement.translation, dtype=float)
    return Location(matrix)


def _safe_name(name: str, fallback: str) -> str:
    cleaned = " ".join((name or "").split()).strip()
    return cleaned or fallback


def import_step_documents(
    service: Any, path: str, name_prefix: str = "step"
) -> dict[str, Any]:
    """Create one part document per unique product and the nested assemblies."""
    graph: StepAssemblyGraph = parse_step_structure(path)
    bodies = list(s.import_step(path))
    bodies_by_name: dict[str, list[Any]] = defaultdict(list)
    for body in bodies:
        bodies_by_name[body.name].append(body)
    instances_by_child: dict[str, list[Any]] = defaultdict(list)
    instances_by_parent: dict[str, list[Any]] = defaultdict(list)
    for instance in graph.instances:
        instances_by_child[instance.child_definition_id].append(instance)
        instances_by_parent[instance.parent_definition_id].append(instance)

    part_ids: dict[str, str] = {}
    missing: list[str] = []
    part_count = 0
    for node in graph.nodes:
        if node.kind != "part":
            continue
        name = _safe_name(node.name, f"{name_prefix}_part_{part_count}")
        group = bodies_by_name.get(node.name, [])
        instances = instances_by_child.get(node.definition_id, [])
        if not group or not instances:
            missing.append(node.name)
            continue
        body = group[0]
        local = body.moved(_location(instances[0].placement).inverse())
        with tempfile.TemporaryDirectory() as folder:
            step_path = Path(folder) / "part.step"
            s.export_step(local, str(step_path))
            payload = step_path.read_bytes()
        document = service.store.create(name)
        service.import_bytes(document.id, f"{name}.step", payload, format="step")
        part_ids[node.definition_id] = document.id
        part_count += 1

    assembly_ids: dict[str, str] = {}
    assembly_documents: dict[str, AssemblyDocument] = {}
    for node in graph.nodes:
        if node.kind == "assembly":
            assembly = new_assembly_document(
                _safe_name(node.name, f"{name_prefix}_assembly")
            )
            assembly_ids[node.definition_id] = assembly.id
            assembly_documents[node.definition_id] = assembly

    def instances_for(node: StepNode) -> tuple[Instance, ...]:
        items: list[Instance] = []
        for occurrence in instances_by_parent.get(node.definition_id, []):
            child = graph.node(occurrence.child_definition_id)
            if child.kind == "part":
                part_id = part_ids.get(child.definition_id)
                if part_id is None:
                    continue
                ref = PartRef(part_id, 1)
            else:
                assembly_id = assembly_ids.get(child.definition_id)
                if assembly_id is None:
                    continue
                ref = AssemblyRef(assembly_id, 1)
            items.append(
                Instance(
                    id=f"i{occurrence.occurrence_id}",
                    ref=ref,
                    placement=Transform(
                        rotation=occurrence.placement.rotation,
                        translation=occurrence.placement.translation,
                    ),
                    name=occurrence.name,
                )
            )
        return tuple(items)

    for node in sorted(
        (item for item in graph.nodes if item.kind == "assembly"),
        key=lambda item: item.depth,
        reverse=True,
    ):
        document = assembly_documents[node.definition_id]
        service.store.save_assembly(replace(document, instances=instances_for(node)))

    root_id = (
        assembly_ids.get(graph.root_definition_ids[0])
        if graph.root_definition_ids
        else None
    )
    return {
        "root_assembly_id": root_id,
        "parts": part_ids,
        "assemblies": assembly_ids,
        "part_documents": len(part_ids),
        "assembly_documents": len(assembly_ids),
        "missing_geometry": missing,
        "depth": graph.depth,
        "leaf_instances": graph.leaf_instance_count,
    }


__all__ = ["import_step_documents"]
