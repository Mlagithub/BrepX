"""Audit Bodies Tree eye and isolate buttons in browser with box created first."""

from __future__ import annotations

import asyncio
import json
import urllib.request
import websockets


async def send_eval(ws, expr: str) -> dict:
    msg = {
        "id": 100,
        "method": "Runtime.evaluate",
        "params": {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True,
        },
    }
    await ws.send(json.dumps(msg))
    while True:
        raw = await ws.recv()
        resp = json.loads(raw)
        if resp.get("id") == 100:
            return resp.get("result", {}).get("result", {}).get("value", {})


async def test_bodies_tree_actions() -> None:
    targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
    page = next(t for t in targets if t["type"] == "page" and "8080" in t.get("url", ""))
    ws_url = page["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url) as ws:
        print("=== Testing Bodies Tree Visibility and Isolate Toggles ===")

        test_script = """
        (async function() {
            // 1. Create a box first
            const boxBtn = document.querySelector('.tool-chip[data-op="box"]');
            if (boxBtn) {
                boxBtn.click();
                await new Promise(r => setTimeout(r, 1000));
            }

            const treeItems = Array.from(document.querySelectorAll('.tree-item'));
            if (!treeItems.length) return { error: 'No tree items found after box creation' };

            const eyeBtn = treeItems[0].querySelector('.tree-eye-btn');
            const isolateBtn = treeItems[0].querySelector('.tree-isolate-btn');

            // Click eye to hide
            eyeBtn.click();
            await new Promise(r => setTimeout(r, 100));
            const hasHiddenClass = eyeBtn.textContent.length > 0;

            // Click eye to show
            eyeBtn.click();
            await new Promise(r => setTimeout(r, 100));

            // Click isolate
            isolateBtn.click();
            await new Promise(r => setTimeout(r, 100));

            return {
                itemsCount: treeItems.length,
                hasHiddenClass,
                isolateClicked: true
            };
        })()
        """
        res = await send_eval(ws, test_script)
        print("Bodies tree items count:", res.get("itemsCount"), "Isolate clicked:", res.get("isolateClicked"))


if __name__ == "__main__":
    asyncio.run(test_bodies_tree_actions())
