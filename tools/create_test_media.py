import os, json, urllib.request
ROOT = os.path.dirname(os.path.dirname(__file__))
MEDIA = os.path.join(ROOT, 'data', 'media')
TDIR = os.path.join(MEDIA, 'torrents')
os.makedirs(TDIR, exist_ok=True)
mp4_url = 'https://sample-videos.com/video123/mp4/240/big_buck_bunny_240p_1mb.mp4'
mp4_name = 'test_video.mp4'
mp4_path = os.path.join(TDIR, mp4_name)
print('Downloading sample mp4 to', mp4_path)
try:
    urllib.request.urlretrieve(mp4_url, mp4_path)
    print('Downloaded')
except Exception as e:
    print('Download failed:', e)
    # create empty placeholder
    with open(mp4_path, 'wb') as f:
        f.write(b'')
    print('Wrote empty placeholder')
# create a dummy .torrent file
torrent_name = 'test_video.torrent'
torrent_path = os.path.join(TDIR, torrent_name)
with open(torrent_path, 'wb') as f:
    f.write(b'Dummy torrent file for UI test')
print('Created dummy torrent at', torrent_path)
# update owners.json
owners_file = os.path.join(MEDIA, 'owners.json')
try:
    if os.path.exists(owners_file):
        with open(owners_file, 'r', encoding='utf-8') as f:
            owners = json.load(f)
    else:
        owners = {}
except Exception:
    owners = {}
owners['torrents/' + torrent_name] = 'testuser'
owners['torrents/' + mp4_name] = 'testuser'
with open(owners_file, 'w', encoding='utf-8') as f:
    json.dump(owners, f, indent=2, ensure_ascii=False)
print('Updated owners.json with testuser mapping')
print('Done')
