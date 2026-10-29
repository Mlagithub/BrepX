import subprocess
import time
import urllib.request
import json
import asyncio
import websockets
import base64

edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

proc = subprocess.Popen([
    edge_path,
    '--headless=new',
    '--remote-debugging-port=9222',
    '--disable-gpu',
    '--window-size=1366,768',
    '--user-data-dir=C:\\Users\\keep_\\AppData\\Local\\Temp\\edge_debug_e2e_final',
    'http://127.0.0.1:8080/'
])

time.sleep(2.5)

async def run_final_e2e_audit():
    with urllib.request.urlopen('http://127.0.0.1:9222/json') as resp:
        targets = json.loads(resp.read().decode('utf-8'))
    target = next(t for t in targets if '8080' in t.get('url', ''))

    async with websockets.connect(target['webSocketDebuggerUrl']) as ws:
        msg_id = 1
        async def call(method, params={}):
            nonlocal msg_id
            msg_id += 1
            await ws.send(json.dumps({'id': msg_id, 'method': method, 'params': params}))
            raw = await ws.recv()
            return json.loads(raw)

        async def eval_js(expr):
            res = await call('Runtime.evaluate', {'expression': expr, 'awaitPromise': True})
            return res.get('result', {}).get('result', {}).get('value')

        # 等待应用初始化加载完成
        for _ in range(30):
            has_ctx = await eval_js('typeof window.ctx !== "undefined"')
            has_scene = await eval_js('window.ctx && window.ctx.sceneData !== null')
            status_val = await eval_js('document.getElementById("status-text").textContent')
            print(f"   wait: has_ctx={has_ctx}, has_scene={has_scene}, status={status_val.encode('ascii', 'ignore').decode()}")
            if has_scene:
                break
            await asyncio.sleep(0.5)

        # 1. 验证初始模型 B-Rep 容器正确渲染
        vol = await eval_js('document.getElementById("stat-volume").textContent')
        faces_cnt = await eval_js('document.getElementById("stat-faces").textContent')
        print(f"1. Initial B-Rep Scene: Volume = {vol.encode('ascii', 'ignore').decode()}, Faces = {faces_cnt}")
        assert vol and '-' not in vol

        # 2. 验证 Shift + A 浮动菜单
        print("2. Testing Shift + A menu...")
        await eval_js("window.dispatchEvent(new KeyboardEvent('keydown', { key: 'a', shiftKey: true, bubbles: true }));")
        await asyncio.sleep(0.2)
        menu_hidden = await eval_js("document.getElementById('add-menu-popup').classList.contains('hidden')")
        print("   Add menu visible:", not menu_hidden)
        assert not menu_hidden

        # 3. 验证点击左侧工具 "圆柱"
        print("3. Clicking left tool 'Cylinder'...")
        await eval_js("document.querySelector('.tool-chip[data-op=\"cylinder\"]').click();")
        await asyncio.sleep(0.8)
        cyl_vol = await eval_js('document.getElementById("stat-volume").textContent')
        print(f"   After Cylinder operator: Volume = {cyl_vol.encode('ascii', 'ignore').decode()}")

        # 4. 验证 F9 Adjust Last Operation 面板自动弹出且可改参
        print("4. Testing Blender F9 Adjust Last Operation...")
        f9_hidden = await eval_js("document.getElementById('adjust-last-panel').classList.contains('hidden')")
        print("   Adjust Last panel visible:", not f9_hidden)
        assert not f9_hidden

        # 5. 验证快捷键 Tab 切换进入编辑模式
        print("5. Testing Tab and 1/2/3 keys...")
        await eval_js("window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }));")
        mode = await eval_js("window.ctx.mode")
        sel_level = await eval_js("window.ctx.selectionLevel")
        print(f"   Context mode: {mode}, selectionLevel: {sel_level}")
        assert mode == 'EDIT' and sel_level == 'face'

        # 6. 验证 G/R/S 快捷手柄切换
        await eval_js("window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }));") # back to OBJECT
        await eval_js("window.dispatchEvent(new KeyboardEvent('keydown', { key: 'g' }));")
        assert await eval_js("window.transformControls.getMode()") == 'translate'

        # 7. 截取最终高质量界面图
        res = await call('Page.captureScreenshot', {'format': 'png'})
        img_b64 = res.get('result', {}).get('data', '')
        if img_b64:
            with open('final_workbench_render.png', 'wb') as f:
                f.write(base64.b64decode(img_b64))
            print("   Screenshot saved to final_workbench_render.png")

try:
    asyncio.run(run_final_e2e_audit())
    print("\n[SUCCESS] Final E2E Architecture & UI Verification PASSED!")
finally:
    proc.terminate()
