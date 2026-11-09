"""Examine pixel colors from the canvas center directly via WebGL readPixels."""

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
            vp.renderer.render(vp.scene, vp.activeCamera);
            const gl = vp.renderer.getContext();
            const w = gl.drawingBufferWidth;
            const h = gl.drawingBufferHeight;

            // Sample center 20x20 pixels
            const pixels = new Uint8Array(4 * 20 * 20);
            gl.readPixels(Math.floor(w / 2 - 10), Math.floor(h / 2 - 10), 20, 20, gl.RGBA, gl.UNSIGNED_BYTE, pixels);

            let hasModelColor = false;
            let sampleColor = [];
            for (let i = 0; i < pixels.length; i += 4) {
                const r = pixels[i];
                const g = pixels[i + 1];
                const b = pixels[i + 2];
                // Background is 0x1a, 0x1d, 0x24 (26, 29, 36)
                if (r > 40 || g > 40 || b > 50) {
                    hasModelColor = true;
                    sampleColor = [r, g, b, pixels[i + 3]];
                    break;
                }
            }

            return {
                bufferWidth: w,
                bufferHeight: h,
                hasModelColor,
                sampleColor,
                centerPixel: [pixels[0], pixels[1], pixels[2], pixels[3]]
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
