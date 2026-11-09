"""Output formatting contracts and payload validation for agent responses."""

from __future__ import annotations

import json
import re
from typing import Any


class AgentOutputError(Exception):
    def __init__(self, message: str, raw_snippet: str = "", field: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.raw_snippet = raw_snippet
        self.field = field

    def to_diagnostic(self) -> dict[str, Any]:
        return {
            "error": "AgentOutputError",
            "message": self.message,
            "raw_snippet": self.raw_snippet,
            "field": self.field,
        }


JSON_CODEBLOCK_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
INDEX_PATTERN = re.compile(r"\(\)\[[0-9]")


def parse_reply(text: str) -> tuple[str, list[dict[str, Any]]]:
    cleaned = text.strip()
    match = JSON_CODEBLOCK_PATTERN.search(cleaned)
    target_json_str = match.group(1).strip() if match else cleaned

    try:
        data = json.loads(target_json_str)
    except json.JSONDecodeError as exc:
        raise AgentOutputError(
            f"Failed to parse LLM reply as JSON: {exc}",
            raw_snippet=cleaned[:200],
        ) from exc

    if isinstance(data, list):
        return "", data

    if isinstance(data, dict):
        explanation = str(data.get("explanation", ""))
        commands_raw = data.get("commands")
        if commands_raw is not None:
            if not isinstance(commands_raw, list):
                raise AgentOutputError("Field 'commands' must be a list of command objects.", field="commands")
            return explanation, commands_raw
        if "op" in data:
            return explanation, [data]

    raise AgentOutputError("Parsed JSON lacks recognized 'commands' array or single command structure.", raw_snippet=str(data)[:200])


def validate_command_payload(payload: dict[str, Any], index: int = 0) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise AgentOutputError(f"Command #{index} must be a dictionary.", field=f"commands[{index}]")

    op = payload.get("op")
    if not op or not isinstance(op, str):
        raise AgentOutputError(f"Command #{index} missing required string field 'op'.", field=f"commands[{index}].op")

    target = payload.get("target")
    if target is not None:
        if not isinstance(target, dict):
            raise AgentOutputError(f"Command #{index} 'target' must be a dictionary.", field=f"commands[{index}].target")
        expr = target.get("expr", "")
        if INDEX_PATTERN.search(expr):
            raise AgentOutputError(
                f"Command #{index} uses forbidden raw integer index in selector '{expr}'.",
                field=f"commands[{index}].target.expr",
            )

    return payload
