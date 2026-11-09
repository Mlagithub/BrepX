"""Check browser console logs and script execution state via CDP."""

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
        await ws.send(
            json.dumps({
                "id": 1,
                "method": "Page.reload",
                "params": {"ignoreCache": True},
            })
        )
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == 1:
                break

        await asyncio.sleep(2)

        expr = """
        (function() {
            return {
                title: document.title,
                canvas: !!document.querySelector('canvas'),
                toolChips: document.querySelectorAll('.tool-chip').length,
                toolbarLength: document.getElementById('toolbar-container')?.children.length || 0,
                timelineNodes: document.querySelectorAll('.timeline-node').length,
                status: document.getElementById('status-text')?.textContent
            };
        })()
        """
        await ws.send(
            json.dumps({
                "id": 2,
                "method": "Runtime.evaluate",
                "params": {"expression": expr, "returnByValue": True},
            })
        )
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == 2:
                val = resp.get("result", {}).get("result", {}).get("value", {})
                print(
                    f"Canvas present: {val.get('canvas')}, "
                    f"Tool chips count: {val.get('toolChips')}, "
                    f"Toolbar categories: {val.get('toolbarLength')}, "
                    f"Timeline nodes: {val.get('timelineNodes')}"
                )
                break


if __name__ == "__main__":
    asyncio.run(main())
