"""Read-only view of the nested product structure inside a STEP file.

The reader resolves the ISO-10303-21 entity graph far enough to expose what an
assembly document needs: PRODUCT definitions, the
NEXT_ASSEMBLY_USAGE_OCCURRENCE edges that instantiate one definition inside
another, and whether a definition carries solid B-Rep geometry (a leaf part) or
only placements (an assembly).  No geometry is evaluated and nothing is written
to the file.
"""

from __future__ import annotations

import math
import os
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

_UNKNOWN_ROLE = "unknown"

_IDENTITY_ROTATION = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)
_IDENTITY_TRANSLATION = (0.0, 0.0, 0.0)


class StepStructureError(ValueError):
    """The file cannot be read as a nested product structure."""


@dataclass(frozen=True)
class StepPlacement:
    """A rigid placement from component coordinates into parent coordinates.

    ``rotation`` is row-major and orthonormal; its columns are the placed
    frame's X/Y/Z axes expressed in the parent frame.  ``translation`` is the
    placed origin in the parent frame.  The JSON form is exactly the assembly
    document transform shape (``rotation`` plus ``translation``) so an importer
    can hand it to the document model without reshaping matrices.
    """

    rotation: tuple[tuple[float, float, float], ...] = _IDENTITY_ROTATION
    translation: tuple[float, float, float] = _IDENTITY_TRANSLATION

    @property
    def matrix(self) -> tuple[tuple[float, float, float, float], ...]:
        """The same placement as a row-major 4x4 matrix."""
        rotation = self.rotation
        translation = self.translation
        return (
            (rotation[0][0], rotation[0][1], rotation[0][2], translation[0]),
            (rotation[1][0], rotation[1][1], rotation[1][2], translation[1]),
            (rotation[2][0], rotation[2][1], rotation[2][2], translation[2]),
            (0.0, 0.0, 0.0, 1.0),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "rotation": [list(row) for row in self.rotation],
            "translation": list(self.translation),
        }


@dataclass(frozen=True)
class StepInstance:
    """One NEXT_ASSEMBLY_USAGE_OCCURRENCE edge between two definitions.

    Repeated part instances appear as one edge each and keep their own
    occurrence id, so the edge list is the place that distinguishes ten
    identical bolts from one bolt definition.  ``placement_source`` records
    whether the placement came from the file (``step``), was absent
    (``identity``), or was present but unresolvable (``unresolved``); callers
    must not treat a defaulted identity as a measured placement.
    """

    occurrence_id: int
    name: str
    parent_definition_id: int
    child_definition_id: int
    placement: StepPlacement = StepPlacement()
    placement_source: str = "identity"


@dataclass(frozen=True)
class StepNode:
    """One PRODUCT definition, either an assembly or a leaf part.

    ``depth`` is a 1-based nesting level: a top-level product definition is 1;
    a definition reused at several depths reports its deepest occurrence.
    ``leaf_instance_count`` is the number of leaf occurrences produced by a
    single instance of this node, while ``instance_count`` is the number of
    expanded occurrences of the node in the whole file.  Both count repeated
    usage and nesting, not unique definitions.
    """

    definition_id: int
    product_id: str
    name: str
    kind: str
    depth: int
    parent_definition_ids: tuple[int, ...]
    child_definition_ids: tuple[int, ...]
    instance_count: int
    leaf_instance_count: int


