"""Expose modelGroup to window and inspect meshes count."""

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
            const vp = await import('./js/viewport.js');
            let meshCount = 0;
            let lineCount = 0;
            vp.modelGroup.traverse(c => {
                if (c.isMesh) meshCount++;
                if (c.isLine) lineCount++;
            });
            const box = new (await import('three')).Box3().setFromObject(vp.modelGroup);
            return {
                children: vp.modelGroup.children.length,
                meshCount,
                lineCount,
                boxMin: [box.min.x, box.min.y, box.min.z],
                boxMax: [box.max.x, box.max.y, box.max.z],
                cameraPos: [vp.activeCamera.position.x, vp.activeCamera.position.y, vp.activeCamera.position.z],
                cameraTarget: [vp.controls.target.x, vp.controls.target.y, vp.controls.target.z]
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
