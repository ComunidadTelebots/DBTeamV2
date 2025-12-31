"""Port of bot/methods.lua minimal helpers for Python.
These helpers enqueue outgoing messages to Redis so the existing
`python_api` worker or userbot can deliver them. They are intentionally
lightweight to ease iterative migration from Lua.
"""
import json
import os
from typing import Optional

try:
    import redis
except Exception:
    redis = None

REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')

def _get_redis():
    if not redis:
        raise RuntimeError('redis library not available')
    return redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)

def send_msg(chat_id: int, text: str, parse: Optional[str] = None):
    """Enqueue a simple text message to the web outbox.
    This mirrors the Lua `send_msg` but uses Redis list `web:outbox`.
    """
    r = _get_redis()
    payload = { 'chat_id': int(chat_id), 'text': text }
    if parse:
        payload['parse'] = parse
    r.rpush('web:outbox', json.dumps(payload))

def reply_msg(chat_id: int, text: str, msg_id: int, parse: Optional[str] = None):
    payload = { 'chat_id': int(chat_id), 'text': text, 'reply_to_message_id': int(msg_id) }
    if parse:
        payload['parse'] = parse
    r = _get_redis()
    r.rpush('web:outbox', json.dumps(payload))

def send_document(chat_id: int, document: str, caption: Optional[str] = None):
    payload = { 'chat_id': int(chat_id), 'type': 'document', 'document': document }
    if caption:
        payload['caption'] = caption
    r = _get_redis()
    r.rpush('web:outbox', json.dumps(payload))

def forward_msg(chat_id: int, from_chat_id: int, message_id: int):
    payload = { 'chat_id': int(chat_id), 'forward_from_chat_id': int(from_chat_id), 'forward_message_id': int(message_id) }
    r = _get_redis()
    r.rpush('web:outbox', json.dumps(payload))

def send_to_api_send(chat_id: int, text: str):
    """Compatibility helper that pushes to `web:outbox` as well.
    External send via Bot API is handled by `python_api` processes.
    """
    send_msg(chat_id, text)
