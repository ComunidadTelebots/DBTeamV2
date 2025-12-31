"""Minimal port of bot/web_api.lua functionality for session handling.
This module provides helpers to verify Telegram Login Widget payloads and
create web sessions stored in Redis. It's NOT a full HTTP server; use
`python_api` FastAPI app for full endpoints and import these helpers there.
"""
import os
import json
import hashlib
import hmac
import time
import redis

REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
REDIS = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def verify_telegram_login(payload: dict) -> bool:
    """Verify Telegram Login Widget payload using BOT_TOKEN.
    Returns True if signature valid.
    """
    if not BOT_TOKEN:
        return False
    data = {k: v for k, v in payload.items() if k != 'hash'}
    # Telegram requires sorting keys and joining k=value with \n
    keys = sorted(data.keys())
    data_check = '\n'.join(['%s=%s' % (k, data[k]) for k in keys])
    secret = hashlib.sha256(BOT_TOKEN.encode('utf-8')).digest()
    digest = hmac.new(secret, data_check.encode('utf-8'), hashlib.sha256).hexdigest()
    return digest == payload.get('hash')


def create_web_session(payload: dict, ttl: int = 3600) -> dict:
    token = hashlib.sha256((str(time.time()) + json.dumps(payload)).encode('utf-8')).hexdigest()
    sess_raw = json.dumps({ 'id': payload.get('id'), 'first_name': payload.get('first_name'), 'username': payload.get('username') })
    REDIS.setex(f'web:session:{token}', ttl, sess_raw)
    return { 'token': token, 'ttl': ttl }
