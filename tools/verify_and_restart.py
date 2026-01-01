#!/usr/bin/env python3
import requests, json, sys
code = 'BTztDant'
try:
    r = requests.post('http://127.0.0.1:8082/login/verify', json={'code': code}, timeout=10)
    print('verify status', r.status_code, r.text)
    rj = r.json()
    session = rj.get('session')
    if not session:
        print('No session returned; exiting')
        sys.exit(1)
    headers = {'Authorization': f'Bearer {session}'}
    rc = requests.post('http://127.0.0.1:8081/control', json={'action':'restart'}, headers=headers, timeout=30)
    print('control status', rc.status_code, rc.text)
except Exception as e:
    print('ERROR', e)
    sys.exit(2)
