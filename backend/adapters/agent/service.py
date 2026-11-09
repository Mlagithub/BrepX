"""Agent turn execution service coordinating observation, LLM reasoning, and command dispatch."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Sequence

from backend.adapters.agent.healing import (
    AgentBudgetError,
    HealingCoordinator,
    build_diagnostic_hint,
)
from backend.adapters.agent.llm_client import LLMConfig, chat
from backend.adapters.agent.prompt import build_messages
from backend.adapters.agent.schema import parse_reply, validate_command_payload


def _execute_command_via_http(host_url: str, cmd_dict: dict[str, Any]) -> dict[str, Any]:
    endpoint = host_url.rstrip("/") + "/api/command"
    req_bytes = json.dumps(cmd_dict).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=req_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(err_body)
        except Exception:
            return {"ok": False, "error": {"message": err_body}}


def handle_turn(
    prompt: str,
    view: dict[str, Any],
    config: LLMConfig,
    host_url: str = "http://127.0.0.1:8080",
    chat_fn: Callable[[list[dict[str, str]], LLMConfig], str] | None = None,
    command_executor: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    do_chat = chat_fn or chat
    do_exec = command_executor or _execute_command_via_http

    coordinator = HealingCoordinator()
    diagnostics: list[str] = []
    executed_commands: list[str] = []

    last_error: dict[str, Any] | None = None
    final_explanation = ""

    for turn_idx in range(coordinator.max_turns):
        try:
            coordinator.check_budget(turn_idx)
            messages = build_messages(view, prompt, diagnostics=diagnostics)
            coordinator.track_tokens(sum(len(m["content"]) for m in messages))

            reply_text = do_chat(messages, config)
            coordinator.track_tokens(len(reply_text))

            explanation, raw_commands = parse_reply(reply_text)
            final_explanation = explanation

            coordinator.record_action_fingerprint(raw_commands)

            turn_succeeded = True
            for c_idx, raw_cmd in enumerate(raw_commands):
                valid_cmd = validate_command_payload(raw_cmd, index=c_idx)
                if "idempotency_key" not in valid_cmd:
                    valid_cmd["idempotency_key"] = f"agent_{valid_cmd.get('command_id', 'cmd')}_{turn_idx}"
                if "command_id" not in valid_cmd:
                    valid_cmd["command_id"] = f"c_{turn_idx}_{c_idx}"

                exec_res = do_exec(host_url, valid_cmd)
                if not exec_res.get("ok", False):
                    turn_succeeded = False
                    last_error = exec_res.get("error", {"message": "Command execution failed"})
                    hint = build_diagnostic_hint(last_error)
                    diagnostics.append(hint)
                    break

                executed_commands.append(valid_cmd["command_id"])

            if turn_succeeded:
                return {
                    "ok": True,
                    "explanation": final_explanation,
                    "executed": executed_commands,
                    "turns_used": turn_idx + 1,
                }

        except AgentBudgetError as b_err:
            return {
                "ok": False,
                "error": b_err.to_diagnostic(),
                "executed": executed_commands,
                "turns_used": turn_idx + 1,
            }
        except Exception as exc:
            err_diag = getattr(exc, "to_diagnostic", lambda: {"error": type(exc).__name__, "message": str(exc)})()
            hint = build_diagnostic_hint(err_diag)
            diagnostics.append(hint)
            last_error = err_diag

    return {
        "ok": False,
        "error": last_error or {"message": "Agent retries exhausted."},
        "executed": executed_commands,
        "turns_used": coordinator.max_turns,
    }
