"""Structured diagnostic translation, self-healing loop, and budget circuit breakers."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable


class AgentBudgetError(Exception):
    def __init__(self, message: str, reason: str) -> None:
        super().__init__(message)
        self.message = message
        self.reason = reason

    def to_diagnostic(self) -> dict[str, Any]:
        return {
            "error": "AgentBudgetError",
            "message": self.message,
            "reason": self.reason,
        }


def build_diagnostic_hint(error_dict: dict[str, Any]) -> str:
    err_type = error_dict.get("error", "Error")
    msg = error_dict.get("message", "")
    hints: list[str] = [f"执行失败 [{err_type}]: {msg}"]

    candidates = error_dict.get("candidates")
    if candidates:
        hints.append(f"当前几何上可用的稳定选择器候选为: {', '.join(candidates)}。请选用上述候选之一替换无效目标。")

    param = error_dict.get("param")
    allowed = error_dict.get("allowed")
    if param and allowed:
        hints.append(f"参数 '{param}' 超出允许区间 ({allowed})，请根据物理限制调整该参数。")

    closest = error_dict.get("closest")
    if closest:
        hints.append(f"未找到该算子，最接近的已注册可用算子为: {', '.join(closest)}。")

    return " ".join(hints)


class HealingCoordinator:
    def __init__(
        self,
        max_turns: int = 3,
        max_seconds: float = 90.0,
        max_total_tokens: int = 20000,
    ) -> None:
        self.max_turns = max_turns
        self.max_seconds = max_seconds
        self.max_total_tokens = max_total_tokens

        self.start_time = time.perf_counter()
        self.consumed_tokens = 0
        self.seen_fingerprints: set[str] = set()

    def check_budget(self, turn_idx: int) -> None:
        if turn_idx >= self.max_turns:
            raise AgentBudgetError(
                f"Exceeded maximum agent retry turns ({self.max_turns}).",
                reason="max_turns_exceeded",
            )
        elapsed = time.perf_counter() - self.start_time
        if elapsed > self.max_seconds:
            raise AgentBudgetError(
                f"Agent execution time {elapsed:.1f}s exceeded budget ({self.max_seconds}s).",
                reason="timeout_exceeded",
            )
        if self.consumed_tokens > self.max_total_tokens:
            raise AgentBudgetError(
                f"Consumed tokens {self.consumed_tokens} exceeded budget ({self.max_total_tokens}).",
                reason="tokens_exceeded",
            )

    def track_tokens(self, char_count: int) -> None:
        self.consumed_tokens += char_count // 3

    def record_action_fingerprint(self, commands: list[dict[str, Any]]) -> None:
        canonical_str = json.dumps(commands, sort_keys=True)
        fp = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
        if fp in self.seen_fingerprints:
            raise AgentBudgetError("Loop detected: Repeated duplicate command proposal.", reason="LOOP_DETECTED")
        self.seen_fingerprints.add(fp)
