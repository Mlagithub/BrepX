"""Check bodies tree HTML content after reload and box creation."""

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
        await asyncio.sleep(2)

        script = """
        (async function() {
            const btn = document.querySelector('.tool-chip[data-op="box"]');
            if (btn) btn.click();
            await new Promise(r => setTimeout(r, 1500));
            return {
                html: document.getElementById('bodies-tree-container')?.innerHTML,
                itemsCount: document.querySelectorAll('.tree-item').length
            };
        })()
        """
        await ws.send(
            json.dumps({
                "id": 2,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": script,
                    "returnByValue": True,
                    "awaitPromise": True,
                },
            })
        )

        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == 2:
                val = resp.get("result", {}).get("result", {}).get("value", {})
                print("HTML content:", val.get("html"))
                print("Items count:", val.get("itemsCount"))
                break


if __name__ == "__main__":
    asyncio.run(main())