@dataclass(frozen=True)
class StepAssemblyGraph:
    """Neutral assembly structure parsed from one STEP file."""

    path: str
    nodes: tuple[StepNode, ...]
    instances: tuple[StepInstance, ...]
    root_definition_ids: tuple[int, ...]
    depth: int

    def node(self, definition_id: int) -> StepNode:
        for node in self.nodes:
            if node.definition_id == definition_id:
                return node
        raise KeyError(definition_id)

    @property
    def product_count(self) -> int:
        return len(self.nodes)

    @property
    def assembly_count(self) -> int:
        return sum(1 for node in self.nodes if node.kind == "assembly")

    @property
    def part_count(self) -> int:
        return sum(1 for node in self.nodes if node.kind == "part")

    @property
    def leaf_instance_count(self) -> int:
        return sum(node.instance_count for node in self.nodes if node.kind == "part")

    def json(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "depth": self.depth,
            "product_count": self.product_count,
            "assembly_count": self.assembly_count,
            "part_count": self.part_count,
            "leaf_instance_count": self.leaf_instance_count,
            "root_definition_ids": list(self.root_definition_ids),
            "nodes": [
                {
                    "definition_id": node.definition_id,
                    "product_id": node.product_id,
                    "name": node.name,
                    "kind": node.kind,
                    "depth": node.depth,
                    "parent_definition_ids": list(node.parent_definition_ids),
                    "child_definition_ids": list(node.child_definition_ids),
                    "instance_count": node.instance_count,
                    "leaf_instance_count": node.leaf_instance_count,
                }
                for node in self.nodes
            ],
            "instances": [
                {
                    "occurrence_id": instance.occurrence_id,
                    "name": instance.name,
                    "parent_definition_id": instance.parent_definition_id,
                    "child_definition_id": instance.child_definition_id,
                    "placement": instance.placement.to_json(),
                    "placement_source": instance.placement_source,
                }
                for instance in self.instances
            ],
        }

    def summary(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "depth": self.depth,
            "product_count": self.product_count,
            "assembly_count": self.assembly_count,
            "part_count": self.part_count,
            "leaf_instance_count": self.leaf_instance_count,
            "instance_edge_count": len(self.instances),
            "placed_instance_count": sum(
                1 for instance in self.instances if instance.placement_source == "step"
            ),
            "identity_instance_count": sum(
                1
                for instance in self.instances
                if instance.placement_source == "identity"
            ),
            "unresolved_instance_count": sum(
                1
                for instance in self.instances
                if instance.placement_source == "unresolved"
            ),
            "root_product_names": [
                self.node(definition_id).name
                for definition_id in self.root_definition_ids
            ],
        }


_CJK_RANGES = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0x20000, 0x2FA1F),
)

_ENTITY_TYPES = frozenset(
    {
        "PRODUCT",
        "PRODUCT_DEFINITION_FORMATION",
        "PRODUCT_DEFINITION",
        "PRODUCT_DEFINITION_WITH_ASSOCIATED_DOCUMENTS",
        "PRODUCT_DEFINITION_SHAPE",
        "SHAPE_DEFINITION_REPRESENTATION",
        "NEXT_ASSEMBLY_USAGE_OCCURRENCE",
        "SHAPE_REPRESENTATION",
        "ADVANCED_BREP_SHAPE_REPRESENTATION",
        "FACETED_BREP_SHAPE_REPRESENTATION",
        "CONTEXT_DEPENDENT_SHAPE_REPRESENTATION",
        "REPRESENTATION_RELATIONSHIP",
        "REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION",
        "SHAPE_REPRESENTATION_RELATIONSHIP",
        "ITEM_DEFINED_TRANSFORMATION",
        "AXIS2_PLACEMENT_3D",
        "CARTESIAN_POINT",
        "DIRECTION",
    }
)


@dataclass(frozen=True)
class _Entity:
    """One entity instance, simple or complex.

    A complex entity is written as a parenthesized group of partial entities
    that share one id; the placement relationship in an assembly is exactly
    such a group, so readers ask for a named part instead of assuming one type
    per entity.
    """

    parts: tuple[tuple[str, tuple[str, ...]], ...]

    def arguments(self, entity_type: str) -> tuple[str, ...] | None:
        for name, arguments in self.parts:
            if name == entity_type:
                return arguments
        return None


def _is_relevant_type(entity_type: str) -> bool:
    return entity_type in _ENTITY_TYPES or entity_type.endswith("SHAPE_REPRESENTATION")


def _entities_of(
    entities: dict[int, _Entity], entity_type: str
) -> Iterator[tuple[int, tuple[str, ...]]]:
    for entity_id, entity in entities.items():
        arguments = entity.arguments(entity_type)
        if arguments is not None:
            yield entity_id, arguments


def _contains_cjk(text: str) -> bool:
    for character in text:
        code = ord(character)
        if any(start <= code <= end for start, end in _CJK_RANGES):
            return True
    return False


def _has_raw_byte_escapes(text: str) -> bool:
    return any(0xDC80 <= ord(character) <= 0xDCFF for character in text)


def _gbk_from_raw_bytes(text: str) -> str | None:
    """Recover a name whose bytes were never escaped, only UTF-8-invalid.

    The file is decoded with ``surrogateescape`` so byte positions survive;
    only names that actually contain those surrogate code points are retried
    as GBK, which keeps ordinary UTF-8 names untouched.
    """
    if not _has_raw_byte_escapes(text):
        return None
    try:
        return text.encode("utf-8", "surrogateescape").decode("gbk")
    except UnicodeError:
        return None


def _decode_hex_group(hex_text: str, group_bytes: int, codec: str) -> str | None:
    compact = "".join(hex_text.split())
    if not compact or len(compact) % group_bytes:
        return None
    try:
        payload = bytes.fromhex(compact)
    except ValueError:
        return None
    try:
        return payload.decode(codec)
    except UnicodeError:
        return None


