"""Inspect the DOM bounding rect of timeline nodes and parent containers."""

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
        (function() {
            const bar = document.getElementById('timeline-bar-root');
            const track = document.getElementById('timeline-track');
            const nodes = document.querySelectorAll('.timeline-node');
            const adjustLast = document.getElementById('adjust-last-panel');

            return {
                barRect: bar ? {
                    top: bar.offsetTop,
                    left: bar.offsetLeft,
                    width: bar.clientWidth,
                    height: bar.clientHeight,
                    zIndex: window.getComputedStyle(bar).zIndex
                } : null,
                trackRect: track ? {
                    width: track.clientWidth,
                    height: track.clientHeight
                } : null,
                nodesCount: nodes.length,
                firstNodeRect: nodes.length ? {
                    width: nodes[0].clientWidth,
                    height: nodes[0].clientHeight,
                    text: nodes[0].textContent.trim()
                } : null,
                adjustLastRect: adjustLast ? {
                    zIndex: window.getComputedStyle(adjustLast).zIndex,
                    bottom: window.getComputedStyle(adjustLast).bottom,
                    left: window.getComputedStyle(adjustLast).left,
                    hidden: adjustLast.classList.contains('hidden')
                } : null
            };
        })()
        """
        msg = {
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": expr, "returnByValue": True},
        }
        await ws.send(json.dumps(msg))
        resp = json.loads(await ws.recv())
        print(json.dumps(resp.get("result", {}).get("result", {}).get("value", {}), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
