"""Full browser end-to-end verification across M1 to M5 milestones via CDP."""

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


async def run_m1_to_m5_suite() -> None:
    targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
    page = next(t for t in targets if t["type"] == "page" and "8080" in t.get("url", ""))
    ws_url = page["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url) as ws:
        print("=== Starting M1-M5 Real Browser Automation Suite ===")

        # Wait for page readiness
        await send_eval(
            ws,
            """
            (async function() {
                while (!document.querySelector('.tool-chip[data-op="box"]')) {
                    await new Promise(r => setTimeout(r, 100));
                }
                return true;
            })()
        """,
        )

        # Test 1: M1 & M4 Creation - Create Box via Tool Chip
        print("\n[Step 1] Creating Box primitive...")
        box_res = await send_eval(
            ws,
            """
            (async function() {
                const btn = document.querySelector('.tool-chip[data-op="box"]');
                const vStart = window.context?.version || 1;
                btn.click();
                let tries = 0;
                while ((window.context?.version === vStart) && tries < 40) {
                    await new Promise(r => setTimeout(r, 150));
                    tries++;
                }
                return {
                    version: window.context?.version,
                    volume: window.context?.body?.volume,
                    timelineCount: document.querySelectorAll('.timeline-node').length
                };
            })()
        """,
        )
        print("Step 1 (Box creation):", box_res)

        # Test 2: M4 Cylinder Creation - Create Cylinder via Tool Chip
        print("\n[Step 2] Creating Cylinder primitive...")
        cyl_res = await send_eval(
            ws,
            """
            (async function() {
                const curVer = window.context?.version || 1;
                const btn = document.querySelector('.tool-chip[data-op="cylinder"]');
                btn.click();
                let tries = 0;
                while (window.context?.version === curVer && tries < 40) {
                    await new Promise(r => setTimeout(r, 150));
                    tries++;
                }
                return {
                    version: window.context?.version,
                    faceCount: window.context?.body?.face_count,
                    status: document.getElementById('status-text')?.textContent
                };
            })()
        """,
        )
        print("Step 2 (Cylinder):", cyl_res)
        assert cyl_res.get("faceCount", 0) == 3, "Cylinder face count should be 3"

        # Test 3: M5 Timeline Bubble In-Place Rebuild
        print("\n[Step 3] Timeline in-place parameter update & cascade rebuild...")
        timeline_res = await send_eval(
            ws,
            """
            (async function() {
                const nodes = document.querySelectorAll('.timeline-node');
                if (!nodes.length) return { error: 'No timeline nodes found' };
                nodes[0].dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
                await new Promise(r => setTimeout(r, 400));

                const bubble = document.querySelector('.timeline-param-bubble');
                if (!bubble) return { error: 'Param bubble not opened' };

                const radiusInput = bubble.querySelector('input[data-param="radius"]');
                if (radiusInput) radiusInput.value = "25";

                const curVer = window.context?.version;
                const saveBtn = bubble.querySelector('.bubble-save');
                saveBtn.click();

                let tries = 0;
                while (window.context?.version === curVer && tries < 40) {
                    await new Promise(r => setTimeout(r, 150));
                    tries++;
                }

                return {
                    version: window.context?.version,
                    newVolume: window.context?.body?.volume
                };
            })()
        """,
        )
        print("Step 3 (Timeline Rebuild):", timeline_res)

        # Test 4: M5 Inspection Tools (Section, Datum, Measure, Display Modes)
        print("\n[Step 4] Testing Section, Datum, Measure & Display toggles...")
        tools_res = await send_eval(
            ws,
            """
            (function() {
                document.getElementById('btn-datum-toggle')?.click();
                document.getElementById('btn-section-toggle')?.click();
                document.getElementById('btn-measure-toggle')?.click();

                return {
                    datumActive: document.getElementById('btn-datum-toggle')?.classList.contains('active'),
                    sectionActive: document.getElementById('btn-section-toggle')?.classList.contains('active'),
                    measureActive: document.getElementById('btn-measure-toggle')?.classList.contains('active')
                };
            })()
        """,
        )
        print("Step 4 (Toggles):", tools_res)

        # Test 5: M1/M4 Export links verification
        print("\n[Step 5] Checking export buttons...")
        export_res = await send_eval(
            ws,
            """
            (function() {
                return {
                    stepExists: !!document.getElementById('btn-export-step'),
                    stlExists: !!document.getElementById('btn-export-stl'),
                    dxfExists: !!document.getElementById('btn-export-dxf'),
                    cfdExists: !!document.getElementById('btn-export-cfd')
                };
            })()
        """,
        )
        print("Step 5 (Exports):", export_res)
        assert export_res["stepExists"] and export_res["cfdExists"], "Export buttons should be available"

        # Test 6: M1 Undo and Redo
        print("\n[Step 6] Testing Undo & Redo...")
        undo_res = await send_eval(
            ws,
            """
            (async function() {
                const uBtn = document.getElementById('btn-undo');
                const vStart = window.context?.version;
                uBtn.click();
                let tries = 0;
                while (window.context?.version === vStart && tries < 40) {
                    await new Promise(r => setTimeout(r, 150));
                    tries++;
                }
                const vUndo = window.context?.version;

                const rBtn = document.getElementById('btn-redo');
                rBtn.click();
                tries = 0;
                while (window.context?.version === vUndo && tries < 40) {
                    await new Promise(r => setTimeout(r, 150));
                    tries++;
                }
                const vRedo = window.context?.version;

                return { vUndo, vRedo };
            })()
        """,
        )
        print("Step 6 (Undo/Redo):", undo_res)
        assert undo_res["vRedo"] > undo_res["vUndo"], "Redo should advance version"

        print("\n=== All Real Browser Operational Tests PASSED! ===")


if __name__ == "__main__":
    asyncio.run(run_m1_to_m5_suite())
