#!/usr/bin/env python3
import os, sys, requests
TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    # try to read from .env in repo root (don't print secrets)
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.abspath(os.path.join(here, '..'))
        env_path = os.path.join(repo_root, '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as ef:
                for line in ef:
                    if line.strip().startswith('BOT_TOKEN='):
                        TOKEN = line.strip().split('=',1)[1]
                        break
    except Exception:
        TOKEN = None
    if not TOKEN:
        print('ERROR: BOT_TOKEN not set in environment or .env')
        sys.exit(2)
CHAT_ID = os.getenv('TARGET_USER_ID') or '163103382'
file_path = os.path.join('projects','bot','tmp_downloaded.torrent')
if not os.path.exists(file_path):
    print('ERROR: torrent file not found at', file_path)
    sys.exit(3)
url = f'https://api.telegram.org/bot{TOKEN}/sendDocument'
with open(file_path, 'rb') as fh:
    files = {'document': fh}
    data = {'chat_id': CHAT_ID}
    r = requests.post(url, data=data, files=files, timeout=20)
    try:
        jr = r.json()
    except Exception:
        print('HTTP', r.status_code, r.text)
        sys.exit(4)
    print('Response:', jr)
    if not jr.get('ok'):
        sys.exit(5)