def _render_escapes(raw: str, x2_codec: str) -> str | None:
    """Render every escape of one ISO-10303-21 string.

    ``x2_codec`` decides how the bytes inside ``\\X2\\...\\X0\\`` groups are
    read.  The standard reading is UTF-16BE; the alternative is the raw byte
    pair read as GBK, which is what some exporters emit although the directive
    nominally means UTF-16.  Any malformed escape makes the whole rendering
    unusable so callers can fall back instead of showing a partial name.
    """
    parts: list[str] = []
    index = 0
    length = len(raw)
    while index < length:
        character = raw[index]
        if character != "\\":
            parts.append(character)
            index += 1
            continue
        if raw.startswith("\\X2\\", index):
            end = raw.find("\\X0\\", index + 4)
            if end < 0:
                return None
            rendered = _decode_hex_group(raw[index + 4 : end], 4, x2_codec)
            if rendered is None:
                return None
            parts.append(rendered)
            index = end + 4
            continue
        if raw.startswith("\\X4\\", index):
            end = raw.find("\\X0\\", index + 4)
            if end < 0:
                return None
            rendered = _decode_hex_group(raw[index + 4 : end], 8, "utf-32-be")
            if rendered is None:
                return None
            parts.append(rendered)
            index = end + 4
            continue
        if raw.startswith("\\X\\", index):
            pair = raw[index + 3 : index + 5]
            if len(pair) != 2:
                return None
            try:
                parts.append(bytes.fromhex(pair).decode("latin-1"))
            except ValueError:
                return None
            index += 5
            continue
        if raw.startswith("\\S\\", index):
            if index + 3 >= length:
                return None
            parts.append(chr(ord(raw[index + 3]) + 128))
            index += 4
            continue
        if (
            raw.startswith("\\P", index)
            and index + 3 < length
            and raw[index + 3] == "\\"
        ):
            index += 4
            continue
        if raw.startswith("\\\\", index):
            parts.append("\\")
            index += 2
            continue
        parts.append(character)
        index += 1
    return "".join(parts)


def decode_step_name(raw: str) -> str:
    """Resolve the string escapes used by ISO-10303-21 into display text.

    ``\\X2\\...\\X0\\`` groups appear in practice with two different payloads:
    standard UTF-16BE code units and GBK byte pairs written into the same
    directive.  Both readings are attempted and the one that yields a Han
    ideograph wins; the UTF-16BE reading is preferred when both qualify because
    it is the standard meaning.  Without any Han character no reading can be
    proven correct, so the raw spelling is returned instead of a guess that
    would turn an exact name into mojibake.  Names without escapes are
    returned unchanged, which keeps generator signatures byte-exact.
    """
    if "\\" not in raw:
        recovered = _gbk_from_raw_bytes(raw)
        if recovered is not None and _contains_cjk(recovered):
            return recovered
        return raw

    utf16 = _render_escapes(raw, "utf-16-be")
    if utf16 is not None and _contains_cjk(utf16):
        return utf16

    gbk = _render_escapes(raw, "gbk")
    if gbk is not None and _contains_cjk(gbk):
        return gbk

    recovered = _gbk_from_raw_bytes(raw)
    if recovered is not None and _contains_cjk(recovered):
        return recovered
    return raw


def _read_step_text(path: Path) -> str:
    data = path.read_bytes()
    return data.decode("utf-8", "surrogateescape").lstrip("\ufeff")


def _split_statements(text: str) -> Iterator[str]:
    """Yield entity statements, splitting only on semicolons outside strings.

    STEP files wrap one entity over many lines and may contain semicolons and
    doubled quote characters inside quoted names, so a plain line or semicolon
    split would cut entities in half.
    """
    start = 0
    index = 0
    length = len(text)
    while True:
        quote = text.find("'", index)
        semicolon = text.find(";", index)
        if semicolon < 0:
            return
        if quote != -1 and quote < semicolon:
            index = quote + 1
            while True:
                closing = text.find("'", index)
                if closing < 0:
                    index = length
                    break
                if closing + 1 < length and text[closing + 1] == "'":
                    index = closing + 2
                    continue
                index = closing + 1
                break
            continue
        yield text[start:semicolon]
        start = semicolon + 1
        index = start


def _split_arguments(text: str) -> tuple[str, ...]:
    arguments: list[str] = []
    depth = 0
    start = 0
    index = 0
    length = len(text)
    while index < length:
        character = text[index]
        if character == "'":
            index += 1
            while index < length:
                if text[index] == "'":
                    if index + 1 < length and text[index + 1] == "'":
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            continue
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        elif character == "," and depth == 0:
            arguments.append(text[start:index].strip())
            start = index + 1
        index += 1
    tail = text[start:].strip()
    if tail or arguments:
        arguments.append(tail)
    return tuple(arguments)


