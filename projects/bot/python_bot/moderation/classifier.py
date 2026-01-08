"""Simple behaviour classifier for moderation.

This is a lightweight, rule-based classifier that scores messages and
records infractions in Redis. It exposes `classify_message` which returns
a dict with `score`, `reasons`, and a `suggestion` for admin action.

The design is intentionally simple: rules produce points, points are
accumulated per-user in Redis over a short window and mapped to actions.
"""
from typing import Dict, Any, List
import os
import time
import json
import re
import redis

REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
_r = redis.from_url(REDIS_URL, decode_responses=True)

LINK_RE = re.compile(r'https?://|t\.me/|telegram\.me/|discord\.gg/|joinchat', re.I)
MENTION_RE = re.compile(r'@[A-Za-z0-9_]{5,}', re.I)
PHONE_RE = re.compile(r'\+?\d{7,}', re.I)

# Scoring weights
WEIGHTS = {
    'link': 40,
    'many_mentions': 25,
    'phone': 15,
    'caps': 10,
    'blacklist_word': 30,
    'repeated': 20,
    'attachment': 20,
}

BLACKLIST = [
    'buy followers', 'free bitcoin', 'visit my channel', 'earn money',
]

# Thresholds for actions (total accumulated points)
ACTION_THRESHOLDS = {
    'warn': 30,
    'mute': 70,
    'ban': 120,
}


def _load_overrides():
    """Load optional overrides for weights and thresholds from Redis keys.

    Keys (JSON): `mod:weights` and `mod:thresholds`.
    """
    try:
        w_raw = _r.get('mod:weights')
        t_raw = _r.get('mod:thresholds')
        w = json.loads(w_raw) if w_raw else {}
        t = json.loads(t_raw) if t_raw else {}
        merged_w = WEIGHTS.copy()
        merged_w.update({k: int(v) for k, v in w.items()})
        merged_t = ACTION_THRESHOLDS.copy()
        merged_t.update({k: int(v) for k, v in t.items()})
        return merged_w, merged_t
    except Exception:
        return WEIGHTS, ACTION_THRESHOLDS


def _now():
    return int(time.time())


def _add_user_points(group_id: int, user_id: int, points: int, window: int = 3600) -> int:
    """Add points for a user and return the new total for the sliding window."""
    key = f'mod:points:{group_id}:{user_id}'
    pipe = _r.pipeline()
    # store as JSON list of [ts,points]
    existing = _r.get(key)
    entries: List[List[int]] = json.loads(existing) if existing else []
    now = _now()
    entries = [e for e in entries if now - e[0] < window]
    entries.append([now, points])
    pipe.set(key, json.dumps(entries), ex=window + 10)
    pipe.execute()
    total = sum(e[1] for e in entries)
    return total


def classify_message(group_id: int, user: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
    """Score a message and return classification info.

    `user` is expected to have `id` and optional fields. `message` is a
    dict with keys like `text`, `media_type`.
    """
    score = 0
    reasons: List[str] = []
    text = (message.get('text') or '')

    # Links
    if LINK_RE.search(text) or message.get('media_type') in ('web_page', 'document'):
        score += WEIGHTS['link']
        reasons.append('contains_link')

    # Many mentions
    mentions = len(MENTION_RE.findall(text))
    if mentions >= 3:
        score += WEIGHTS['many_mentions']
        reasons.append(f'many_mentions:{mentions}')

    # Phone numbers or long digit sequences (possible spam)
    if PHONE_RE.search(text):
        score += WEIGHTS['phone']
        reasons.append('phone_or_digits')

    # Caps ratio
    letters = [c for c in text if c.isalpha()]
    if letters:
        caps = sum(1 for c in letters if c.isupper())
        ratio = caps / len(letters)
        if ratio > 0.7 and len(letters) > 6:
            score += WEIGHTS['caps']
            reasons.append('high_caps')

    # Blacklist words
    lower = text.lower()
    for w in BLACKLIST:
        if w in lower:
            score += WEIGHTS['blacklist_word']
            reasons.append(f'blacklist:{w}')

    # Repeated message detection (basic): compare with last message stored
    last_key = f'mod:lastmsg:{group_id}:{user.get("id")}'
    last = _r.get(last_key)
    if last and last == text and text.strip():
        score += WEIGHTS['repeated']
        reasons.append('repeated_message')
    # store last message
    if text.strip():
        _r.set(last_key, text, ex=3600)

    # Attachments
    if message.get('media_type') in ('photo', 'video', 'sticker'):
        score += WEIGHTS['attachment']
        reasons.append('has_attachment')

    # Persist incremental points and compute aggregate
    total = _add_user_points(group_id, int(user.get('id', 0)), score)

    # Decide suggestion
    suggestion = None
    if total >= ACTION_THRESHOLDS['ban']:
        suggestion = 'ban'
    elif total >= ACTION_THRESHOLDS['mute']:
        suggestion = 'mute'
    elif total >= ACTION_THRESHOLDS['warn']:
        suggestion = 'warn'

    return {
        'score': score,
        'total': total,
        'reasons': reasons,
        'suggestion': suggestion,
    }


def push_action_suggestion(group_id: int, user_id: int, suggestion: str, info: Dict[str, Any]):
    """Push a suggestion to a Redis queue for admin review."""
    payload = {
        'group_id': int(group_id),
        'user_id': int(user_id),
        'suggestion': suggestion,
        'info': info,
        'ts': _now(),
    }
    _r.rpush('moderation:actions', json.dumps(payload))
    # Also push a lightweight web notification for the UI
    try:
        note = {
            'title': f"Moderation: {suggestion}",
            'text': f"User {user_id} in group {group_id}: {', '.join(info.get('reasons', []))}",
            'group_id': int(group_id),
            'user_id': int(user_id),
            'suggestion': suggestion,
            'ts': payload['ts'],
        }
        _r.rpush('web:notifications', json.dumps(note))
        # keep notifications list bounded
        _r.ltrim('web:notifications', -200, -1)
    except Exception:
        pass
