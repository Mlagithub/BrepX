"""CDP Real Browser DOM and interactive verification for BrepX M1-M5."""

from __future__ import annotations

import asyncio
import json
import urllib.request
import websockets


async def cdp_eval(expression: str) -> dict:
    targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
    page = next(t for t in targets if t["type"] == "page" and "8080" in t.get("url", ""))
    ws_url = page["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url) as ws:
        msg = {
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        }
        await ws.send(json.dumps(msg))
        reply = await ws.recv()
        data = json.loads(reply)
        return data.get("result", {}).get("result", {}).get("value", {})


def run_test() -> None:
    res = asyncio.run(
        cdp_eval(
            """
        ({
            title: document.title,
            canvas: !!document.querySelector('canvas'),
            toolChipsCount: document.querySelectorAll('.tool-chip').length,
            timelineExists: !!document.getElementById('timeline-bar-root'),
            agentExists: !!document.getElementById('agent-panel-container'),
            statusText: document.getElementById('status-text')?.textContent || ''
        })
    """
        )
    )
    print("CDP DOM Initial State:", res)


if __name__ == "__main__":
    run_test()