def _split_complex_parts(
    text: str,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    parts: list[tuple[str, tuple[str, ...]]] = []
    index = 0
    length = len(text)
    while index < length:
        while index < length and text[index].isspace():
            index += 1
        if index >= length:
            break
        start = index
        while index < length and (text[index].isalnum() or text[index] == "_"):
            index += 1
        entity_type = text[start:index].upper()
        if not entity_type:
            break
        while index < length and text[index].isspace():
            index += 1
        if index >= length or text[index] != "(":
            break
        arguments_start = index + 1
        depth = 1
        index += 1
        while index < length and depth:
            character = text[index]
            if character == "'":
                index += 1
                while index < length:
                    if text[index] == "'":
                        if index + 1 < length and text[index + 1] == "'":
                            index += 2
                            continue
                        index += 1
                        break
                    index += 1
                continue
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
            index += 1
        if depth:
            break
        parts.append((entity_type, _split_arguments(text[arguments_start : index - 1])))
    return tuple(parts)


def _scan_entities(text: str) -> dict[int, _Entity]:
    text = _strip_block_comments(text)
    entities: dict[int, _Entity] = {}
    for statement in _split_statements(text):
        head = statement.lstrip()
        if not head.startswith("#"):
            continue
        separator = head.find("=")
        if separator < 0:
            continue
        try:
            entity_id = int(head[1:separator].strip())
        except ValueError:
            continue
        body = head[separator + 1 :].strip()
        if not body:
            continue
        opening = body.find("(")
        if opening < 0:
            continue
        closing = body.rfind(")")
        if closing < opening:
            continue
        if body.startswith("("):
            parts = _split_complex_parts(body[1:closing])
            if not parts or not any(_is_relevant_type(name) for name, _ in parts):
                continue
            entities[entity_id] = _Entity(parts)
            continue
        entity_type = body[:opening].strip().upper()
        if not _is_relevant_type(entity_type):
            continue
        entities[entity_id] = _Entity(
            ((entity_type, _split_arguments(body[opening + 1 : closing])),)
        )
    return entities


def _strip_block_comments(text: str) -> str:
    parts: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        start = text.find("/*", index)
        if start < 0:
            parts.append(text[index:])
            break
        parts.append(text[index:start])
        end = text.find("*/", start + 2)
        if end < 0:
            break
        index = end + 2
    return "".join(parts)


def _as_string(argument: str | None) -> str | None:
    if argument is None:
        return None
    value = argument.strip()
    if len(value) < 2 or not value.startswith("'") or not value.endswith("'"):
        return None
    return value[1:-1].replace("''", "'")


def _as_reference(argument: str) -> int | None:
    value = argument.strip()
    if len(value) < 2 or not value.startswith("#"):
        return None
    try:
        return int(value[1:])
    except ValueError:
        return None


def _references(arguments: tuple[str, ...]) -> tuple[int, ...]:
    return tuple(
        reference
        for argument in arguments
        if (reference := _as_reference(argument)) is not None
    )


def _reference_list(argument: str) -> tuple[int, ...]:
    value = argument.strip()
    if value.startswith("(") and value.endswith(")"):
        value = value[1:-1]
    return _references(_split_arguments(value))


def _read_products(
    entities: dict[int, _Entity],
) -> dict[int, tuple[str, str]]:
    products: dict[int, tuple[str, str]] = {}
    for entity_id, arguments in _entities_of(entities, "PRODUCT"):
        identifier = _as_string(arguments[0]) if arguments else None
        label = _as_string(arguments[1]) if len(arguments) > 1 else None
        product_id = decode_step_name(identifier or "")
        name = decode_step_name(label or "") or product_id
        products[entity_id] = (product_id, name)
    return products


def _read_formations(
    entities: dict[int, _Entity],
) -> dict[int, int]:
    formations: dict[int, int] = {}
    for entity_id, arguments in _entities_of(entities, "PRODUCT_DEFINITION_FORMATION"):
        references = _references(arguments)
        if not references:
            raise StepStructureError(
                f"PRODUCT_DEFINITION_FORMATION #{entity_id} has no product reference"
            )
        formations[entity_id] = references[-1]
    return formations


def _read_definitions(
    entities: dict[int, _Entity],
    formations: dict[int, int],
    products: dict[int, tuple[str, str]],
) -> dict[int, int]:
    definitions: dict[int, int] = {}
    for entity_type in (
        "PRODUCT_DEFINITION",
        "PRODUCT_DEFINITION_WITH_ASSOCIATED_DOCUMENTS",
    ):
        for entity_id, arguments in _entities_of(entities, entity_type):
            references = _references(arguments)
            if not references:
                raise StepStructureError(
                    f"PRODUCT_DEFINITION #{entity_id} has no formation reference"
                )
            formation = references[0]
            product_entity = formations.get(formation)
            if product_entity is None:
                raise StepStructureError(
                    f"PRODUCT_DEFINITION #{entity_id} references unknown "
                    f"formation #{formation}"
                )
            if product_entity not in products:
                raise StepStructureError(
                    f"PRODUCT_DEFINITION #{entity_id} reaches unknown "
                    f"PRODUCT #{product_entity}"
                )
            definitions[entity_id] = product_entity
    return definitions


def _is_shape_representation_type(entity_type: str) -> bool:
    if entity_type == "CONTEXT_DEPENDENT_SHAPE_REPRESENTATION":
        return False
    return entity_type == "SHAPE_REPRESENTATION" or entity_type.endswith(
        "_SHAPE_REPRESENTATION"
    )


def _representation_role(entity_type: str) -> str:
    if entity_type == "SHAPE_REPRESENTATION":
        return "assembly"
    if entity_type.endswith("BREP_SHAPE_REPRESENTATION"):
        return "part"
    return _UNKNOWN_ROLE


def _read_shape_owners(entities: dict[int, _Entity]) -> dict[int, int]:
    owners: dict[int, int] = {}
    for entity_id, arguments in _entities_of(entities, "PRODUCT_DEFINITION_SHAPE"):
        references = _references(arguments)
        if references:
            owners[entity_id] = references[-1]
    return owners


def _read_definition_representations(
    entities: dict[int, _Entity],
    definitions: dict[int, int],
) -> dict[int, int]:
    owners = _read_shape_owners(entities)
    representations: dict[int, int] = {}
    for _entity_id, arguments in _entities_of(
        entities, "SHAPE_DEFINITION_REPRESENTATION"
    ):
        references = _references(arguments)
        if len(references) < 2:
            continue
        definition_id = owners.get(references[0])
        if definition_id in definitions:
            representations[definition_id] = references[1]
    return representations


def _read_representation_roles(
    entities: dict[int, _Entity],
    representations: dict[int, int],
) -> dict[int, str]:
    roles: dict[int, str] = {}
    for definition_id, representation_id in representations.items():
        entity = entities.get(representation_id)
        if entity is None:
            continue
        for entity_type, _arguments in entity.parts:
            if not _is_shape_representation_type(entity_type):
                continue
            role = _representation_role(entity_type)
            if role == _UNKNOWN_ROLE:
                break
            # A definition that also carries a solid representation stays a
            # part; an assembly placement cannot turn it back into an assembly.
            if roles.get(definition_id) != "part":
                roles[definition_id] = role
            break
    return roles


def _read_representation_items(
    entities: dict[int, _Entity],
) -> dict[int, tuple[int, ...]]:
    items: dict[int, tuple[int, ...]] = {}
    for entity_id, entity in entities.items():
        for entity_type, arguments in entity.parts:
            if not _is_shape_representation_type(entity_type):
                continue
            if len(arguments) > 1:
                references = _reference_list(arguments[1])
                if references:
                    items[entity_id] = references
            break
    return items


def _read_instances(
    entities: dict[int, _Entity],
) -> list[StepInstance]:
    instances: list[StepInstance] = []
    for entity_id, arguments in _entities_of(
        entities, "NEXT_ASSEMBLY_USAGE_OCCURRENCE"
    ):
        references = _references(arguments)
        if len(references) < 2:
            raise StepStructureError(
                f"NEXT_ASSEMBLY_USAGE_OCCURRENCE #{entity_id} does not name a "
                "parent and a child definition"
            )
        label = _as_string(arguments[1]) if len(arguments) > 1 else None
        instances.append(
            StepInstance(
                occurrence_id=entity_id,
                name=decode_step_name(label or ""),
                parent_definition_id=references[0],
                child_definition_id=references[1],
            )
        )
    instances.sort(key=lambda instance: instance.occurrence_id)
    return instances


def _read_cartesian_points(
    entities: dict[int, _Entity],
) -> dict[int, tuple[float, float, float]]:
    points: dict[int, tuple[float, float, float]] = {}
    for entity_id, arguments in _entities_of(entities, "CARTESIAN_POINT"):
        coordinates = _read_tuple3(arguments[1]) if len(arguments) > 1 else None
        if coordinates is not None:
            points[entity_id] = coordinates
    return points


def _read_directions(
    entities: dict[int, _Entity],
) -> dict[int, tuple[float, float, float]]:
    directions: dict[int, tuple[float, float, float]] = {}
    for entity_id, arguments in _entities_of(entities, "DIRECTION"):
        coordinates = _read_tuple3(arguments[1]) if len(arguments) > 1 else None
        if coordinates is not None:
            directions[entity_id] = coordinates
    return directions


def _read_tuple3(argument: str) -> tuple[float, float, float] | None:
    value = argument.strip()
    if not value.startswith("(") or not value.endswith(")"):
        return None
    parts = _split_arguments(value[1:-1])
    if len(parts) < 3:
        return None
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except ValueError:
        return None


def _dot(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> float:
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def _subtract(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        left[0] - right[0],
        left[1] - right[1],
        left[2] - right[2],
    )


def _scale(
    vector: tuple[float, float, float],
    factor: float,
) -> tuple[float, float, float]:
    return (vector[0] * factor, vector[1] * factor, vector[2] * factor)


def _cross(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _normalize(
    vector: tuple[float, float, float],
) -> tuple[float, float, float] | None:
    length = math.sqrt(_dot(vector, vector))
    if length <= 1e-15:
        return None
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def _placement_from_frame(
    origin: tuple[float, float, float],
    axis: tuple[float, float, float] | None,
    ref_direction: tuple[float, float, float] | None,
) -> StepPlacement | None:
    """Turn an axis placement into a rotation and translation.

    The placement's axis is its Z direction and the reference direction is an
    approximate X direction; X is orthogonalized against Z and Y completes the
    right-handed frame.  Missing directions fall back to the global Z/X axes,
    which is the STEP default for ``$`` operands.
    """
    z_axis = _normalize(axis) if axis is not None else None
    if z_axis is None:
        z_axis = (0.0, 0.0, 1.0)
    hint = ref_direction if ref_direction is not None else (1.0, 0.0, 0.0)
    x_axis = _normalize(_subtract(hint, _scale(z_axis, _dot(hint, z_axis))))
    if x_axis is None:
        alternative = (0.0, 1.0, 0.0) if abs(z_axis[0]) > 0.9 else (1.0, 0.0, 0.0)
        x_axis = _normalize(
            _subtract(alternative, _scale(z_axis, _dot(alternative, z_axis)))
        )
    if x_axis is None:
        return None
    y_axis = _normalize(_cross(z_axis, x_axis))
    if y_axis is None:
        return None
    return StepPlacement(
        rotation=(
            (x_axis[0], y_axis[0], z_axis[0]),
            (x_axis[1], y_axis[1], z_axis[1]),
            (x_axis[2], y_axis[2], z_axis[2]),
        ),
        translation=origin,
    )


def _read_axis_placements(
    entities: dict[int, _Entity],
    points: dict[int, tuple[float, float, float]],
    directions: dict[int, tuple[float, float, float]],
) -> dict[int, StepPlacement]:
    placements: dict[int, StepPlacement] = {}
    for entity_id, arguments in _entities_of(entities, "AXIS2_PLACEMENT_3D"):
        references = _references(arguments)
        if not references:
            continue
        origin = points.get(references[0])
        if origin is None:
            continue
        axis = directions.get(references[1]) if len(references) > 1 else None
        ref_direction = directions.get(references[2]) if len(references) > 2 else None
        placement = _placement_from_frame(origin, axis, ref_direction)
        if placement is not None:
            placements[entity_id] = placement
    return placements


def _read_representation_relationships(
    entities: dict[int, _Entity],
) -> dict[int, tuple[int, int, int]]:
    relationships: dict[int, tuple[int, int, int]] = {}
    for entity_id, entity in entities.items():
        relationship = entity.arguments("REPRESENTATION_RELATIONSHIP")
        transformation = entity.arguments(
            "REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION"
        )
        if relationship is None or transformation is None:
            continue
        references = _references(relationship)
        transform_references = _references(transformation)
        if len(references) < 2 or not transform_references:
            continue
        relationships[entity_id] = (
            references[0],
            references[1],
            transform_references[0],
        )
    return relationships


def _read_item_transformations(
    entities: dict[int, _Entity],
) -> dict[int, tuple[int, int]]:
    transformations: dict[int, tuple[int, int]] = {}
    for entity_id, arguments in _entities_of(entities, "ITEM_DEFINED_TRANSFORMATION"):
        references = _references(arguments)
        if len(references) >= 2:
            transformations[entity_id] = (references[0], references[1])
    return transformations


def _resolve_item_roles(
    relationship: tuple[int, int, int],
    items: tuple[int, int],
    parent_representation: int | None,
    child_representation: int | None,
    representation_items: dict[int, tuple[int, ...]],
) -> tuple[int, int] | None:
    """Return the (parent-side, child-side) items of one transformation.

    The parent definition's representation names which side holds the
    occurrence placement.  When that link is missing, the parent
    representation's item list and finally the first-item-is-the-own-frame
    convention decide the direction; an unresolvable pair returns ``None``
    rather than silently mirroring the placement.
    """
    representation_1, representation_2, _transformation = relationship
    item_1, item_2 = items
    if parent_representation is not None and child_representation is not None:
        if (
            representation_1 == parent_representation
            and representation_2 == child_representation
        ):
            return item_1, item_2
        if (
            representation_2 == parent_representation
            and representation_1 == child_representation
        ):
            return item_2, item_1

    parent_items = (
        representation_items.get(parent_representation)
        if parent_representation is not None
        else None
    )
    if parent_items is not None:
        item_1_is_parent = item_1 in parent_items
        item_2_is_parent = item_2 in parent_items
        if item_1_is_parent and not item_2_is_parent:
            return item_1, item_2
        if item_2_is_parent and not item_1_is_parent:
            return item_2, item_1

    items_1 = representation_items.get(representation_1, ())
    items_2 = representation_items.get(representation_2, ())
    item_1_is_origin = bool(items_1) and items_1[0] == item_1
    item_2_is_origin = bool(items_2) and items_2[0] == item_2
    if item_1_is_origin and not item_2_is_origin:
        return item_2, item_1
    if item_2_is_origin and not item_1_is_origin:
        return item_1, item_2
    return None


def _compose_placements(
    parent: StepPlacement,
    child: StepPlacement,
) -> StepPlacement:
    """Map child coordinates into the parent: parent frame times inverse child."""
    parent_rotation = parent.rotation
    child_rotation = child.rotation
    rotation: tuple[tuple[float, float, float], ...] = tuple(
        tuple(
            sum(parent_rotation[row][k] * child_rotation[column][k] for k in range(3))
            for column in range(3)
        )
        for row in range(3)
    )
    translation: tuple[float, float, float] = tuple(
        parent.translation[row]
        - sum(rotation[row][k] * child.translation[k] for k in range(3))
        for row in range(3)
    )
    return StepPlacement(rotation=rotation, translation=translation)


def _read_instance_placements(
    entities: dict[int, _Entity],
    instances: list[StepInstance],
    representations: dict[int, int],
) -> dict[int, tuple[StepPlacement, str]]:
    points = _read_cartesian_points(entities)
    directions = _read_directions(entities)
    frames = _read_axis_placements(entities, points, directions)
    relationships = _read_representation_relationships(entities)
    transformations = _read_item_transformations(entities)
    shape_owners = _read_shape_owners(entities)
    representation_items = _read_representation_items(entities)
    by_occurrence = {instance.occurrence_id: instance for instance in instances}
    placements: dict[int, tuple[StepPlacement, str]] = {}
    for _entity_id, arguments in _entities_of(
        entities, "CONTEXT_DEPENDENT_SHAPE_REPRESENTATION"
    ):
        references = _references(arguments)
        if len(references) < 2:
            continue
        occurrence_id = shape_owners.get(references[1])
        if occurrence_id is None:
            continue
        instance = by_occurrence.get(occurrence_id)
        if instance is None or occurrence_id in placements:
            continue
        relationship = relationships.get(references[0])
        if relationship is None:
            placements[occurrence_id] = (StepPlacement(), "unresolved")
            continue
        items = transformations.get(relationship[2])
        if items is None:
            placements[occurrence_id] = (StepPlacement(), "unresolved")
            continue
        resolved = _resolve_item_roles(
            relationship,
            items,
            representations.get(instance.parent_definition_id),
            representations.get(instance.child_definition_id),
            representation_items,
        )
        if resolved is None:
            placements[occurrence_id] = (StepPlacement(), "unresolved")
            continue
        parent_frame = frames.get(resolved[0])
        child_frame = frames.get(resolved[1])
        if parent_frame is None or child_frame is None:
            placements[occurrence_id] = (StepPlacement(), "unresolved")
            continue
        placements[occurrence_id] = (
            _compose_placements(parent_frame, child_frame),
            "step",
        )
    return placements


def _topological_order(
    children: dict[int, list[StepInstance]],
    in_degree: dict[int, int],
) -> list[int]:
    pending = dict(in_degree)
    queue = deque(
        sorted(
            definition_id for definition_id, degree in pending.items() if degree == 0
        )
    )
    order: list[int] = []
    while queue:
        definition_id = queue.popleft()
        order.append(definition_id)
        for instance in children[definition_id]:
            child = instance.child_definition_id
            pending[child] -= 1
            if pending[child] == 0:
                queue.append(child)
    return order


def _assemble_graph(
    source: str,
    products: dict[int, tuple[str, str]],
    definitions: dict[int, int],
    roles: dict[int, str],
    instances: list[StepInstance],
) -> StepAssemblyGraph:
    if not definitions:
        raise StepStructureError("no PRODUCT_DEFINITION entities found")

    children: dict[int, list[StepInstance]] = {
        definition_id: [] for definition_id in definitions
    }
    parents: dict[int, set[int]] = {
        definition_id: set() for definition_id in definitions
    }
    in_degree: dict[int, int] = {definition_id: 0 for definition_id in definitions}
    for instance in instances:
        if instance.parent_definition_id not in definitions:
            raise StepStructureError(
                f"NEXT_ASSEMBLY_USAGE_OCCURRENCE #{instance.occurrence_id} "
                f"references unknown parent definition "
                f"#{instance.parent_definition_id}"
            )
        if instance.child_definition_id not in definitions:
            raise StepStructureError(
                f"NEXT_ASSEMBLY_USAGE_OCCURRENCE #{instance.occurrence_id} "
                f"references unknown child definition "
                f"#{instance.child_definition_id}"
            )
        children[instance.parent_definition_id].append(instance)
        parents[instance.child_definition_id].add(instance.parent_definition_id)
        in_degree[instance.child_definition_id] += 1

    roots = tuple(
        sorted(
            definition_id for definition_id, degree in in_degree.items() if degree == 0
        )
    )
    if not roots:
        raise StepStructureError(
            "every product definition is a child; the occurrence graph has "
            "no top-level definition"
        )

    order = _topological_order(children, in_degree)
    if len(order) != len(definitions):
        raise StepStructureError("the product definition graph is cyclic")

    depth: dict[int, int] = {root: 1 for root in roots}
    for definition_id in order:
        for instance in children[definition_id]:
            child = instance.child_definition_id
            depth[child] = max(depth.get(child, 1), depth[definition_id] + 1)

    instance_count: dict[int, int] = {definition_id: 0 for definition_id in definitions}
    for root in roots:
        instance_count[root] = 1
    for definition_id in order:
        for instance in children[definition_id]:
            child = instance.child_definition_id
            instance_count[child] += instance_count[definition_id]

    leaf_count: dict[int, int] = {}
    for definition_id in reversed(order):
        edges = children[definition_id]
        if edges:
            leaf_count[definition_id] = sum(
                leaf_count[instance.child_definition_id] for instance in edges
            )
        else:
            leaf_count[definition_id] = 1

    nodes: list[StepNode] = []
    for definition_id in sorted(definitions):
        product_entity = definitions[definition_id]
        product_id, name = products[product_entity]
        kind = (
            "assembly"
            if children[definition_id] or roles.get(definition_id) == "assembly"
            else "part"
        )
        nodes.append(
            StepNode(
                definition_id=definition_id,
                product_id=product_id,
                name=name,
                kind=kind,
                depth=depth[definition_id],
                parent_definition_ids=tuple(sorted(parents[definition_id])),
                child_definition_ids=tuple(
                    sorted(
                        {
                            instance.child_definition_id
                            for instance in children[definition_id]
                        }
                    )
                ),
                instance_count=instance_count[definition_id],
                leaf_instance_count=leaf_count[definition_id],
            )
        )

    return StepAssemblyGraph(
        path=source,
        nodes=tuple(nodes),
        instances=tuple(instances),
        root_definition_ids=roots,
        depth=max(depth.values()),
    )


def parse_step_structure(
    path: str | os.PathLike[str],
) -> StepAssemblyGraph:
    """Read one STEP file into an assembly/part/instance tree.

    Occurrence placements are resolved from the context-dependent shape
    relationships when present; an occurrence without one keeps an explicit
    identity placement.  Only structural entities are interpreted; B-Rep
    geometry is never parsed.  Raises :class:`StepStructureError` when the file
    has no product definitions or the occurrence graph references unknown
    definitions or contains a cycle.
    """
    source = Path(path)
    entities = _scan_entities(_read_step_text(source))
    products = _read_products(entities)
    formations = _read_formations(entities)
    definitions = _read_definitions(entities, formations, products)
    representations = _read_definition_representations(entities, definitions)
    roles = _read_representation_roles(entities, representations)
    instances = _read_instances(entities)
    placements = _read_instance_placements(entities, instances, representations)
    placed: list[StepInstance] = []
    for instance in instances:
        placement, placement_source = placements.get(
            instance.occurrence_id, (StepPlacement(), "identity")
        )
        placed.append(
            replace(
                instance,
                placement=placement,
                placement_source=placement_source,
            )
        )
    return _assemble_graph(
        os.fspath(source),
        products,
        definitions,
        roles,
        placed,
    )
