import sys
import os
import unittest

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
import importlib
sys.modules.setdefault('redis', _FakeRedisModule())

from python_bot.moderation import classifier


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
        if isinstance(lst, str):
            # shouldn't happen in tests
            lst = [lst]
        lst.append(value)
        self.store[key] = lst

    def lrange(self, key, start, end):
        lst = self.store.get(key) or []
        # emulate inclusive end
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


class ClassifierTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeRedis()
        # patch module redis instance
        classifier._r = self.fake

    def test_link_generates_warn(self):
        user = {'id': 123}
        msg = {'text': 'Check this https://t.me/join/abc', 'media_type': None}
        out = classifier.classify_message(1, user, msg)
        self.assertGreaterEqual(out['score'], classifier.WEIGHTS['link'])
        self.assertEqual(out['suggestion'], 'warn')

    def test_repeated_escalates_to_mute(self):
        user = {'id': 123}
        msg = {'text': 'Check this room https://t.me/room', 'media_type': None}
        first = classifier.classify_message(1, user, msg)
        self.assertEqual(first['suggestion'], 'warn')
        second = classifier.classify_message(1, user, msg)
        # second should include repeated weight
        self.assertIn('repeated_message', second['reasons'])
        self.assertEqual(second['suggestion'], 'mute')


if __name__ == '__main__':
    unittest.main()
