import os, io, requests, tempfile, hashlib
from PIL import Image, ImageDraw, ImageFont

# Adjust file_id/chat_id if needed
token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = 163103382
file_id = 'BQACAgEAAxkBAAM1aVUS6yBt4Az2IdGLqw58ECtHt0wAAkwGAAJoualGMhFunqqzVwQ4BA'

if not token:
    print('NO_TOKEN')
    raise SystemExit(1)

# get file info
r = requests.get(f'https://api.telegram.org/bot{token}/getFile', params={'file_id': file_id}, timeout=30)
if not r.ok:
    print('GETFILE_ERR', r.status_code, r.text)
    raise SystemExit(1)
file_path = r.json().get('result', {}).get('file_path')
if not file_path:
    print('NO_FILE_PATH')
    raise SystemExit(1)

# download file
download_url = f'https://api.telegram.org/file/bot{token}/{file_path}'
resp = requests.get(download_url, stream=True, timeout=60)
resp.raise_for_status()

fd, fname = tempfile.mkstemp(suffix='.torrent')
os.close(fd)
with open(fname, 'wb') as f:
    for chunk in resp.iter_content(8192):
        if chunk:
            f.write(chunk)

size = os.path.getsize(fname)
sha = hashlib.sha256()
with open(fname, 'rb') as f:
    for chunk in iter(lambda: f.read(8192), b''):
        if not chunk:
            break
        sha.update(chunk)
hexsha = sha.hexdigest()

# build cover
W, H = 700, 200
im = Image.new('RGB', (W, H), color=(24,24,28))
d = ImageDraw.Draw(im)
try:
    font = ImageFont.truetype('arial.ttf', 16)
except Exception:
    font = ImageFont.load_default()

name = os.path.basename(file_path)
d.text((16,16), f'Archivo: {name}', fill=(240,240,240), font=font)
d.text((16,46), f'Tamaño: {size} bytes ({size//1024} KB)', fill=(200,200,220), font=font)
d.text((16,76), f'SHA256: {hexsha[:16]}...', fill=(200,200,200), font=font)
d.text((16,106), f'Fuente: Telegram upload by chat {chat_id}', fill=(180,200,180), font=font)
d.text((16,136), 'Acción: responde con /stream_torrent para iniciar streaming', fill=(180,180,250), font=font)

# send image
buf = io.BytesIO()
im.save(buf, format='PNG')
buf.seek(0)
caption = f'{name} — {size//1024} KB — SHA256 {hexsha[:16]}...'
post = requests.post(
    f'https://api.telegram.org/bot{token}/sendPhoto',
    data={'chat_id': chat_id, 'caption': caption},
    files={'photo': ('cover.png', buf, 'image/png')},
    timeout=60
)
print('SEND_STATUS', post.status_code)
print(post.text)

try:
    os.unlink(fname)
except Exception:
    pass
