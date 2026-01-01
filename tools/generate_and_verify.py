#!/usr/bin/env python3
import sys, time, secrets, json, requests
sys.path.insert(0, 'projects/bot')
from python_bot.storage import storage

code = secrets.token_urlsafe(6)
key = f'weblogin:{code}'
payload = {'user':'@andrea7221', 'created': int(time.time())}
storage.set(key, payload)
print('generated', code)
# now call verify
try:
    r = requests.post('http://127.0.0.1:8082/login/verify', json={'code': code}, timeout=10)
    print('verify', r.status_code, r.text)
    if r.status_code == 200:
        session = r.json().get('session')
        print('session', session)
        # call control restart
        headers = {'Authorization': f'Bearer {session}'}
        rc = requests.post('http://127.0.0.1:8081/control', json={'action':'restart'}, headers=headers, timeout=30)
        print('control', rc.status_code, rc.text)
    else:
        print('verify failed')
except Exception as e:
    print('ERROR', e)
    sys.exit(2)
