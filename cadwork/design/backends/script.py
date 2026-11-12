"""Backend that executes a plan node as a script on the local smlibpy kernel.

One smlibpy MCP session is kept per document, so the ``n*`` variables earlier
nodes created stay available to later nodes.  ``build_node`` emits one
deterministic script (:mod:`cadwork.design.script_emit`), runs it through the
MCP client and returns the metrics the script printed.

The class is synchronous: it wraps :class:`~cadwork.service.smlibpy_client.SyncSmlibpyClient`,
which owns a background event loop.  ``prior_vars`` is accepted for interface
parity with in-process backends but is not used — the script addresses the
session's live variables by name.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

from cadwork.design.script_emit import METRICS_PREFIX, emit_node
from cadwork.service.smlibpy_client import DEFAULT_TIMEOUT_S, RunResult, SyncSmlibpyClient

from .base import BackendError, BackendTimeout, NodeResult

_TIMEOUT_MARKERS = ("did not finish within", "the script was stopped", "timed out", "timeout")


def _looks_like_timeout(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in _TIMEOUT_MARKERS)


def parse_metrics(text: str) -> dict[str, Any] | None:
    """Extract the JSON object after :data:`METRICS_PREFIX` from a tool answer."""
    if not text:
        return None
    index = text.find(METRICS_PREFIX)
    if index < 0:
        return None
    payload = text[index + len(METRICS_PREFIX):].lstrip()
    try:
        value, _end = json.JSONDecoder().raw_decode(payload)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


class ScriptBackend:
    """Runs plan steps on a local smlibpy MCP server."""

    name = "script"

    def __init__(
        self,
        client: Any | None = None,
        *,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self._client = client if client is not None else SyncSmlibpyClient()
        self.timeout_s = float(timeout_s)
        self._sessions: dict[str, str] = {}
        self._committed: dict[str, set[str]] = {}
        self._closed = False

    # -- lifecycle -------------------------------------------------------
    def start(self) -> "ScriptBackend":
        self._start_client()
        return self

    def _start_client(self) -> None:
        if self._closed:
            raise BackendError("the script backend is closed", code="SCRIPT_FAILED")
        starter = getattr(self._client, "start", None)
        if callable(starter):
            starter()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._sessions.clear()
        self._committed.clear()
        closer = getattr(self._client, "close", None)
        if callable(closer):
            closer()

    def __enter__(self) -> "ScriptBackend":
        return self.start()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    # -- observation -----------------------------------------------------
    def session_id(self, document_id: str) -> str | None:
        """The smlibpy session currently mapped to ``document_id``, if any."""
        return self._sessions.get(document_id)

    def committed_nodes(self, document_id: str) -> frozenset[str]:
        """Node ids that ran successfully for ``document_id``."""
        return frozenset(self._committed.get(document_id, ()))

    # -- execution -------------------------------------------------------
    def build_node(
        self,
        document_id: str,
        step: Any,
        prior_vars: Mapping[str, Any] | None = None,
        step_path: str | None = None,
    ) -> NodeResult:
        """Emit and run one step, returning its parsed metrics.

        Raises :class:`~cadwork.design.script_emit.EmitError` when the step
        cannot be emitted, ``BackendError`` when the kernel rejects the script
        and ``BackendTimeout`` when it does not finish.  A failed script leaves
        the session untouched, matching smlibpy's transactional guarantee.
        """
        del prior_vars  # the session already holds the n* variables
        if self._closed:
            raise BackendError("the script backend is closed", code="SCRIPT_FAILED")
        self._start_client()
        script = emit_node(step, step_path=step_path)
        node_id = str(getattr(step, "node_id", "") or "")
        session = self._ensure_session(document_id)
        try:
            result = self._client.run(
                session, script, label=node_id or None, timeout_s=self.timeout_s
            )
        except BackendTimeout:
            self._sessions.pop(document_id, None)
            raise
        except BackendError as exc:
            # The session may be gone (server restart); the next call recovers
            # by opening a fresh one.
            self._sessions.pop(document_id, None)
            raise exc

        if not isinstance(result, RunResult):
            raise BackendError(
                f"client returned {type(result).__name__}, expected RunResult",
                raw=str(result),
            )
        if not result.ok:
            if result.timed_out or _looks_like_timeout(result.text):
                self._sessions.pop(document_id, None)
                raise BackendTimeout(
                    f"node {node_id or '?'} did not finish within {self.timeout_s:.0f} s",
                    raw=result.text,
                )
            raise BackendError(
                f"node {node_id or '?'} failed: {result.text}",
                raw=result.text,
            )

        metrics = parse_metrics(result.text)
        if metrics is None:
            raise BackendError(
                f"node {node_id or '?'} ran but printed no {METRICS_PREFIX} line",
                raw=result.text,
            )
        self._committed.setdefault(document_id, set()).add(node_id)
        return NodeResult(metrics=metrics, step_path=step_path, raw=result.text)

    def replay(
        self,
        document_id: str,
        steps: Iterable[Any],
    ) -> dict[str, Any] | None:
        """Rebuild a document session from scratch by re-running ``steps``.

        Used after a restart or lost session: a fresh smlibpy session is opened
        and every supplied step runs in order.  Returns the metrics of the last
        step (or ``None`` for an empty prefix).
        """
        if self._closed:
            raise BackendError("the script backend is closed", code="SCRIPT_FAILED")
        self._start_client()

        previous = self._sessions.pop(document_id, None)
        self._committed.pop(document_id, None)
        if previous is not None:
            # Best effort: an old session may already be gone.
            try:
                self._client.clear(previous)
            except BackendError:
                pass
        try:
            session = self._client.new_session()
        except BackendError as exc:
            raise BackendError(
                f"could not open a session to replay {document_id!r}: {exc}",
                code="SESSION_REPLAY_FAILED",
                raw=getattr(exc, "raw", None),
            ) from exc
        self._sessions[document_id] = session

        metrics: dict[str, Any] | None = None
        for step in steps:
            node_id = str(getattr(step, "node_id", "") or "")
            script = emit_node(step)
            try:
                result = self._client.run(
                    session, script, label=node_id or None, timeout_s=self.timeout_s
                )
            except BackendTimeout as exc:
                self._sessions.pop(document_id, None)
                self._committed.pop(document_id, None)
                raise BackendTimeout(
                    f"replay stopped at node {node_id or '?'}: {exc}",
                    raw=getattr(exc, "raw", None),
                ) from exc
            if not result.ok:
                self._sessions.pop(document_id, None)
                self._committed.pop(document_id, None)
                if result.timed_out or _looks_like_timeout(result.text):
                    raise BackendTimeout(
                        f"replay stopped at node {node_id or '?'}: {result.text}",
                        raw=result.text,
                    )
                raise BackendError(
                    f"replay stopped at node {node_id or '?'}: {result.text}",
                    code="SESSION_REPLAY_FAILED",
                    raw=result.text,
                )
            parsed = parse_metrics(result.text)
            if parsed is None:
                self._sessions.pop(document_id, None)
                self._committed.pop(document_id, None)
                raise BackendError(
                    f"replay node {node_id or '?'} printed no {METRICS_PREFIX} line",
                    code="SESSION_REPLAY_FAILED",
                    raw=result.text,
                )
            self._committed.setdefault(document_id, set()).add(node_id)
            metrics = parsed
        return metrics

    def reset(self, document_id: str) -> None:
        """Empty the document's session and forget what was committed."""
        previous = self._sessions.pop(document_id, None)
        self._committed.pop(document_id, None)
        if previous is None:
            return
        if self._closed:
            return
        try:
            self._client.clear(previous)
        except BackendError:
            # A session lost with the server is already empty; the next
            # build_node opens a new one.
            pass

    # -- internals -------------------------------------------------------
    def _ensure_session(self, document_id: str) -> str:
        session = self._sessions.get(document_id)
        if session is not None:
            return session
        session = self._client.new_session()
        self._sessions[document_id] = session
        return session


__all__ = ["ScriptBackend", "parse_metrics"]
