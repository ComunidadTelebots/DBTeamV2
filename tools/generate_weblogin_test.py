#!/usr/bin/env python3
import sys, time, secrets, json
sys.path.insert(0, 'projects/bot')
from python_bot.storage import storage

code = secrets.token_urlsafe(6)
key = f'weblogin:{code}'
payload = {'user':'@andrea7221', 'created': int(time.time())}
try:
    storage.set(key, payload)
    stored = storage.get(key)
except Exception as e:
    print('ERROR:', e)
    sys.exit(2)
print(json.dumps({'ok': True, 'code': code, 'key': key, 'stored': stored}, ensure_ascii=False))
