"""Command submission and execution pipeline for BrepX supporting multi-body modeling."""

from __future__ import annotations

from typing import Any

from backend.core.assertions import run as run_assertions
from backend.core.command import Assertion, Command, CommandRecord
from backend.core.design import Design, next_version
from backend.core.errors import PostconditionError, PreconditionError
from backend.core.params import validate_value
from backend.core.patches import create_patch
from backend.core.snapshot import should_snapshot
from backend.selector.resolver import SelectorResolver

PRIMITIVE_OPERATORS = {
    "box",
    "cylinder",
    "sphere",
    "cone",
    "torus",
    "wedge",
    "blade_runner",
    "volute",
}

BOOLEAN_OPERATORS = {
    "boolean_cut",
    "boolean_join",
    "boolean_intersect",
}

_REDO_STACK: list[CommandRecord] = []


def validate_command(design: Design, cmd: Command, registry: Any) -> tuple[Any, dict[str, Any]]:
    spec = registry.get(cmd.op)
    validated_params: dict[str, Any] = {}
    for param_name, param_spec in spec.params.items():
        raw_val = cmd.params.get(param_name)
        val = validate_value(param_spec, raw_val)
        validated_params[param_name] = val

    if cmd.op in PRIMITIVE_OPERATORS:
        pass
    else:
        if not design.bodies and design.geometry is None:
            raise PreconditionError(f"Operator '{cmd.op}' requires existing geometry in design.")

    return spec, validated_params


def _resolve_handle_across_bodies(design: Design, expr: str) -> tuple[Any, str | None]:
    if expr.startswith("bodies["):
        end_idx = expr.find("]")
        if end_idx != -1:
            body_key = expr[7:end_idx].strip("'\"")
            inner_expr = expr[end_idx + 1 :].lstrip(".")
            body_part = design.bodies.get(body_key)
            if body_part is not None:
                if not inner_expr:
                    return body_part, body_key
                return SelectorResolver.resolve(body_part, inner_expr), body_key

    for b_id, part in design.bodies.items():
        if expr == b_id:
            return part, b_id
        try:
            return SelectorResolver.resolve(part, expr), b_id
        except Exception:
            continue

    if design.geometry is not None:
        return SelectorResolver.resolve(design.geometry, expr), design.active_body_id

    raise PreconditionError(f"Failed to resolve selector '{expr}' in any active design body.")


def resolve_command_targets(design: Design, cmd: Command) -> tuple[Any, Any, str | None, str | None]:
    target_handle = None
    tool_handle = None
    target_body_id = None
    tool_body_id = None

    if cmd.target is not None:
        target_handle, target_body_id = _resolve_handle_across_bodies(design, cmd.target.expr)

    if cmd.tool is not None:
        tool_handle, tool_body_id = _resolve_handle_across_bodies(design, cmd.tool.expr)

    return target_handle, tool_handle, target_body_id, tool_body_id


