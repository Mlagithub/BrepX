"""Inspect modelGroup contents and meshes count."""

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
            // Check api/scene response directly from browser
            const res = await fetch('/api/scene');
            const data = await res.json();
            return {
                sceneBodies: data.bodies?.length,
                faces: data.bodies?.[0]?.faces?.length,
                edges: data.bodies?.[0]?.edges?.length
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
        print(json.dumps(resp.get("result", {}).get("result", {}).get("value", {}), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
