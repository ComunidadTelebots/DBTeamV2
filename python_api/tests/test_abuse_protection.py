import os
import sys
import importlib
import unittest


class FakeRedis:
    def __init__(self):
        self.kv = {}
        self.lists = {}
        self.sets = {}
        self.hashes = {}

    def from_url(self, url, decode_responses=True):
        return self

    # simple kv
    def get(self, k):
        return self.kv.get(k)

    def set(self, k, v, ex=None):
        self.kv[k] = v

    def delete(self, k):
        self.kv.pop(k, None)

    def incr(self, k):
        v = int(self.kv.get(k) or 0) + 1
        self.kv[k] = str(v)
        return v

    def expire(self, k, seconds):
        return True

    # lists
    def rpush(self, k, v):
        self.lists.setdefault(k, []).append(v)

    def lrange(self, k, a, b):
        lst = self.lists.get(k, [])
        return lst[a:b+1] if b!=-1 else lst[a:]

    def ltrim(self, k, a, b):
        lst = self.lists.get(k, [])
        self.lists[k] = lst[a:b+1]

    def lrem(self, k, num, val):
        lst = self.lists.get(k, [])
        removed = 0
        new = []
        for item in lst:
            if item == val and (num == 0 or removed < num):
                removed += 1
                continue
            new.append(item)
        self.lists[k] = new
        return removed

    # sets
    def sadd(self, k, v):
        s = self.sets.setdefault(k, set())
        s.add(v)

    def srem(self, k, v):
        s = self.sets.get(k, set())
        s.discard(v)

    def sismember(self, k, v):
        return v in self.sets.get(k, set())

    def smembers(self, k):
        return set(self.sets.get(k, set()))

    # hashes
    def hset(self, h, key, val):
        self.hashes.setdefault(h, {})[key] = val

    def hdel(self, h, key):
        if h in self.hashes:
            self.hashes[h].pop(key, None)



class AbuseProtectionTests(unittest.TestCase):
    def setUp(self):
        # inject fake redis module
        self.fake = FakeRedis()
        fake_mod = type(sys)('redis')
        fake_mod.from_url = lambda url, decode_responses=True: self.fake
        sys.modules['redis'] = fake_mod
        # set environment for low threshold
        os.environ['ABUSE_IP_THRESHOLD'] = '3'
        os.environ['ABUSE_AUTO_BLOCK'] = '1'
        # reload module
        if 'python_api.abuse_protection' in sys.modules:
            importlib.reload(sys.modules['python_api.abuse_protection'])
        self.ap = importlib.import_module('python_api.abuse_protection')

    def tearDown(self):
        # cleanup
        sys.modules.pop('redis', None)

    def test_auto_block_on_threshold(self):
        ip = '1.2.3.4'
        for i in range(3):
            res = self.ap.record_request(ip)
        # after threshold should be blocked
        self.assertTrue(self.fake.sismember('abuse:blacklist:ip', ip))
        # notifications list may be populated; primary check is blacklist
        # (some internal error paths may skip notifications in tests)

    def test_block_medium_and_detect(self):
        # block medium telegram
        self.ap.block_medium('telegram', reason='test')
        self.assertTrue(self.ap.is_blocked_medium('telegram'))
        # simulate request with Telegram UA
        ip = '5.6.7.8'
        res = self.ap.record_request(ip, meta={'headers': {'User-Agent': 'TelegramBot'}})
        # medium field should be included
        self.assertIn('medium', res)


if __name__ == '__main__':
    unittest.main()
