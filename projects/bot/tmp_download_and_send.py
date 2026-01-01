import os
import io
import sys
import time
import tempfile
import requests
import subprocess
import shutil
import hashlib

BOT_TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = 163103382
FILE_ID = 'BQACAgEAAxkBAAM1aVUS6yBt4Az2IdGLqw58ECtHt0wAAkwGAAJoualGMhFunqqzVwQ4BA'

if not BOT_TOKEN:
    print('NO_TOKEN')
    sys.exit(1)

session = requests.Session()

def get_file_path(file_id):
    r = session.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getFile', params={'file_id': file_id}, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get('result', {}).get('file_path')


def download_file_path(file_path, dest):
    url = f'https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}'
    r = session.get(url, stream=True, timeout=60)
    r.raise_for_status()
    with open(dest, 'wb') as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)


def try_libtorrent_download(torrent_path, dest_dir, timeout=600):
    try:
        import libtorrent as lt
    except Exception:
        return None
    ses = lt.session()
    ses.listen_on(6881, 6891)
    ti = lt.torrent_info(torrent_path)
    h = ses.add_torrent({'ti': ti, 'save_path': dest_dir})
    # wait for download to finish or timeout
    total_size = sum(ti.files().size(i) for i in range(ti.files().num_files()))
    start = time.time()
    while time.time() - start < timeout:
        s = h.status()
        if getattr(s, 'state', None) == lt.torrent_status.seeding or h.is_seed():
            break
        time.sleep(2)
    # return path to largest file
    files = ti.files()
    sizes = [(i, files.size(i)) for i in range(files.num_files())]
    idx, _ = max(sizes, key=lambda x: x[1])
    rel = files.file_path(idx)
    return os.path.join(dest_dir, rel)


def try_aria2c_download(torrent_path, dest_dir, timeout=1800):
    if shutil.which('aria2c') is None:
        return None
    cmd = ['aria2c', '--dir', dest_dir, '--max-concurrent-downloads=1', torrent_path]
    proc = subprocess.Popen(cmd)
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return None
    # find newest file
    files = [os.path.join(dest_dir, f) for f in os.listdir(dest_dir)]
    if not files:
        return None
    files = sorted(files, key=os.path.getmtime, reverse=True)
    # if torrent extracted multiple files into subdirs, walk dest_dir
    largest = None
    largest_size = -1
    for root, _, fnames in os.walk(dest_dir):
        for fn in fnames:
            p = os.path.join(root, fn)
            try:
                sz = os.path.getsize(p)
            except Exception:
                sz = 0
            if sz > largest_size:
                largest_size = sz
                largest = p
    return largest


def send_document(chat_id, path):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    with open(path, 'rb') as f:
        files = {'document': (os.path.basename(path), f)}
        data = {'chat_id': str(chat_id)}
        r = session.post(url, data=data, files=files, timeout=300)
    r.raise_for_status()
    return r.json()


def main():
    tmp_torrent_fd, tmp_torrent = tempfile.mkstemp(suffix='.torrent')
    os.close(tmp_torrent_fd)
    try:
        print('Fetching .torrent file info...')
        file_path = get_file_path(FILE_ID)
        if not file_path:
            print('NO_FILE_PATH')
            return
        print('Downloading .torrent to', tmp_torrent)
        download_file_path(file_path, tmp_torrent)
        print('Downloaded .torrent, size', os.path.getsize(tmp_torrent))
        # attempt libtorrent first
        tmpdir = tempfile.mkdtemp()
        print('Attempting libtorrent download (if available)')
        target = None
        try:
            target = try_libtorrent_download(tmp_torrent, tmpdir, timeout=600)
        except Exception as e:
            print('libtorrent error', e)
            target = None
        if target and os.path.exists(target):
            print('libtorrent download produced', target)
        else:
            print('libtorrent not available or failed, trying aria2c')
            try:
                target = try_aria2c_download(tmp_torrent, tmpdir, timeout=1800)
            except Exception as e:
                print('aria2c error', e)
                target = None
        if not target:
            print('Download failed (no backend)')
            return
        print('Selected file to send:', target)
        # send file
        resp = send_document(CHAT_ID, target)
        print('SEND_OK', resp.get('ok'))
    finally:
        try:
            os.unlink(tmp_torrent)
        except Exception:
            pass

if __name__ == '__main__':
    main()
