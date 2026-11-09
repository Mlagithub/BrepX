"""Capture Console.messageAdded and Runtime.exceptionThrown via CDP."""

from __future__ import annotations

import asyncio
import json
import urllib.request
import websockets


async def main() -> None:
    targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
    page = next(t for t in targets if t["type"] == "page" and "8080" in t.get("url", ""))
    ws_url = page["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Console.enable"}))
        await ws.send(json.dumps({"id": 2, "method": "Runtime.enable"}))
        await ws.send(json.dumps({"id": 3, "method": "Page.enable"}))

        await ws.send(
            json.dumps({
                "id": 4,
                "method": "Page.reload",
                "params": {"ignoreCache": True},
            })
        )

        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < 3.0:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                msg = json.loads(raw)
                method = msg.get("method", "")
                if "Console" in method or "exception" in method.lower():
                    print("CDP EVENT:", json.dumps(msg, indent=2, ensure_ascii=False))
            except asyncio.TimeoutError:
                break


if __name__ == "__main__":
    asyncio.run(main())
