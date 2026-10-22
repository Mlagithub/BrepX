import urllib.request
import os

base_url = 'https://www.cax-viewer.com/smlib/'

files = [
    'modeler.js',
    'geometry-worker.js',
    'kernel-client.js',
    'parametric-part.js',
    'feature-graph.js',
    'feature-commands.js',
    'feature-ui.js',
    'modeling-state.js',
    'modeling-ui.js',
    'modeling-interaction.js',
    'modeling-selection.js',
    'modeling-command-line.js',
    'camera-controls.js',
    'source-archive.js',
    'kernel/smlib.5dd21e03709b46c9.js'
]

os.makedirs('cax_reverse/kernel', exist_ok=True)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for rel_path in files:
    file_url = base_url + rel_path
    local_path = os.path.join('cax_reverse', rel_path.replace('/', os.sep))
    print(f'Fetching {file_url} -> {local_path}')
    try:
        req = urllib.request.Request(file_url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            with open(local_path, 'wb') as f:
                f.write(content)
            print(f'Saved {rel_path} ({len(content)} bytes)')
    except Exception as e:
        print(f'Failed to fetch {rel_path}: {e}')
