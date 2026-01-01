#!/usr/bin/env python3
import os, sys, requests
# read .env explicitly and ignore BOM issues
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
config = {}
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '=' not in line:
                continue
            k,v = line.strip().split('=',1)
            k = k.lstrip('\ufeff')
            config[k] = v
print('CONFIG_KEYS:', list(config.keys()))
print('BOT_TOKEN_IN_CONFIG:', 'BOT_TOKEN' in config)
TOKEN = config.get('BOT_TOKEN') or os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print('ERROR: BOT_TOKEN not found in .env or environment')
    sys.exit(2)
CHAT_ID = config.get('TARGET_USER_ID') or os.getenv('TARGET_USER_ID') or '163103382'
file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'projects', 'bot', 'tmp_downloaded.torrent')
if not os.path.exists(file_path):
    print('ERROR: torrent file not found at', file_path)
    sys.exit(3)
url = f'https://api.telegram.org/bot{TOKEN}/sendDocument'
with open(file_path, 'rb') as fh:
    r = requests.post(url, data={'chat_id': CHAT_ID}, files={'document': fh}, timeout=20)
    try:
        jr = r.json()
    except Exception:
        print('HTTP', r.status_code, r.text)
        sys.exit(4)
    print('Response:', jr)
    if not jr.get('ok'):
        sys.exit(5)
