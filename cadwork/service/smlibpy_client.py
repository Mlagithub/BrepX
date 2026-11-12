"""Client for the local ``smlibpy`` MCP server.

``smlibpy`` (0.6.2 here) ships a stdio MCP server::

    python -m smlibpy.mcp

with fifteen tools.  The backend only needs five of them (``run_script``,
``clear``, ``checkpoint``, ``restore`` and ``list_tools``), but the server's
instructions are 44 KB, which is why this module talks to it through the
official ``mcp`` SDK instead of the harness' own proxy.

Layering
--------
``SmlibpyClient`` is **async** and must live entirely inside one event loop:
enter it with ``await client.start()`` / ``await client.close()`` or use it as
``async with``.  ``SyncSmlibpyClient`` is a thin synchronous facade that owns a
dedicated event-loop thread, for the synchronous service layer and tests.

Every call is serialised through one ``asyncio.Lock`` because an MCP client
session is a single request/response stream.  Failures surface as
``BackendError`` / ``BackendTimeout`` from ``cadwork.design.backends.base``.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
import re
import sys
import threading
from dataclasses import dataclass
from typing import Any, Sequence

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from cadwork.design.backends.base import BackendError, BackendTimeout

SERVER_MODULE = "smlibpy.mcp"

DEFAULT_TIMEOUT_S = 120.0
MIN_TIMEOUT_S = 1.0
MAX_TIMEOUT_S = 900.0
#: The server stops a script itself at ``timeout_s``; the client waits a little
#: longer so the server's own "the script was stopped" answer can be read.
DEFAULT_GRACE_S = 15.0

CONTROL_TIMEOUT_S = 60.0
START_TIMEOUT_S = 120.0

_SESSION_RE = re.compile(r'Session "(s-[a-z0-9]+)"')
_FAILED_PREFIX = "Script failed"
_TIMEOUT_MARKERS = ("did not finish within", "the script was stopped", "timed out", "timeout")


@dataclass(frozen=True)
class RunResult:
    """One ``run_script`` answer.

    ``ok`` is false for a script that raised (the server keeps the session as
    it was); ``text`` is the complete answer including printed output; and
    ``session_id`` is present when the answer opened a new session.
    """

    ok: bool
    text: str
    session_id: str | None = None

    def __bool__(self) -> bool:  # convenience for ``if result:``
        return self.ok

    @property
    def timed_out(self) -> bool:
        """True when the server reports that it stopped a runaway script."""
        lowered = self.text.lower()
        return not self.ok and any(marker in lowered for marker in _TIMEOUT_MARKERS)


def parse_session_id(text: str) -> str | None:
    """Return ``s-xxxx`` from a server answer, or ``None``."""
    if not text:
        return None
    match = _SESSION_RE.search(text)
    return match.group(1) if match else None


def _text_of(result: Any) -> str:
    parts: list[str] = []
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


def _clamp_timeout(value: float | None) -> float:
    try:
        number = float(value if value is not None else DEFAULT_TIMEOUT_S)
    except (TypeError, ValueError):
        number = DEFAULT_TIMEOUT_S
    return max(MIN_TIMEOUT_S, min(MAX_TIMEOUT_S, number))


class SmlibpyClient:
    """Async client for the local smlibpy MCP server (one event loop)."""

    def __init__(
        self,
        *,
        command: str | None = None,
        args: Sequence[str] | None = None,
        env: dict[str, str] | None = None,
        cwd: str | os.PathLike[str] | None = None,
        start_timeout_s: float = START_TIMEOUT_S,
        timeout_grace_s: float = DEFAULT_GRACE_S,
    ) -> None:
        self.command = command or sys.executable
        self.args = list(args) if args is not None else ["-m", SERVER_MODULE]
        self.env: dict[str, str] = {"SMLIBPY_VIEWER": "off", "SMLIBPY_SESSIONS_AWAKE": "1"}
        if env:
            self.env.update({str(key): str(value) for key, value in env.items()})
        self.cwd = cwd
        self.start_timeout_s = float(start_timeout_s)
        self.timeout_grace_s = max(0.0, float(timeout_grace_s))

        self._lock: asyncio.Lock | None = None
        self._session: ClientSession | None = None
        self._session_cm: Any = None
        self._stdio_cm: Any = None
        self._errlog: Any = None
        self.server_info: Any = None
        self._closed = False

    # -- lifecycle -------------------------------------------------------
    @property
    def started(self) -> bool:
        return self._session is not None

    def _get_lock(self) -> asyncio.Lock:
        # Created lazily so the lock is bound to the loop that actually uses it
        # (the sync facade constructs the client in another thread).
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def start(self) -> "SmlibpyClient":
        """Spawn the server and initialise the MCP session (idempotent)."""
        lock = self._get_lock()
        async with lock:
            if self._session is not None:
                return self
            self._closed = False
            await self._start_locked()
        return self

    async def _start_locked(self) -> None:
        params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env,
            cwd=self.cwd,
        )
        # The MCP SDK writes server stderr to ``errlog``; Windows' default
        # stderr encoding is not UTF-8, so give it a safe sink.
        errlog = open(os.devnull, "w", encoding="utf-8", errors="replace")
        stdio_cm = stdio_client(params, errlog=errlog)
        try:
            read, write = await asyncio.wait_for(stdio_cm.__aenter__(), timeout=self.start_timeout_s)
        except BaseException:
            try:
                await stdio_cm.__aexit__(None, None, None)
            except Exception:
                pass
            errlog.close()
            raise
        session_cm: Any = None
        try:
            session_cm = ClientSession(read, write)
            session = await asyncio.wait_for(session_cm.__aenter__(), timeout=self.start_timeout_s)
            init = await asyncio.wait_for(session.initialize(), timeout=self.start_timeout_s)
        except BaseException:
            if session_cm is not None:
                try:
                    await session_cm.__aexit__(None, None, None)
                except Exception:
                    pass
            try:
                await stdio_cm.__aexit__(None, None, None)
            except Exception:
                pass
            errlog.close()
            raise
        self._stdio_cm = stdio_cm
        self._session_cm = session_cm
        self._session = session
        self._errlog = errlog
        self.server_info = getattr(init, "server_info", None)

    async def close(self) -> None:
        """Shut the session and the server down (idempotent, best effort)."""
        lock = self._get_lock()
        async with lock:
            session_cm = self._session_cm
            stdio_cm = self._stdio_cm
            errlog = self._errlog
            self._session = None
            self._session_cm = None
            self._stdio_cm = None
            self._errlog = None
            self.server_info = None
            self._closed = True
            if session_cm is not None:
                try:
                    await session_cm.__aexit__(None, None, None)
                except Exception:
                    pass
            if stdio_cm is not None:
                try:
                    await stdio_cm.__aexit__(None, None, None)
                except Exception:
                    pass
            if errlog is not None:
                try:
                    errlog.close()
                except Exception:
                    pass

    async def __aenter__(self) -> "SmlibpyClient":
        return await self.start()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    # -- tools -----------------------------------------------------------
    async def list_tools(self) -> list[Any]:
        """List the server's tools; the health check used by tests."""
        async with self._get_lock():
            session = self._require_session("list_tools")
            try:
                result = await asyncio.wait_for(
                    session.list_tools(), timeout=self.start_timeout_s
                )
            except asyncio.TimeoutError as exc:
                raise BackendTimeout("smlibpy list_tools timed out") from exc
            except Exception as exc:
                raise BackendError(f"smlibpy list_tools failed: {exc}", raw=str(exc)) from exc
        return list(result.tools)

    async def run(
        self,
        session: str,
        script: str,
        label: str | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> RunResult:
        """Run ``script`` in ``session`` and classify the answer.

        Returns ``ok=False`` for a script error (the server leaves the session
        untouched).  A transport-level timeout raises ``BackendTimeout``; a
        server-side timeout is reported as ``ok=False`` with ``timed_out``.
        """
        timeout = _clamp_timeout(timeout_s)
        wire_timeout = timeout + self.timeout_grace_s
        async with self._get_lock():
            text = await self._request(
                "run_script",
                {"session": session, "script": script, "label": label, "timeout_s": timeout},
                wire_timeout,
            )
        ok = not text.lstrip().startswith(_FAILED_PREFIX)
        return RunResult(ok=ok, text=text, session_id=parse_session_id(text))

    async def new_session(self) -> str:
        """Open an empty session and return its id (``s-...``).

        Opening a session is done through ``clear`` on ``session="new"``; the
        server names the new session in its answer.
        """
        async with self._get_lock():
            text = await self._request(
                "clear", {"session": "new"}, CONTROL_TIMEOUT_S
            )
        session_id = parse_session_id(text)
        if not session_id:
            raise BackendError(
                "smlibpy opened no session (its answer did not contain an s-... id)",
                raw=text,
            )
        return session_id

    async def clear(self, session: str) -> str:
        """Empty ``session`` (checkpoints included)."""
        async with self._get_lock():
            return await self._request("clear", {"session": session}, CONTROL_TIMEOUT_S)

    async def checkpoint(self, session: str, label: str | None = None) -> str:
        """Remember the current state of ``session`` under ``label``."""
        async with self._get_lock():
            return await self._request(
                "checkpoint", {"session": session, "label": label}, CONTROL_TIMEOUT_S
            )

    async def restore(self, session: str, label: str | None = None) -> str:
        """Rebuild ``session`` back to a checkpoint."""
        async with self._get_lock():
            return await self._request(
                "restore", {"session": session, "label": label}, CONTROL_TIMEOUT_S
            )

    # -- internals -------------------------------------------------------
    def _require_session(self, tool: str) -> ClientSession:
        if self._session is None:
            raise BackendError(
                f"smlibpy client is not started; call start() before {tool}()",
                code="SCRIPT_FAILED",
            )
        return self._session

    async def _request(self, tool: str, arguments: dict[str, Any], timeout_s: float) -> str:
        session = self._require_session(tool)
        try:
            result = await asyncio.wait_for(
                session.call_tool(tool, arguments), timeout=timeout_s
            )
        except asyncio.TimeoutError as exc:
            raise BackendTimeout(
                f"smlibpy tool {tool!r} did not answer within {timeout_s:.0f} s"
            ) from exc
        except BackendError:
            raise
        except Exception as exc:  # transport or protocol failure
            raise BackendError(f"smlibpy tool {tool!r} failed: {exc}", raw=str(exc)) from exc
        text = _text_of(result)
        if getattr(result, "is_error", False) or getattr(result, "isError", False):
            raise BackendError(text or f"smlibpy tool {tool!r} failed", raw=text)
        return text


class SyncSmlibpyClient:
    """Synchronous facade for :class:`SmlibpyClient`.

    It owns a daemon thread running one asyncio event loop; every method
    submits the matching coroutine and waits.  Use ``close()`` when done (or a
    ``with`` block); the server process and the loop thread are stopped.
    """

    def __init__(self, **client_kwargs: Any) -> None:
        self._inner = SmlibpyClient(**client_kwargs)
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop, name="smlibpy-client-loop", daemon=True
        )
        self._started = False
        self._closed = False
        self._thread.start()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        finally:
            try:
                asyncio.set_event_loop(None)
            except Exception:
                pass

    # -- plumbing --------------------------------------------------------
    def _submit(self, coro: Any, timeout: float | None) -> Any:
        if self._closed:
            raise BackendError("smlibpy client is closed", code="SCRIPT_FAILED")
        try:
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        except RuntimeError as exc:  # loop already stopped
            raise BackendError(f"smlibpy client loop is not running: {exc}", raw=str(exc)) from exc
        try:
            return future.result(timeout)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise BackendTimeout("smlibpy call did not answer in time") from exc

    @property
    def server_info(self) -> Any:
        return self._inner.server_info

    @property
    def started(self) -> bool:
        return self._started

    # -- lifecycle -------------------------------------------------------
    def start(self) -> "SyncSmlibpyClient":
        if self._closed:
            raise BackendError("smlibpy client is closed", code="SCRIPT_FAILED")
        if not self._started:
            self._submit(self._inner.start(), START_TIMEOUT_S + 30.0)
            self._started = True
        return self

    def close(self) -> None:
        if self._closed:
            return
        try:
            if self._started:
                self._submit(self._inner.close(), START_TIMEOUT_S)
        except Exception:
            pass
        finally:
            self._closed = True
            self._started = False
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except RuntimeError:
                pass
            self._thread.join(10.0)
            if not self._loop.is_closed():
                try:
                    self._loop.close()
                except Exception:
                    pass

    def __enter__(self) -> "SyncSmlibpyClient":
        return self.start()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    # -- tools -----------------------------------------------------------
    def list_tools(self) -> list[Any]:
        self.start()
        return self._submit(self._inner.list_tools(), START_TIMEOUT_S + 30.0)

    def run(
        self,
        session: str,
        script: str,
        label: str | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> RunResult:
        self.start()
        timeout = _clamp_timeout(timeout_s)
        budget = timeout + self._inner.timeout_grace_s + 30.0
        return self._submit(
            self._inner.run(session, script, label=label, timeout_s=timeout), budget
        )

    def new_session(self) -> str:
        self.start()
        return self._submit(self._inner.new_session(), CONTROL_TIMEOUT_S * 4)

    def clear(self, session: str) -> str:
        self.start()
        return self._submit(self._inner.clear(session), CONTROL_TIMEOUT_S * 4)

    def checkpoint(self, session: str, label: str | None = None) -> str:
        self.start()
        return self._submit(self._inner.checkpoint(session, label), CONTROL_TIMEOUT_S * 4)

    def restore(self, session: str, label: str | None = None) -> str:
        self.start()
        return self._submit(self._inner.restore(session, label), CONTROL_TIMEOUT_S * 4)


__all__ = [
    "DEFAULT_GRACE_S",
    "DEFAULT_TIMEOUT_S",
    "MAX_TIMEOUT_S",
    "MIN_TIMEOUT_S",
    "RunResult",
    "SmlibpyClient",
    "SyncSmlibpyClient",
    "parse_session_id",
]
