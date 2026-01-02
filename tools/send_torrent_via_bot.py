#!/usr/bin/env python3
import os
import sys
import requests
from urllib.parse import urljoin


def load_token():
    # prefer explicit env vars
    for name in ('BOT_TOKEN', 'TELEGRAM_BOT_TOKEN', 'TG_BOT_TOKEN'):
        v = os.environ.get(name)
        if v:
            return v
    # fallback to .env BOT_TOKEN
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.abspath(os.path.join(here, '..'))
        env_path = os.path.join(repo_root, '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as ef:
                for line in ef:
                    if '=' not in line:
                        continue
                    k, v = line.strip().split('=', 1)
                    if k == 'BOT_TOKEN' and v:
                        return v
    except Exception:
        pass
    return None


TOKEN = load_token()
if not TOKEN:
    print('ERROR: BOT_TOKEN not set in env or .env')
    sys.exit(2)


def find_torrent_file():
    # candidate paths in order
    candidates = [
        os.path.join('projects', 'bot', 'tmp_downloaded.torrent'),
        os.path.join('projects', 'bot', 'tmp_downloaded.torrent'.replace('tmp_', '')),
        os.path.join('data', 'torrents', 'tmp_downloaded.torrent'),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # try any .torrent file in data/torrents
    d = os.path.join('data', 'torrents')
    if os.path.isdir(d):
        for fname in os.listdir(d):
            if fname.endswith('.torrent'):
                return os.path.join(d, fname)
    return None


CHAT_ID = os.environ.get('TARGET_USER_ID') or os.environ.get('CHAT_ID') or os.environ.get('TG_CHAT_ID') or '163103382'

# allow override from environment (set by wrapper script)
env_selected = os.environ.get('SELECTED_TORRENT')
if env_selected and os.path.exists(env_selected):
    file_path = env_selected
else:
    file_path = find_torrent_file()
if not file_path:
    print('No local torrent file found; attempting to generate an accessible URL...')
    # if no file, try to use stream_server's torrent_url API to build one
    # only useful if stream_server is reachable at localhost:8082
    try:
        api = os.environ.get('STREAM_SERVER_URL', 'http://127.0.0.1:8082')
        # try to find a file name in data/torrents
        d = os.path.join('data', 'torrents')
        name = None
        if os.path.isdir(d):
            for fname in os.listdir(d):
                if fname.endswith('.torrent'):
                    name = fname
                    break
        if name:
            r = requests.post(urljoin(api, '/stream/torrent_url'), json={'name': name}, timeout=10)
            jr = r.json()
            if jr.get('ok') and jr.get('url'):
                url = jr['url']
                print('Generated URL for torrent:', url)
                # send by URL
                send_by_url = True
            else:
                print('No torrent available and failed to generate URL')
                sys.exit(3)
        else:
            print('No torrent files found in data/torrents')
            sys.exit(3)
    except Exception as e:
        print('Error while trying to generate torrent URL:', e)
        sys.exit(3)
else:
    send_by_url = False


def send_file(token, chat_id, path):
    url = f'https://api.telegram.org/bot{token}/sendDocument'
    with open(path, 'rb') as fh:
        files = {'document': (os.path.basename(path), fh)}
        data = {'chat_id': chat_id}
        try:
            r = requests.post(url, data=data, files=files, timeout=60)
        except Exception as e:
            print('HTTP error:', e)
            return False, None
        try:
            jr = r.json()
        except Exception:
            print('HTTP', r.status_code, r.text)
            return False, None
        return jr.get('ok', False), jr


def send_url(token, chat_id, file_url):
    url = f'https://api.telegram.org/bot{token}/sendDocument'
    data = {'chat_id': chat_id, 'document': file_url}
    try:
        r = requests.post(url, data=data, timeout=30)
        jr = r.json()
        return jr.get('ok', False), jr
    except Exception as e:
        print('HTTP error:', e)
        return False, None


if not send_by_url:
    ok, resp = send_file(TOKEN, CHAT_ID, file_path)
else:
    ok, resp = send_url(TOKEN, CHAT_ID, url)

print('Response:', resp)
if not ok:
    sys.exit(5)
