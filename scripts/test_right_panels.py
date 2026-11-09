"""Browser live UI test verifying right sidebar panels: Agent, Measure Inspector, Python viewer."""

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


async def test_right_panels() -> None:
    targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
    page = next(t for t in targets if t["type"] == "page" and "8080" in t.get("url", ""))
    ws_url = page["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url) as ws:
        print("=== Testing Right Sidebar Tabs & Panels in Chrome ===")

        test_script = """
        (async function() {
            const tabs = Array.from(document.querySelectorAll('.tab-btn[data-tab]'));
            const tabNames = tabs.map(t => t.dataset.tab);

            // 1. Switch to Inspect Tab
            const inspectTab = document.getElementById('tab-btn-inspect');
            inspectTab.click();
            await new Promise(r => setTimeout(r, 200));
            const inspectActive = document.getElementById('tab-inspect')?.classList.contains('active');
            const inspectorContent = document.getElementById('measure-inspector-container')?.textContent;

            // 2. Switch to Python Viewer Tab
            const pythonTab = document.getElementById('tab-btn-python');
            pythonTab.click();
            await new Promise(r => setTimeout(r, 400));
            const pythonActive = document.getElementById('tab-python')?.classList.contains('active');
            const pythonCode = document.getElementById('python-viewer-textarea')?.value;

            // 3. Switch back to Agent Tab
            const agentTab = document.getElementById('tab-btn-agent');
            agentTab.click();
            await new Promise(r => setTimeout(r, 200));
            const agentActive = document.getElementById('tab-agent')?.classList.contains('active');
            const agentInput = !!document.getElementById('agent-prompt-input');

            return {
                tabsCount: tabs.length,
                tabNames,
                inspectActive,
                inspectorContent: inspectorContent?.trim().slice(0, 30),
                pythonActive,
                pythonCodeLength: pythonCode ? pythonCode.length : 0,
                agentActive,
                agentInput
            };
        })()
        """
        res = await send_eval(ws, test_script)
        print("Right panels verification:", json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(test_right_panels())
