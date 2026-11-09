"""Incremental rebuild engine using topological DAG and snapshot cache."""

from __future__ import annotations

from typing import Any

from backend.core.assertions import run as run_assertions
from backend.core.command import CommandRecord
from backend.core.design import Design, next_version
from backend.core.errors import DomainError, PostconditionError
from backend.core.graph import build_graph
from backend.core.pipeline import (
    execute,
    merge_assertions,
    resolve_command_targets,
    validate_command,
)
from backend.core.snapshot import should_snapshot


class RebuildResult:
    def __init__(
        self,
        ok: bool,
        succeeded: list[str],
        failed: tuple[str, dict[str, Any]] | None = None,
        blocked: list[str] | None = None,
        design: Design | None = None,
    ) -> None:
        self.ok = ok
        self.succeeded = succeeded
        self.failed = failed
        self.blocked = blocked or []
        self.design = design

    def to_diagnostic(self) -> dict[str, Any]:
        if self.ok:
            return {"ok": True, "status": "ok", "rebuilt": self.succeeded}

        failed_id, error_detail = self.failed if self.failed else ("unknown", {})
        return {
            "ok": False,
            "status": "rebuild_failed",
            "failed_command": failed_id,
            "error": error_detail,
            "succeeded_upstream": self.succeeded,
            "blocked_downstream": self.blocked,
        }


def rebuild(
    design: Design,
    changed_command_id: str,
    registry: Any,
    new_params: dict[str, Any] | None = None,
    force_full: bool = False,
) -> RebuildResult:
    graph = build_graph(design.journal)
    if changed_command_id not in [r.command.command_id for r in design.journal]:
        raise KeyError(f"Changed command '{changed_command_id}' not found in design journal.")

    dirty_nodes = graph.downstream_of(changed_command_id, include_self=True)

    records_by_id: dict[str, CommandRecord] = {r.command.command_id: r for r in design.journal}
    first_dirty_idx = min(design.journal.index(records_by_id[cid]) for cid in dirty_nodes)

    snapshot_entry = None
    if not force_full and first_dirty_idx > 0:
        target_pre_ver = design.journal[first_dirty_idx - 1].version
        snapshot_entry = design.snapshots.get_below(target_pre_ver)

    if snapshot_entry is not None:
        snap_ver, snap_geo = snapshot_entry
        start_geo = snap_geo
        snap_idx = -1
        for idx, rec in enumerate(design.journal):
            if rec.version == snap_ver:
                snap_idx = idx
                break

        current_geo = start_geo
        replay_start_idx = snap_idx + 1 if snap_idx >= 0 else 0
    else:
        current_geo = None
        replay_start_idx = 0

    rebuilt_records: list[CommandRecord] = list(design.journal[:replay_start_idx])
    temp_design = Design(
        version=design.version,
        journal=rebuilt_records,
        snapshots=design.snapshots,
        patches=list(design.patches),
        geometry=current_geo,
        bodies=dict(design.bodies) if current_geo is not None else {},
        active_body_id=design.active_body_id,
    )

    succeeded: list[str] = [r.command.command_id for r in rebuilt_records]
    failed_info: tuple[str, dict[str, Any]] | None = None
    blocked: list[str] = []

    for idx in range(replay_start_idx, len(design.journal)):
        rec = design.journal[idx]
        cmd = rec.command
        cid = cmd.command_id

        if cid in dirty_nodes and cid == changed_command_id and new_params is not None:
            updated_params = dict(cmd.params)
            updated_params.update(new_params)
            from dataclasses import replace

            cmd = replace(cmd, params=updated_params)

        prev_geo = temp_design.get_body()

        try:
            spec, validated_params = validate_command(temp_design, cmd, registry)
            target_handle, tool_handle, target_body_id, tool_body_id = resolve_command_targets(temp_design, cmd)
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

            active_geo = new_bodies.get(active_body_id)
            assertions = merge_assertions(spec.default_assertions, cmd.expect)
            failures = run_assertions(active_geo, prev_geo, assertions)
            if failures:
                raise PostconditionError(
                    assertion_name="assertion_suite",
                    actual=failures,
                    expected=[],
                    suggestion="Check modified parameters to avoid violating physical invariants.",
                )

            current_ver = next_version(temp_design.version)
            new_record = CommandRecord(command=cmd, version=current_ver, result_summary=summary)
            rebuilt_records.append(new_record)
            succeeded.append(cid)

            if should_snapshot(current_ver):
                temp_design.snapshots.put(current_ver, active_geo)

            temp_design = Design(
                version=current_ver,
                journal=rebuilt_records,
                snapshots=temp_design.snapshots,
                patches=list(temp_design.patches),
                geometry=active_geo,
                bodies=new_bodies,
                active_body_id=active_body_id,
            )

        except Exception as exc:
            if isinstance(exc, DomainError):
                diag = exc.to_diagnostic()
            else:
                diag = {"error": type(exc).__name__, "message": str(exc)}

            failed_info = (cid, diag)
            downstream_blocked = graph.downstream_of(cid, include_self=False)
            blocked = [
                rec_down.command.command_id
                for rec_down in design.journal[idx + 1 :]
                if rec_down.command.command_id in downstream_blocked
            ]
            break

    if failed_info is not None:
        return RebuildResult(
            ok=False,
            succeeded=succeeded,
            failed=failed_info,
            blocked=blocked,
            design=design,
        )

    final_design = Design(
        version=temp_design.version,
        journal=rebuilt_records,
        snapshots=temp_design.snapshots,
        patches=temp_design.patches,
        geometry=temp_design.geometry,
        bodies=temp_design.bodies,
        active_body_id=temp_design.active_body_id,
    )
    return RebuildResult(ok=True, succeeded=succeeded, design=final_design)


def verify_determinism(design: Design, registry: Any) -> bool:
    if not design.journal:
        return True

    from backend.core.pipeline import replay

    replayed_design = replay(design.journal, registry)

    vol_orig = float(getattr(design.geometry, "volume", 0.0))
    vol_rep = float(getattr(replayed_design.geometry, "volume", 0.0))

    return abs(vol_orig - vol_rep) < 1e-4
