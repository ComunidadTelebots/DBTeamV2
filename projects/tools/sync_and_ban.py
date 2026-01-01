#!/usr/bin/env python3
"""One-off utility: fetch blocked IDs from web API and ban them in a Telegram chat.

Usage examples:
  set BOT_TOKEN and API_BASE env vars, then:
    python projects/tools/sync_and_ban.py @tsalltech

This script will:
  - resolve chat id for provided username (if necessary)
  - GET `{API_BASE}/bot/data` and look for `blocked_ids` or `blocked`
  - call Telegram `banChatMember` for each id

WARNING: the bot token must have admin privileges in the target chat.
"""
import os
import sys
import time
import argparse
import requests


def get_env(name, default=None):
    return os.getenv(name, default)


def resolve_chat_id(token, identifier):
    # identifier can be numeric id or @username
    if str(identifier).lstrip('-').isdigit():
        return int(identifier)
    url = f'https://api.telegram.org/bot{token}/getChat'
    try:
        r = requests.get(url, params={'chat_id': identifier}, timeout=10)
        r.raise_for_status()
        j = r.json()
        if j.get('ok') and 'result' in j:
            return j['result'].get('id')
    except Exception as e:
        print('getChat failed:', e)
    return None


def fetch_blocked_from_api(api_base):
    """Try to fetch blocked IDs from a web API.

    Handles JSON responses (keys: blocked_ids, blocked) or plain text lists of numeric ids.
    """
    url = api_base.rstrip('/')
    tried = []
    # prefer /bot/data path when contacting a local API
    candidates = [url, url + '/bot/data', url + '/blocked', url + '/blocklist']
    for c in candidates:
        if c in tried:
            continue
        tried.append(c)
        try:
            r = requests.get(c, timeout=10)
            r.raise_for_status()
            # try JSON
            try:
                j = r.json()
                blocked = j.get('blocked_ids') or j.get('blocked') or j.get('data') or j.get('ids')
                if isinstance(blocked, list) and blocked:
                    return [int(x) for x in blocked if str(x).lstrip('-').isdigit()]
            except Exception:
                # fallback to text parsing
                text = r.text or ''
                ids = [int(x) for x in re.findall(r"\b\d{5,}\b", text)]
                if ids:
                    return ids
        except Exception:
            continue
    print('Error: no blocked IDs found at', api_base)
    return []


def ban_user(token, chat_id, user_id):
    url = f'https://api.telegram.org/bot{token}/banChatMember'
    try:
        r = requests.post(url, data={'chat_id': chat_id, 'user_id': user_id}, timeout=10)
        r.raise_for_status()
        j = r.json()
        return j.get('ok', False), j
    except Exception as e:
        return False, {'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description='Sync blocked IDs from API and ban them in a Telegram chat')
    parser.add_argument('chat', help='chat identifier (username like @foo or numeric id)')
    parser.add_argument('--api', help='API base URL (overrides API_BASE env)', default=None)
    parser.add_argument('--cas', help='Use https://cas.chat/api as source', action='store_true')
    args = parser.parse_args()

    token = get_env('BOT_TOKEN')
    if not token:
        print('Set BOT_TOKEN environment variable with your bot token')
        sys.exit(1)

    target = args.chat
    print('Resolving chat id for', target)
    chat_id = resolve_chat_id(token, target)
    if not chat_id:
        print('Failed to resolve chat id for', target)
        sys.exit(1)
    print('Chat id:', chat_id)

    api_base = None
    if args.api:
        api_base = args.api
    elif args.cas:
        api_base = 'https://cas.chat/api'
    else:
        api_base = get_env('API_BASE', None)

    blocked = []
    if api_base:
        print('Fetching blocked IDs from API:', api_base)
        blocked = fetch_blocked_from_api(api_base)
    else:
        print('No API base provided; exiting')
        sys.exit(1)

    print('Found', len(blocked), 'IDs')
    if not blocked:
        print('No IDs to ban; exiting')
        sys.exit(0)

    ok = 0
    fail = 0
    for uid in blocked:
        print('Banning', uid)
        success, resp = ban_user(token, chat_id, uid)
        if success:
            ok += 1
        else:
            fail += 1
            print('Failed banning', uid, resp)
        time.sleep(0.4)

    print('Done. success:', ok, 'failed:', fail)


if __name__ == '__main__':
    main()
