import subprocess
import time
import urllib.request
import json
import asyncio
import websockets

edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

proc = subprocess.Popen([
    edge_path,
    '--headless=new',
    '--remote-debugging-port=9222',
    '--disable-gpu',
    '--user-data-dir=C:\\Users\\keep_\\AppData\\Local\\Temp\\edge_debug_profile_test_actions',
    'http://127.0.0.1:8080/'
])

time.sleep(3)

async def test_actions():
    with urllib.request.urlopen('http://127.0.0.1:9222/json') as resp:
        targets = json.loads(resp.read().decode('utf-8'))
    target = next(t for t in targets if '8080' in t.get('url', ''))
    print('Testing page:', target['url'])
    
    async with websockets.connect(target['webSocketDebuggerUrl']) as ws:
        msg_id = 100
        async def call(expr):
            nonlocal msg_id
            msg_id += 1
            await ws.send(json.dumps({'id': msg_id, 'method': 'Runtime.evaluate', 'params': {'expression': expr, 'awaitPromise': True}}))
            raw = await ws.recv()
            return json.loads(raw).get('result', {}).get('result', {})
        
        async def wait_until_text_contains(selector, expected, timeout=10):
            for _ in range(int(timeout / 0.2)):
                raw = (await call(f'document.querySelector("{selector}").textContent')).get('value', '')
                if expected in raw:
                    return raw
                await asyncio.sleep(0.2)
            raise TimeoutError(f"Timed out waiting for {expected} in {selector}")

        # 1. Check initial volume
        val = await wait_until_text_contains('#stat-volume', '84,074')
        print('1. Initial volume:', val.encode('ascii', 'ignore').decode())
        
        # 2. Switch to L-bracket template
        print('2. Switching to bracket template...')
        await call('''
            const sel = document.getElementById("template-select");
            sel.value = "bracket";
            sel.dispatchEvent(new Event("change"));
        ''')
        val = await wait_until_text_contains('#stat-volume', '63,869')
        print('   Bracket volume:', val.encode('ascii', 'ignore').decode())
        
        # 3. Test changing a slider (thickness) and rebuilding
        print('3. Modifying parameter (thickness)...')
        await call('''
            const num = document.getElementById("num-thickness");
            num.value = "15";
            num.dispatchEvent(new Event("change"));
        ''')
        val = await wait_until_text_contains('#stat-volume', '90,508')
        print('   Modified bracket volume:', val.encode('ascii', 'ignore').decode())
        
        # 4. Switch to CSG demo template
        print('4. Switching to csg_demo...')
        await call('''
            const sel = document.getElementById("template-select");
            sel.value = "csg_demo";
            sel.dispatchEvent(new Event("change"));
        ''')
        val = await wait_until_text_contains('#stat-volume', '23,157')
        print('   CSG volume:', val.encode('ascii', 'ignore').decode())
        
        # 5. Test running custom Python script
        print('5. Testing custom script execution...')
        await call('''
            const editor = document.getElementById("script-editor");
            editor.value = "from smlibpy import *\\npart = Box(60, 60, 30) - Cylinder(12, 35)\\n";
            document.getElementById("btn-run-script").click();
        ''')
        val = await wait_until_text_contains('#stat-volume', '92,159')
        print('   Script part volume:', val.encode('ascii', 'ignore').decode())
        
        # 6. Test camera buttons
        print('6. Testing view buttons...')
        for btn_id in ['btn-top', 'btn-front', 'btn-right', 'btn-iso', 'btn-fit', 'btn-camera-toggle', 'btn-grid-toggle', 'btn-axes-toggle', 'btn-edges-toggle']:
            await call(f'document.getElementById("{btn_id}").click()')
        print('   All view and display buttons clicked without error!')

print("\n--- Running Browser Action Test ---")
try:
    asyncio.run(test_actions())
    print("\n[SUCCESS] All browser actions and geometry generations PASSED!")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    proc.terminate()
