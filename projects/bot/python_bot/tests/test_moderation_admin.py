import sys
import os
import unittest
import json

# Ensure package import path (add projects/bot so `python_bot` package is importable)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PKG_ROOT = os.path.abspath(os.path.join(ROOT, '..'))
if PKG_ROOT not in sys.path:
    sys.path.insert(0, PKG_ROOT)

# Provide a minimal fake `redis` module to avoid external dependency during import
class _FakeRedisModule:
    class _FakeRedis:
        def __init__(self):
            self.store = {}

        def from_url(self, *args, **kwargs):
            return self

    def from_url(self, *args, **kwargs):
        return self._FakeRedis()

import types
sys.modules.setdefault('redis', _FakeRedisModule())

from python_bot.plugins import moderation_admin


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, k):
        return self.store.get(k)

    def set(self, k, v, ex=None):
        self.store[k] = v

    def pipeline(self):
        return self

    def execute(self):
        return True

    def rpush(self, key, value):
        lst = self.store.get(key) or []
        lst.append(value)
        self.store[key] = lst

    def lrange(self, key, start, end):
        lst = self.store.get(key) or []
        if end == -1:
            return lst[start:]
        return lst[start:end + 1]

    def lpop(self, key):
        lst = self.store.get(key) or []
        if not lst:
            return None
        v = lst.pop(0)
        self.store[key] = lst
        return v

    def lrem(self, key, count, value):
        lst = self.store.get(key) or []
        try:
            lst.remove(value)
            self.store[key] = lst
            return 1
        except ValueError:
            return 0


class AdminPluginTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeRedis()
        moderation_admin._r = self.fake

    def test_list_and_apply(self):
        # prepare a suggestion
        suggestion = {'group_id': 10, 'user_id': 55, 'suggestion': 'ban', 'info': {'score': 120}, 'ts': 123}
        raw = json.dumps(suggestion)
        self.fake.rpush('moderation:actions', raw)

        # list
        res = moderation_admin.run({'text': '/mod_list', 'from': {'id': 1}}, None)
        self.assertIn('group:10', res)

        # apply
        res2 = moderation_admin.run({'text': '/mod_apply 1 ban', 'from': {'id': 1}}, None)
        self.assertIn('marcada como ban', res2)
        # applied list should contain entry
        applied = self.fake.store.get('moderation:applied')
        self.assertIsNotNone(applied)


if __name__ == '__main__':
    unittest.main()
