import urllib.request
import os

os.makedirs('static/utils', exist_ok=True)

files = {
    'static/utils/BufferGeometryUtils.js': 'https://unpkg.com/three@0.186.0/examples/jsm/utils/BufferGeometryUtils.js',
    'static/utils/SkeletonUtils.js': 'https://unpkg.com/three@0.186.0/examples/jsm/utils/SkeletonUtils.js'
}

headers = {'User-Agent': 'Mozilla/5.0'}
for path, url in files.items():
    print(f'Fetching {url} -> {path}')
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            with open(path, 'wb') as f:
                f.write(data)
            print(f'Saved {path} ({len(data)} bytes)')
    except Exception as e:
        print(f'Error fetching {url}: {e}')
