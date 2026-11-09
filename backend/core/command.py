"""Command and assertion data contracts for BrepX mutation pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

BASE_PATTERN = re.compile(r"^(prev|c[0-9]+)$")
INDEX_SYNTAX_PATTERN = re.compile(r"\(\)\[[0-9]")


@dataclass(frozen=True)
class SelectorRef:
    base: str
    expr: str

    def __post_init__(self) -> None:
        if not BASE_PATTERN.match(self.base):
            raise ValueError(
                f"Invalid selector base '{self.base}'. Must be 'prev' or 'c<digits>'."
            )
        if not self.expr or not self.expr.strip():
            raise ValueError("Selector expression cannot be empty.")
        if INDEX_SYNTAX_PATTERN.search(self.expr):
            raise ValueError(
                f"Topological raw integer index forbidden in selector expression '{self.expr}'."
            )


@dataclass(frozen=True)
class Assertion:
    name: str
    args: tuple[Any, ...] = ()


def is_valid() -> Assertion:
    return Assertion("is_valid")


def is_solid() -> Assertion:
    return Assertion("is_solid")


def volume_gt(v: float) -> Assertion:
    return Assertion("volume_gt", (float(v),))


def volume_delta_sign(s: int) -> Assertion:
    if s not in (-1, 0, 1):
        raise ValueError(f"Volume delta sign must be -1, 0, or 1, got {s}")
    return Assertion("volume_delta_sign", (s,))


def face_count_delta(n: int) -> Assertion:
    return Assertion("face_count_delta", (int(n),))


def no_degenerate_faces(min_area: float) -> Assertion:
    return Assertion("no_degenerate_faces", (float(min_area),))


def bbox_within(box: tuple[float, float, float, float, float, float]) -> Assertion:
    if len(box) != 6:
        raise ValueError("Bounding box must be a 6-tuple of coordinates.")
    return Assertion("bbox_within", tuple(float(x) for x in box))


@dataclass(frozen=True)
class Command:
    command_id: str
    op: str
    target: SelectorRef | None
    tool: SelectorRef | None
    params: dict[str, int | float | bool | str]
    expect: tuple[Assertion, ...]
    idempotency_key: str
    replaces: str | None = None

    def __post_init__(self) -> None:
        if not self.command_id:
            raise ValueError("command_id cannot be empty.")
        if not self.op:
            raise ValueError("op cannot be empty.")
        if not self.idempotency_key:
            raise ValueError("idempotency_key cannot be empty.")
        for k, v in self.params.items():
            if not isinstance(v, (int, float, bool, str)) or isinstance(v, type(None)):
                raise ValueError(
                    f"Command param '{k}' has invalid type {type(v).__name__}. Only scalar values are admitted."
                )

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> Command:
        required_keys = ("command_id", "op", "params", "idempotency_key")
        for rk in required_keys:
            if rk not in payload:
                raise ValueError(f"Missing required command payload field: '{rk}'")

        target_raw = payload.get("target")
        target = (
            SelectorRef(base=target_raw["base"], expr=target_raw["expr"])
            if target_raw is not None
            else None
        )

        tool_raw = payload.get("tool")
        tool = (
            SelectorRef(base=tool_raw["base"], expr=tool_raw["expr"])
            if tool_raw is not None
            else None
        )

        params_raw = payload.get("params", {})
        if not isinstance(params_raw, dict):
            raise ValueError("Command 'params' field must be a dictionary.")

        expect_raw = payload.get("expect", [])
        assertions: list[Assertion] = []
        for item in expect_raw:
            if isinstance(item, Assertion):
                assertions.append(item)
            elif isinstance(item, dict):
                assertions.append(Assertion(name=item["name"], args=tuple(item.get("args", ()))))
            else:
                raise ValueError(f"Invalid assertion specification: {item}")

        return cls(
            command_id=str(payload["command_id"]),
            op=str(payload["op"]),
            target=target,
            tool=tool,
            params=dict(params_raw),
            expect=tuple(assertions),
            idempotency_key=str(payload["idempotency_key"]),
            replaces=payload.get("replaces"),
        )


@dataclass
class CommandRecord:
    command: Command
    version: int
    result_summary: dict[str, Any]

    def __post_init__(self) -> None:
        required_keys = {"volume", "face_count", "is_valid"}
        missing = required_keys - set(self.result_summary.keys())
        if missing:
            raise ValueError(f"result_summary missing mandatory keys: {sorted(missing)}")
