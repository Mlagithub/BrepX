"""Capture real screenshot with model creation via direct command API then screenshot."""

from __future__ import annotations

import asyncio
import base64
import json
import urllib.request
import websockets


async def main() -> None:
    targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
    page = next(t for t in targets if t["type"] == "page" and "8080" in t.get("url", ""))
    ws_url = page["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Page.reload", "params": {"ignoreCache": True}}))
        await asyncio.sleep(2.0)

        # Trigger Box from browser
        script = """
        (async function() {
            while (!window.context) await new Promise(r => setTimeout(r, 100));
            const btn = document.querySelector('.tool-chip[data-op="box"]');
            if (btn) btn.click();
            await new Promise(r => setTimeout(r, 1200));
            return {
                timelineNodes: document.querySelectorAll('.timeline-node').length,
                journal: window.context?.journal?.length,
                vol: window.context?.body?.volume
            };
        })()
        """
        msg = {
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {"expression": script, "returnByValue": True, "awaitPromise": True},
        }
        await ws.send(json.dumps(msg))
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == 2:
                print("Creation result:", resp.get("result", {}).get("result", {}).get("value", {}))
                break

        # Capture screenshot
        shot_msg = {
            "id": 3,
            "method": "Page.captureScreenshot",
            "params": {"format": "png", "captureBeyondViewport": False},
        }
        await ws.send(json.dumps(shot_msg))
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == 3:
                data_b64 = resp.get("result", {}).get("data", "")
                with open("workbench_live.png", "wb") as f:
                    f.write(base64.b64decode(data_b64))
                print("Screenshot saved to workbench_live.png")
                break


if __name__ == "__main__":
    asyncio.run(main())
