import os, sys
try:
    import requests
except Exception:
    print('requests library not installed. Install with: pip install requests')
    sys.exit(2)

HERE = os.path.abspath(os.path.dirname(__file__))
from_path = os.path.abspath(os.path.join(HERE, '..', 'python_api', '..', 'data', 'torrents', 'http_test_upload.torrent'))
# ensure directory
os.makedirs(os.path.dirname(from_path), exist_ok=True)
with open(from_path, 'wb') as f:
    f.write(b'http-upload-test')
print('Created file:', from_path)

for url in ('http://127.0.0.1:8082/stream/upload_torrent', 'http://127.0.0.1:8000/stream/upload_torrent'):
    print('\nUploading to', url)
    try:
        with open(from_path, 'rb') as fh:
            files = {'file': ('http_test_upload.torrent', fh)}
            r = requests.post(url, files=files, timeout=10)
        print('Status:', r.status_code)
        try:
            print('JSON:', r.json())
        except Exception:
            print('Text:', r.text[:1000])
    except Exception as e:
        print('Request failed:', str(e))
        # continue to next
