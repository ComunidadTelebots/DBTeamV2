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
