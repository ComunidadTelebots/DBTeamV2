#!/usr/bin/env python3
"""E2E test script for python_api.

Requires the API running at http://localhost:8081 and Redis available.
This script will:
- craft a Telegram login payload signed with BOT_TOKEN
- call POST /auth to get a session token
- call POST /devices/add to add a device
- call GET /devices to list devices
- call POST /send_user to enqueue a message

Set environment variables: BOT_TOKEN and API_BASE (default http://localhost:8081)
"""
import os
import time
import json
import hashlib
import hmac
import requests

API_BASE = os.getenv('API_BASE', 'http://localhost:8081')
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print('Set BOT_TOKEN environment variable before running')
    raise SystemExit(1)

def make_auth_payload(user_id=123456, first_name='Test', username='tester'):
    payload = {
        'id': user_id,
        'first_name': first_name,
        'username': username,
        'auth_date': int(time.time())
    }
    parts = sorted([k for k in payload.keys()])
    data_check = '\n'.join([f"{k}={payload[k]}" for k in parts])
    key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    sig = hmac.new(key, data_check.encode(), hashlib.sha256).hexdigest()
    payload['hash'] = sig
    return payload

def post_auth():
    payload = make_auth_payload()
    url = API_BASE.rstrip('/') + '/auth'
    r = requests.post(url, json=payload)
    print('auth ->', r.status_code, r.text)
    r.raise_for_status()
    return r.json().get('token')

def add_device(token, device_id='bot-e2e', device_name='E2E Bot', device_token='123:ABC'):
    url = API_BASE.rstrip('/') + '/devices/add'
    headers = {'Authorization': 'Bearer ' + token}
    payload = {'id': device_id, 'name': device_name, 'token': device_token}
    r = requests.post(url, json=payload, headers=headers)
    print('devices/add ->', r.status_code, r.text)
    r.raise_for_status()

def list_devices(token):
    url = API_BASE.rstrip('/') + '/devices'
    headers = {'Authorization': 'Bearer ' + token}
    r = requests.get(url, headers=headers)
    print('devices ->', r.status_code, r.text)
    r.raise_for_status()
    return r.json()

def send_user(token, chat_id='123456789', text='E2E test message'):
    url = API_BASE.rstrip('/') + '/send_user'
    headers = {'Authorization': 'Bearer ' + token}
    payload = {'chat_id': chat_id, 'text': text}
    r = requests.post(url, json=payload, headers=headers)
    print('send_user ->', r.status_code, r.text)
    r.raise_for_status()

def main():
    print('Starting E2E test against', API_BASE)
    token = post_auth()
    print('Received session token:', token)
    add_device(token)
    devs = list_devices(token)
    print('Devices listed:', devs)
    send_user(token)
    print('Enqueued send_user; check bot logs for processing')

if __name__ == '__main__':
    main()
