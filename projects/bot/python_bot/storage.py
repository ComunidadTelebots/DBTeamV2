"""Simple storage wrapper using Redis with in-memory fallback.

Provides basic chat/user persistence used by core commands.
"""
import os
import json
import time
from typing import List, Dict, Any, Optional

try:
    import redis
except Exception:
    redis = None


class InMemoryStore:
    def __init__(self):
        self.data = {}

    def sadd(self, key, value):
        self.data.setdefault(key, set()).add(value)

    def smembers(self, key):
        return set(self.data.get(key, set()))

    def set(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)

    def delete(self, key):
        if key in self.data:
            del self.data[key]


class Storage:
    def __init__(self):
        self.prefix = 'dbteam:'
        self.redis = None
        self.fallback = InMemoryStore()
        if redis is not None:
            try:
                self.redis = redis.Redis(host=os.getenv('REDIS_HOST','localhost'), port=int(os.getenv('REDIS_PORT','6379')), db=0, decode_responses=True)
                self.redis.ping()
            except Exception:
                self.redis = None

    def _skey(self, key: str) -> str:
        return f'{self.prefix}{key}'

    # Generic key/value helpers (used by web login/session code)
    def set(self, key: str, value):
        k = self._skey(key)
        if self.redis:
            # store raw value as string
            self.redis.set(k, json.dumps(value) if not isinstance(value, str) else value)
        else:
            self.fallback.set(k, json.dumps(value) if not isinstance(value, str) else value)

    def get(self, key: str):
        k = self._skey(key)
        if self.redis:
            val = self.redis.get(k)
            return val
        else:
            return self.fallback.get(k)

    def add_chat(self, chat_id: int):
        k = self._skey('chats')
        if self.redis:
            self.redis.sadd(k, chat_id)
        else:
            self.fallback.sadd(k, chat_id)

    def list_chats(self) -> List[int]:
        k = self._skey('chats')
        if self.redis:
            return [int(x) for x in self.redis.smembers(k) or []]
        else:
            return [int(x) for x in (self.fallback.smembers(k) or [])]

    def set_lang(self, chat_id: int, code: str):
        k = self._skey(f'lang:{chat_id}')
        if self.redis:
            self.redis.set(k, code)
        else:
            self.fallback.set(k, code)

    def get_lang(self, chat_id: int) -> Optional[str]:
        k = self._skey(f'lang:{chat_id}')
        if self.redis:
            return self.redis.get(k)
        else:
            return self.fallback.get(k)

    def ban_chat(self, chat_id: int):
        k = self._skey('banned')
        if self.redis:
            self.redis.sadd(k, chat_id)
        else:
            self.fallback.sadd(k, chat_id)

    def unban_chat(self, chat_id: int):
        k = self._skey('banned')
        if self.redis:
            self.redis.srem(k, chat_id)
        else:
            s = self.fallback.smembers(k)
            if chat_id in s:
                s.remove(chat_id)

    def is_banned(self, chat_id: int) -> bool:
        k = self._skey('banned')
        if self.redis:
            return self.redis.sismember(k, chat_id)
        else:
            return chat_id in (self.fallback.smembers(k) or set())

    def set_role(self, user_id: int, role: str):
        k = self._skey(f'role:{user_id}')
        if self.redis:
            self.redis.set(k, role)
        else:
            self.fallback.set(k, role)

    def get_role(self, user_id: int) -> Optional[str]:
        k = self._skey(f'role:{user_id}')
        if self.redis:
            return self.redis.get(k)
        else:
            return self.fallback.get(k)

    def rate_limit_check(self, chat_id: int, cmd: str, cooldown: int) -> bool:
        k = self._skey(f'rl:{chat_id}:{cmd}')
        now = int(time.time())
        if self.redis:
            last = self.redis.get(k)
            if last and now - int(last) < cooldown:
                return False
            self.redis.set(k, now)
            return True
        else:
            last = self.fallback.get(k)
            if last and now - int(last) < cooldown:
                return False
            self.fallback.set(k, now)
            return True

    def dump_settings(self) -> Dict[str, Any]:
        # Export limited settings (chats, banned, roles, langs)
        return {
            'chats': self.list_chats(),
            'banned': list(self.redis.smembers(self._skey('banned'))) if self.redis else list(self.fallback.smembers(self._skey('banned')) or []),
        }

    def export_json(self) -> str:
        return json.dumps(self.dump_settings(), ensure_ascii=False)
    # Forwarding tracking helpers
    def record_forward(self, file_hash: str, chat_id: int):
        k = self._skey(f'forwarded:{file_hash}')
        if self.redis:
            self.redis.sadd(k, chat_id)
        else:
            self.fallback.sadd(k, chat_id)

    def has_been_forwarded(self, file_hash: str, chat_id: int) -> bool:
        k = self._skey(f'forwarded:{file_hash}')
        if self.redis:
            return self.redis.sismember(k, chat_id)
        else:
            return chat_id in (self.fallback.smembers(k) or set())

    def get_forwarded_chats(self, file_hash: str):
        k = self._skey(f'forwarded:{file_hash}')
        if self.redis:
            return [int(x) for x in self.redis.smembers(k) or []]
        else:
            return [int(x) for x in (self.fallback.smembers(k) or [])]
    # Known torrent infohashes
    def add_infohash(self, infohash: str):
        k = self._skey('infohashes')
        if self.redis:
            self.redis.sadd(k, infohash)
        else:
            self.fallback.sadd(k, infohash)

    def has_infohash(self, infohash: str) -> bool:
        k = self._skey('infohashes')
        if self.redis:
            return self.redis.sismember(k, infohash)
        else:
            return infohash in (self.fallback.smembers(k) or set())

    def list_infohashes(self):
        k = self._skey('infohashes')
        if self.redis:
            return [x for x in (self.redis.smembers(k) or [])]
        else:
            return [x for x in (self.fallback.smembers(k) or set())]
    # Pending torrents per-user (used when users send .torrent/magnets in private)
    def add_pending_torrent(self, user_id: int, obj: dict):
        k = self._skey(f'pending:{user_id}')
        # store as JSON list in a single key for simplicity
        if self.redis:
            raw = self.redis.get(k) or '[]'
            try:
                arr = json.loads(raw)
            except Exception:
                arr = []
            arr.append(obj)
            self.redis.set(k, json.dumps(arr))
        else:
            raw = self.fallback.get(k) or '[]'
            try:
                arr = json.loads(raw)
            except Exception:
                arr = []
            arr.append(obj)
            self.fallback.set(k, json.dumps(arr))

    def get_pending_torrents(self, user_id: int):
        k = self._skey(f'pending:{user_id}')
        if self.redis:
            raw = self.redis.get(k)
        else:
            raw = self.fallback.get(k)
        if not raw:
            return []
        try:
            return json.loads(raw)
        except Exception:
            return []

    def remove_pending_torrent(self, user_id: int, index: int):
        k = self._skey(f'pending:{user_id}')
        lst = self.get_pending_torrents(user_id)
        try:
            idx = int(index)
            if idx < 0 or idx >= len(lst):
                return False
            lst.pop(idx)
            if self.redis:
                self.redis.set(k, json.dumps(lst))
            else:
                self.fallback.set(k, json.dumps(lst))
            return True
        except Exception:
            return False
    # Allowed senders per chat (who can trigger the bot to post to origin chats)
    def add_allowed_sender(self, chat_id: int, user_id: int):
        k = self._skey(f'allowed_senders:{chat_id}')
        if self.redis:
            self.redis.sadd(k, user_id)
        else:
            self.fallback.sadd(k, str(user_id))

    def remove_allowed_sender(self, chat_id: int, user_id: int):
        k = self._skey(f'allowed_senders:{chat_id}')
        if self.redis:
            self.redis.srem(k, user_id)
        else:
            s = self.fallback.smembers(k)
            if str(user_id) in s:
                s.remove(str(user_id))

    def is_allowed_sender(self, chat_id: int, user_id: int) -> bool:
        k = self._skey(f'allowed_senders:{chat_id}')
        if self.redis:
            return self.redis.sismember(k, user_id)
        else:
            return str(user_id) in (self.fallback.smembers(k) or set())

    def list_allowed_senders(self, chat_id: int):
        k = self._skey(f'allowed_senders:{chat_id}')
        if self.redis:
            return [int(x) for x in (self.redis.smembers(k) or [])]
        else:
            return [int(x) for x in (self.fallback.smembers(k) or set())]
    # Streaming session helpers (per-chat)
    def start_stream_session(self, chat_id: int, name: Optional[str] = None):
        k = self._skey(f'session:{chat_id}')
        payload = {'active': '1', 'name': name or '', 'started_at': str(int(time.time())), 'abort': '0'}
        if self.redis:
            self.redis.hset(k, mapping=payload)
        else:
            self.fallback.set(k, payload)

    # counters for active uploaders/downloaders per session
    def inc_stream_downloaders(self, chat_id: int):
        k = self._skey(f'session_counters:{chat_id}')
        if self.redis:
            self.redis.hincrby(k, 'downloaders', 1)
        else:
            s = self.fallback.get(k) or {}
            s['downloaders'] = int(s.get('downloaders', 0)) + 1
            self.fallback.set(k, s)

    def dec_stream_downloaders(self, chat_id: int):
        k = self._skey(f'session_counters:{chat_id}')
        if self.redis:
            self.redis.hincrby(k, 'downloaders', -1)
        else:
            s = self.fallback.get(k) or {}
            s['downloaders'] = max(0, int(s.get('downloaders', 0)) - 1)
            self.fallback.set(k, s)

    def inc_stream_uploaders(self, chat_id: int):
        k = self._skey(f'session_counters:{chat_id}')
        if self.redis:
            self.redis.hincrby(k, 'uploaders', 1)
        else:
            s = self.fallback.get(k) or {}
            s['uploaders'] = int(s.get('uploaders', 0)) + 1
            self.fallback.set(k, s)

    def dec_stream_uploaders(self, chat_id: int):
        k = self._skey(f'session_counters:{chat_id}')
        if self.redis:
            self.redis.hincrby(k, 'uploaders', -1)
        else:
            s = self.fallback.get(k) or {}
            s['uploaders'] = max(0, int(s.get('uploaders', 0)) - 1)
            self.fallback.set(k, s)

    def get_stream_counters(self, chat_id: int):
        k = self._skey(f'session_counters:{chat_id}')
        if self.redis:
            data = self.redis.hgetall(k) or {}
            return {'downloaders': int(data.get('downloaders', 0)), 'uploaders': int(data.get('uploaders', 0))}
        else:
            s = self.fallback.get(k) or {}
            return {'downloaders': int(s.get('downloaders', 0)), 'uploaders': int(s.get('uploaders', 0))}

    def stop_stream_session(self, chat_id: int):
        k = self._skey(f'session:{chat_id}')
        if self.redis:
            self.redis.delete(k)
        else:
            self.fallback.delete(k)

    def abort_stream_session(self, chat_id: int):
        k = self._skey(f'session:{chat_id}')
        if self.redis:
            self.redis.hset(k, 'abort', '1')
        else:
            s = self.fallback.get(k) or {}
            s['abort'] = '1'
            self.fallback.set(k, s)

    def get_stream_session(self, chat_id: int) -> Optional[Dict[str, str]]:
        k = self._skey(f'session:{chat_id}')
        if self.redis:
            if not self.redis.exists(k):
                return None
            return {k: v for k, v in self.redis.hgetall(k).items()}
        else:
            return self.fallback.get(k)

    def is_stream_active(self, chat_id: int) -> bool:
        sess = self.get_stream_session(chat_id)
        return bool(sess and sess.get('active') == '1')


storage = Storage()
