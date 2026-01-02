import os, json, importlib.util

# Load stream_server.py by path (module isn't a package)
here = os.path.abspath(os.path.dirname(__file__))
mod_path = os.path.abspath(os.path.join(here, '..', 'python_api', 'stream_server.py'))
spec = importlib.util.spec_from_file_location('stream_server_mod', mod_path)
stream_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stream_server)

TORRENTS_DIR = stream_server.TORRENTS_DIR
PLEX_DIR = stream_server.PLEX_TORRENTS_DIR
MEDIA_DIR = stream_server.MEDIA_DIR
OWNERS_FILE = stream_server.MEDIA_OWNERS_FILE

os.makedirs(TORRENTS_DIR, exist_ok=True)
os.makedirs(PLEX_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)

# create a small dummy torrent file
src = os.path.join(TORRENTS_DIR, 'test_sync.torrent')
with open(src, 'wb') as f:
    f.write(b'test-torrent-data')

print('Created:', src)

ok = stream_server._sync_torrent_to_plex(src, 'test_sync.torrent')
print('sync result:', ok)

# list files in plex dir
print('Plex dir listing:')
for p in os.listdir(PLEX_DIR):
    print(' -', p)

# show owners.json
if os.path.exists(OWNERS_FILE):
    with open(OWNERS_FILE, 'r', encoding='utf-8') as f:
        try:
            owners = json.load(f)
        except Exception:
            owners = None
    print('owners.json content:')
    print(json.dumps(owners, indent=2, ensure_ascii=False))
else:
    print('owners.json not found at', OWNERS_FILE)