def execute(
    design: Design,
    cmd: Command,
    registry: Any,
    target_handle: Any,
    tool_handle: Any,
    target_body_id: str | None,
    tool_body_id: str | None,
    validated_params: dict[str, Any],
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    spec = registry.get(cmd.op)

    new_bodies = dict(design.bodies)
    active_body_id = design.active_body_id

    if cmd.op in PRIMITIVE_OPERATORS:
        new_geometry = spec.call(None, None, None, validated_params)
        body_count = len(new_bodies) + 1
        new_body_id = f"body_{body_count}"
        new_bodies[new_body_id] = new_geometry
        active_body_id = new_body_id
    elif cmd.op in BOOLEAN_OPERATORS:
        target_geom = target_handle or design.get_body(target_body_id)
        tool_geom = tool_handle or design.get_body(tool_body_id)
        if target_geom is None or tool_geom is None:
            raise PreconditionError(f"Operator '{cmd.op}' requires both target and tool bodies.")

        new_geometry = spec.call(target_geom, target_handle, tool_handle, validated_params)
        eff_target_id = target_body_id or design.active_body_id or "body_1"
        new_bodies[eff_target_id] = new_geometry
        if tool_body_id and tool_body_id in new_bodies and tool_body_id != eff_target_id:
            del new_bodies[tool_body_id]
        active_body_id = eff_target_id
    else:
        current_geom = design.get_body(target_body_id)
        new_geometry = spec.call(current_geom, target_handle, tool_handle, validated_params)
        eff_id = target_body_id or design.active_body_id or "body_1"
        new_bodies[eff_id] = new_geometry
        active_body_id = eff_id

    vol = float(getattr(new_geometry, "volume", 0.0))
    face_count = len(list(getattr(new_geometry, "faces")())) if hasattr(new_geometry, "faces") else 0
    valid_fn = getattr(new_geometry, "is_valid", lambda: False)
    is_valid = bool(valid_fn())

    summary = {
        "volume": vol,
        "face_count": face_count,
        "is_valid": is_valid,
        "body_id": active_body_id,
        "total_bodies": len(new_bodies),
    }
    return new_bodies, active_body_id, summary


def merge_assertions(
    default_assertions: tuple[Assertion, ...], explicit_assertions: tuple[Assertion, ...]
) -> tuple[Assertion, ...]:
    seen: set[tuple[str, tuple[Any, ...]]] = set()
    merged: list[Assertion] = []

    for item in (*default_assertions, *explicit_assertions):
        key = (item.name, item.args)
        if key not in seen:
            seen.add(key)
            merged.append(item)

    return tuple(merged)


def submit(design: Design, cmd: Command, registry: Any) -> Design:
    for record in design.journal:
        if record.command.idempotency_key == cmd.idempotency_key:
            return design

    spec, validated_params = validate_command(design, cmd, registry)
    target_handle, tool_handle, target_body_id, tool_body_id = resolve_command_targets(design, cmd)

    new_bodies, active_body_id, summary = execute(
        design,
        cmd,
        registry,
        target_handle,
        tool_handle,
        target_body_id,
        tool_body_id,
        validated_params,
    )

    active_geom = new_bodies.get(active_body_id)
    assertions = merge_assertions(spec.default_assertions, cmd.expect)
    failures = run_assertions(active_geom, design.get_body(target_body_id), assertions)
    if failures:
        raise PostconditionError(
            assertion_name="assertion_suite",
            actual=failures,
            expected=[],
            suggestion="Check operator inputs or prior geometry boundary conditions.",
        )

    _REDO_STACK.clear()

    new_version = next_version(design.version)
    new_record = CommandRecord(command=cmd, version=new_version, result_summary=summary)

    new_journal = list(design.journal)
    new_journal.append(new_record)

    snapshots_store = design.snapshots
    if should_snapshot(new_version):
        snapshots_store.put(new_version, active_geom)

    new_patches = list(design.patches)
    if cmd.op == "tag_boundary" and cmd.target is not None:
        p_name = str(validated_params.get("name", "boundary_1"))
        p_type = str(validated_params.get("semantic_type", "inlet"))
        area = float(getattr(target_handle, "area", 0.0))
        patch_obj = create_patch(
            patch_id=f"patch_{cmd.command_id}",
            name=p_name,
            semantic_type=p_type,
            selector_expr=cmd.target.expr,
            area=area,
        )
        new_patches = [p for p in new_patches if p.selector_expr != cmd.target.expr]
        new_patches.append(patch_obj)

    return Design(
        version=new_version,
        journal=new_journal,
        snapshots=snapshots_store,
        patches=new_patches,
        geometry=active_geom,
        bodies=new_bodies,
        active_body_id=active_body_id,
    )


def replay(records: list[CommandRecord], registry: Any) -> Design:
    temp_design = Design.empty()

    for record in records:
        cmd = record.command
        spec, validated_params = validate_command(temp_design, cmd, registry)
        target_handle, tool_handle, target_body_id, tool_body_id = resolve_command_targets(temp_design, cmd)
        try:
            new_bodies, active_body_id, summary = execute(
                temp_design,
                cmd,
                registry,
                target_handle,
                tool_handle,
                target_body_id,
                tool_body_id,
                validated_params,
            )
        except Exception as exc:
            raise PreconditionError(
                f"Replay failed on historical command '{cmd.command_id}' (op '{cmd.op}'): {exc}"
            ) from exc

        temp_design = Design(
            version=record.version,
            journal=[],
            snapshots=temp_design.snapshots,
            patches=[],
            geometry=new_bodies.get(active_body_id),
            bodies=new_bodies,
            active_body_id=active_body_id,
        )

    return temp_design


def undo(design: Design, registry: Any) -> Design:
    if not design.journal:
        return design

    last_record = design.journal[-1]
    _REDO_STACK.append(last_record)

    remaining_records = design.journal[:-1]
    if not remaining_records:
        return Design.empty()

    rebuilt_design = replay(remaining_records, registry)
    rebuilt_patches = [
        p
        for p in design.patches
        if not p.patch_id.endswith(last_record.command.command_id)
    ]

    return Design(
        version=next_version(design.version),
        journal=remaining_records,
        snapshots=design.snapshots,
        patches=rebuilt_patches,
        geometry=rebuilt_design.geometry,
        bodies=rebuilt_design.bodies,
        active_body_id=rebuilt_design.active_body_id,
    )


def redo(design: Design, registry: Any) -> Design:
    if not _REDO_STACK:
        return design

    record_to_restore = _REDO_STACK.pop()
    records_to_apply = list(design.journal) + [record_to_restore]
    rebuilt_design = replay(records_to_apply, registry)

    return Design(
        version=next_version(design.version),
        journal=records_to_apply,
        snapshots=rebuilt_design.snapshots,
        patches=design.patches,
        geometry=rebuilt_design.geometry,
        bodies=rebuilt_design.bodies,
        active_body_id=rebuilt_design.active_body_id,
    )
