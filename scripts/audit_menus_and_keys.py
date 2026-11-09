"""Complete audit of mouse right click, Space palette, Z pie menu, Shift+A add menu."""

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


async def audit_mouse_keyboard_interactions() -> None:
    targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
    page = next(t for t in targets if t["type"] == "page" and "8080" in t.get("url", ""))
    ws_url = page["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url) as ws:
        print("=== Auditing Menus, Shortcuts and Mouse Interactions ===")

        # 1. Right Click Context Menu
        print("\n[Test 1] Right click on viewport...")
        rclick_res = await send_eval(
            ws,
            """
            (function() {
                const vp = document.getElementById('viewport');
                const evt = new MouseEvent('contextmenu', {
                    clientX: 400,
                    clientY: 300,
                    bubbles: true,
                    cancelable: true
                });
                vp.dispatchEvent(evt);
                const menu = document.getElementById('cad-context-menu');
                return {
                    visible: menu && !menu.classList.contains('hidden'),
                    itemCount: menu ? menu.querySelectorAll('.ctx-menu-item').length : 0
                };
            })()
        """,
        )
        print("Test 1 (Context Menu):", rclick_res)
        assert rclick_res["visible"] and rclick_res["itemCount"] > 0, "Right click menu should open with items"

        # 2. Shift + A Add Menu
        print("\n[Test 2] Shift + A Add Menu...")
        add_res = await send_eval(
            ws,
            """
            (function() {
                // Click away to close context menu first
                document.body.click();
                const evt = new KeyboardEvent('keydown', {
                    key: 'A',
                    shiftKey: true,
                    bubbles: true
                });
                window.dispatchEvent(evt);
                const menu = document.getElementById('shift-a-add-menu');
                return {
                    visible: menu && !menu.classList.contains('hidden'),
                    itemCount: menu ? menu.querySelectorAll('.add-menu-item').length : 0
                };
            })()
        """,
        )
        print("Test 2 (Shift+A Add Menu):", add_res)
        assert add_res["visible"] and add_res["itemCount"] > 10, "Shift+A menu should open with items"

        # 3. Z Key Radial Pie Menu
        print("\n[Test 3] Z Key Radial Pie Menu...")
        pie_res = await send_eval(
            ws,
            """
            (function() {
                document.body.click();
                const evt = new KeyboardEvent('keydown', {
                    key: 'z',
                    bubbles: true
                });
                window.dispatchEvent(evt);
                const menu = document.getElementById('cad-pie-menu');
                return {
                    visible: menu && !menu.classList.contains('hidden'),
                    sectorCount: menu ? menu.querySelectorAll('.pie-sector-btn').length : 0
                };
            })()
        """,
        )
        print("Test 3 (Pie Menu):", pie_res)
        assert pie_res["visible"] and pie_res["sectorCount"] == 4, "Pie menu should open with 4 sectors"

        # 4. Spacebar Command Palette
        print("\n[Test 4] Spacebar Command Palette...")
        palette_res = await send_eval(
            ws,
            """
            (function() {
                document.body.click();
                const evt = new KeyboardEvent('keydown', {
                    key: ' ',
                    bubbles: true
                });
                window.dispatchEvent(evt);
                const modal = document.getElementById('command-palette-modal');
                const input = document.getElementById('palette-search-input');
                return {
                    visible: modal && !modal.classList.contains('hidden'),
                    hasInput: !!input
                };
            })()
        """,
        )
        print("Test 4 (Command Palette):", palette_res)
        assert palette_res["visible"] and palette_res["hasInput"], "Command palette should open"

        # 5. Fuzzy search in Command Palette
        print("\n[Test 5] Searching 'runner' in Command Palette...")
        search_res = await send_eval(
            ws,
            """
            (function() {
                const input = document.getElementById('palette-search-input');
                input.value = 'runner';
                input.dispatchEvent(new Event('input', { bubbles: true }));
                const items = Array.from(document.querySelectorAll('.palette-item'));
                return {
                    count: items.length,
                    firstMatch: items[0]?.textContent
                };
            })()
        """,
        )
        print("Test 5 (Fuzzy Search):", search_res)
        assert search_res["count"] >= 1 and "blade_runner" in search_res["firstMatch"], "Fuzzy search should find Blade Runner"

        print("\n=== All Menus and Keyboard Interactions PASSED! ===")


if __name__ == "__main__":
    asyncio.run(audit_mouse_keyboard_interactions())
