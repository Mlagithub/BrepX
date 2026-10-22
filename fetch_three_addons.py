import urllib.request
import os

files = {
    'OrbitControls.js': 'https://unpkg.com/three@0.186.0/examples/jsm/controls/OrbitControls.js',
    'GLTFLoader.js': 'https://unpkg.com/three@0.186.0/examples/jsm/loaders/GLTFLoader.js',
}

headers = {'User-Agent': 'Mozilla/5.0'}
for name, url in files.items():
    path = os.path.join('static', 'vendor', name)
    print(f'Fetching {url} -> {path}')
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            with open(path, 'wb') as f:
                f.write(content)
            print(f'Saved {name} ({len(content)} bytes)')
    except Exception as e:
        print(f'Failed to fetch {name}: {e}')
