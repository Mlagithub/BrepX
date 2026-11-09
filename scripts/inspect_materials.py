"""Inspect face mesh materials and rendering properties."""

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
            const faces = [];
            vp.modelGroup.traverse(c => {
                if (c.isMesh) {
                    faces.push({
                        visible: c.visible,
                        materialColor: '#' + c.material.color.getHexString(),
                        opacity: c.material.opacity,
                        transparent: c.material.transparent,
                        wireframe: c.material.wireframe,
                        vertexCount: c.geometry.attributes.position.count,
                        indexCount: c.geometry.index ? c.geometry.index.count : 0
                    });
                }
            });
            return {
                facesCount: faces.length,
                firstFace: faces[0],
                rendererDom: {
                    clientWidth: vp.renderer.domElement.clientWidth,
                    clientHeight: vp.renderer.domElement.clientHeight,
                    style: vp.renderer.domElement.style.cssText
                }
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
