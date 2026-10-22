import urllib.request
import re
import json

url = 'https://www.cax-viewer.com/smlib/'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

print('HTML length:', len(html))

# Save html for analysis
with open('cax_index.html', 'w', encoding='utf-8') as f:
    f.write(html)

scripts = re.findall(r'<script[^>]*src=[\'"]([^\'"]+)[\'"]', html, re.IGNORECASE)
print('Script src tags:')
for s in scripts:
    print(' -', s)

links = re.findall(r'<link[^>]*href=[\'"]([^\'"]+)[\'"]', html, re.IGNORECASE)
print('Link tags:')
for l in links:
    print(' -', l)

# Inline scripts
inline_scripts = re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', html, re.IGNORECASE | re.DOTALL)
print('Inline scripts count:', len(inline_scripts))
for i, s in enumerate(inline_scripts):
    print(f'--- Inline script {i} ({len(s)} chars) ---')
    print(s[:500])
