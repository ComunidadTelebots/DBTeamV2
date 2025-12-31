"""Port of bot/web_api.lua HTTP helpers (subset) to Python.

This module exposes helpers for Telegram login verification and sending
messages via Bot API using `requests`.
"""
import os
import json
import hashlib
import hmac
import requests
from python_bot import web_api as pyweb

BOT_TOKEN = os.getenv('BOT_TOKEN', '')

def verify_telegram_login(payload: dict) -> bool:
    return pyweb.verify_telegram_login(payload)

def create_web_session(payload: dict, ttl: int = 3600) -> dict:
    return pyweb.create_web_session(payload, ttl)

def send_via_bot_api(chat_id, text, device_token=None):
    token = device_token or BOT_TOKEN
    if not token:
        raise RuntimeError('no BOT_TOKEN')
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    body = { 'chat_id': chat_id, 'text': text }
    resp = requests.post(url, json=body)
    resp.raise_for_status()
    return resp.json()
