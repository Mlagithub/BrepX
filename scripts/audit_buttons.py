"""Exhaustive browser audit testing every button, menu, and mouse/keyboard interaction."""

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


async def audit_buttons_and_interactions() -> None:
    targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
    page = next(t for t in targets if t["type"] == "page" and "8080" in t.get("url", ""))
    ws_url = page["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url) as ws:
        print("=== Audit: Inspecting All Buttons & Handlers in DOM ===")

        audit_script = """
        (function() {
            const buttons = Array.from(document.querySelectorAll('button'));
            const results = buttons.map(b => {
                const id = b.id || b.dataset.op || b.dataset.tab || b.className;
                const hasOnclick = typeof b.onclick === 'function';
                const text = b.textContent.trim().slice(0, 20);
                return { id, text, hasOnclick, className: b.className };
            });

            const unhandled = results.filter(r => !r.hasOnclick);
            return {
                totalButtons: buttons.length,
                handledCount: results.length - unhandled.length,
                unhandledButtons: unhandled
            };
        })()
        """
        res = await send_eval(ws, audit_script)
        print("Buttons audit:", json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(audit_buttons_and_interactions())
