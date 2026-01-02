import requests, os, json

url = 'http://127.0.0.1:8082/stream/add_magnet'
magnet = 'magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567&dn=Test+Magnet'
print('Posting magnet to', url)
headers = {'X-User': 'plex'}
resp = requests.post(url, json={'magnet': magnet}, headers=headers, timeout=10)
print('Status', resp.status_code)
try:
    print('JSON:', resp.json())
except Exception:
    print('Text:', resp.text)

# show plex dir and owners
from_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'media', 'torrents'))
owners_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'media', 'owners.json'))
print('Plex dir:', from_path)
if os.path.exists(from_path):
    for f in os.listdir(from_path):
        print(' -', f)
else:
    print('Plex dir missing')

if os.path.exists(owners_file):
    print('Owners:')
    print(json.dumps(json.load(open(owners_file, 'r', encoding='utf-8')), indent=2, ensure_ascii=False))
else:
    print('Owners file missing')
