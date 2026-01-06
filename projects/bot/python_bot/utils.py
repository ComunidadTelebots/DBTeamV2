"""Utility helpers ported from bot/utils.lua (minimal subset).
"""
import json
import os
import re
from typing import Any, Dict, List, Optional

try:
    import redis
except Exception:
    redis = None

REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')

def _get_redis():
    if not redis:
        raise RuntimeError('redis library not available')
    return redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)

def match_pattern(pattern: str, text: Optional[str], lower_case: bool = False):
    if not text:
        return None
    if lower_case:
        text = text.lower()
    m = re.search(pattern, text)
    if not m:
        return None
    return list(m.groups()) if m.groups() else [m.group(0)]

def get_receiver(msg: Dict[str, Any]) -> Optional[int]:
    return msg.get('to', {}).get('id')

def getChatId(chat_id: Any) -> Dict[str, Any]:
    s = str(chat_id)
    if s.startswith('-100'):
        return { 'ID': s.replace('-100','',1), 'type': 'channel' }
    else:
        return { 'ID': s.lstrip('-'), 'type': 'group' }

def serialize_to_file(data: Any, path: str):
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

def lang_text(chat_id: int, keyword: str) -> str:
    r = _get_redis()
    lang = r.get(f'langset:{chat_id}') or 'en'
    text = r.get(f'lang:{lang}:{keyword}')
    if text:
        return text
    return f'Language text "{keyword}" not installed for {lang}'

def is_number(name_id: str) -> bool:
    try:
        int(name_id)
        return True
    except Exception:
        return False

def no_markdown(text: Optional[str], replace: Optional[str] = None) -> Optional[str]:
    if text is None:
        return None
    if replace is None:
        return re.sub(r'[`*_]', '', str(text))
    else:
        return re.sub(r'[`*_]', replace, str(text))


def send_telegram_message(chat_id_or_username: str, text: str, token: Optional[str] = None, timeout: int = 5):
    """Send a message using the Bot API. `chat_id_or_username` may be numeric id or @username.

    Returns the parsed JSON response on success or raises an exception on failure.
    """
    try:
        import requests
    except Exception:
        raise RuntimeError('requests library is required to send Telegram messages')
    token = token or os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise RuntimeError('BOT_TOKEN not configured in environment')
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {'chat_id': chat_id_or_username, 'text': text, 'disable_web_page_preview': True}
    r = requests.post(url, json=payload, timeout=timeout)
    try:
        return r.json()
    except Exception:
        r.raise_for_status()


def compute_file_sha256(path: str) -> str:
    """Compute SHA256 hex digest for a local file. Raises on I/O errors."""
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def verify_local_with_checksums_api(name: str, local_hash: str = None, timeout: int = 5):
    """Query the checksums API for `name` and compare expected hash with `local_hash`.
    Returns: True=match, False=mismatch, None=no entry or API unavailable.
    """
    import os
    try:
        import requests
    except Exception:
        return None
    checks_url = os.getenv('CHECKSUMS_URL', os.getenv('AI_URL', 'http://127.0.0.1:8081'))
    try:
        r = requests.get(f'{checks_url}/checksums/list', timeout=timeout)
        if not r.ok:
            return None
        data = r.json()
        entries = {e['name']: e['sha256'] for e in data.get('entries', [])}
        expected = entries.get(name)
        if not expected:
            return None
        if local_hash is None:
            # cannot compute local here; caller should provide
            return None
        return expected == local_hash
    except Exception:
        return None
