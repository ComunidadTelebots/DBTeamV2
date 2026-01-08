"""Executor that consumes `moderation:applied` and performs actions via Telegram Bot API.

Run this as a separate process. It expects `BOT_TOKEN` env var and optional
`REDIS_URL`. It supports actions: `ban`, `mute`, `warn`, `ignore`.
"""
import os
import time
import json
import requests
try:
    import redis
except Exception:
    redis = None

BOT_TOKEN = os.environ.get('BOT_TOKEN')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')

if not BOT_TOKEN:
    print('BOT_TOKEN not set. Exiting.')
    raise SystemExit(1)

if redis is None:
    print('redis library not available. Exiting.')
    raise SystemExit(1)

_r = redis.from_url(REDIS_URL, decode_responses=True)
BASE = f'https://api.telegram.org/bot{BOT_TOKEN}'


def ban_chat_member(chat_id, user_id):
    url = BASE + '/banChatMember'
    resp = requests.post(url, json={'chat_id': int(chat_id), 'user_id': int(user_id)})
    return resp.ok, resp.text


def restrict_chat_member(chat_id, user_id):
    url = BASE + '/restrictChatMember'
    permissions = {
        'can_send_messages': False,
        'can_send_media_messages': False,
        'can_send_polls': False,
        'can_send_other_messages': False,
        'can_add_web_page_previews': False,
    }
    resp = requests.post(url, json={'chat_id': int(chat_id), 'user_id': int(user_id), 'permissions': permissions})
    return resp.ok, resp.text


def process_item(raw):
    try:
        j = raw if isinstance(raw, dict) else json.loads(raw)
    except Exception:
        print('Invalid item:', raw)
        return
    action = j.get('action') or j.get('applied', {}).get('action') or j.get('action')
    # support older format where top level has 'action'
    action = action or j.get('action')
    if not action:
        # older format: original suggestion contains 'action'
        action = j.get('action') or j.get('original', {}).get('action') or j.get('action')

    # fallback: if original.suggestion present
    if not action and j.get('original') and isinstance(j.get('original'), dict):
        action = j['original'].get('suggestion')

    group = j.get('original', {}).get('group_id') or j.get('group_id') or j.get('original', {}).get('group')
    user = j.get('original', {}).get('user_id') or j.get('user_id') or j.get('original', {}).get('user')
    if not group or not user:
        print('Missing group/user in', j)
        return

    if action == 'ban':
        ok, txt = ban_chat_member(group, user)
        print('ban', group, user, ok, txt)
    elif action == 'mute':
        ok, txt = restrict_chat_member(group, user)
        print('mute', group, user, ok, txt)
    elif action == 'warn':
        print('warn logged for', user, 'in', group)
    elif action == 'ignore':
        print('ignored', user)
    else:
        print('unknown action', action)


def run_loop(poll_interval=2.0):
    print('moderation_executor started, polling moderation:applied')
    while True:
        item = _r.lpop('moderation:applied')
        if not item:
            time.sleep(poll_interval)
            continue
        try:
            process_item(item)
        except Exception as e:
            print('processing error:', e)


if __name__ == '__main__':
    run_loop()
