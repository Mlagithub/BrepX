"""Inspect button click behavior for blade_runner via CDP."""

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
        expr = """
        (async function() {
            const btn = document.querySelector('.tool-chip[data-op="blade_runner"]');
            if (!btn) return { error: 'Not found' };
            btn.click();
            await new Promise(r => setTimeout(r, 2000));
            return {
                statusText: document.getElementById('status-text')?.textContent,
                journalLength: window.context?.journal?.length,
                lastOp: window.context?.lastCommand?.op,
                bodyFaces: window.context?.body?.face_count
            };
        })()
        """
        msg = {
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": expr, "returnByValue": True, "awaitPromise": True},
        }
        await ws.send(json.dumps(msg))
        resp = json.loads(await ws.recv())
        print("Click result:", json.dumps(resp, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
