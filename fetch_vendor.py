import urllib.request
import os

base_url = 'https://www.cax-viewer.com/smlib/vendor/'
files = [
    'three.module.js',
    'three.core.js',
    'lines/LineMaterial.js',
    'lines/LineSegments2.js',
    'lines/LineSegmentsGeometry.js'
]

os.makedirs('static/vendor/lines', exist_ok=True)
headers = {'User-Agent': 'Mozilla/5.0'}

for rel in files:
    url = base_url + rel
    target = os.path.join('static/vendor', rel.replace('/', os.sep))
    print(f'Fetching {url} -> {target}')
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            with open(target, 'wb') as f:
                f.write(data)
            print(f'Saved {rel} ({len(data)} bytes)')
    except Exception as e:
        print(f'Error fetching {rel}: {e}')
