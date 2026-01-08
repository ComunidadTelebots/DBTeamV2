import os
import sys
import importlib
import unittest
import json


class FakeRedis:
    def __init__(self):
        self.kv = {}
        self.lists = {}
        self.sets = {}
        self.hashes = {}

    def from_url(self, url, decode_responses=True):
        return self

    def get(self, k):
        return self.kv.get(k)

    def set(self, k, v, ex=None):
        self.kv[k] = v

    def incr(self, k):
        v = int(self.kv.get(k) or 0) + 1
        self.kv[k] = str(v)
        return v

    def expire(self, k, seconds):
        return True

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

    def sadd(self, k, v):
        self.sets.setdefault(k, set()).add(v)

    def srem(self, k, v):
        self.sets.get(k, set()).discard(v)

    def smembers(self, k):
        return set(self.sets.get(k, set()))

    def sismember(self, k, v):
        return v in self.sets.get(k, set())

    def hset(self, h, key, val):
        self.hashes.setdefault(h, {})[key] = val

    def hdel(self, h, key):
        if h in self.hashes:
            self.hashes[h].pop(key, None)


class StreamServerTests(unittest.TestCase):
    def setUp(self):
        # inject fake redis module before importing stream_server
        self.fake = FakeRedis()
        fake_mod = type(sys)('redis')
        fake_mod.from_url = lambda url, decode_responses=True: self.fake
        sys.modules['redis'] = fake_mod
        # ensure abuse_protection uses same fake (reload so it picks our fake redis)
        apmod = importlib.import_module('python_api.abuse_protection')
        importlib.reload(apmod)
        # set admin token
        os.environ['ADMIN_TOKEN'] = 'admintest'
        # import/ reload stream_server
        if 'python_api.stream_server' in sys.modules:
            importlib.reload(sys.modules['python_api.stream_server'])
        self.ss = importlib.import_module('python_api.stream_server')
        # ensure the loaded module's abuse._r points to our fake redis
        try:
            if hasattr(self.ss, 'abuse') and getattr(self.ss, 'abuse') is not None:
                self.ss.abuse._r = self.fake
        except Exception:
            pass
        self.client = self.ss.app.test_client()

    def tearDown(self):
        sys.modules.pop('redis', None)
        os.environ.pop('ADMIN_TOKEN', None)

    def test_admin_block_and_list(self):
        # without token
        r = self.client.get('/admin/abuse/blocked')
        self.assertEqual(r.status_code, 401)
        # with token
        r = self.client.get('/admin/abuse/blocked', headers={'X-ADMIN-TOKEN': 'admintest'})
        self.assertEqual(r.status_code, 200, f"blocked response: {r.get_json()}")
        data = r.get_json()
        self.assertIn('blocked', data)
        # ensure abuse helper available
        self.assertIsNotNone(getattr(self.ss, 'abuse', None), 'abuse module not loaded in stream_server')
        # perform a direct block via the abuse module (ensure fake redis updated)
        self.ss.abuse.block_ip('9.9.9.9', reason='test')
        self.assertTrue(self.fake.sismember('abuse:blacklist:ip', '9.9.9.9'))
        # ensure test client IP is not blacklisted (before_request may block otherwise)
        self.fake.srem('abuse:blacklist:ip', '127.0.0.1')
        # list via endpoint
        r = self.client.get('/admin/abuse/blocked', headers={'X-ADMIN-TOKEN': 'admintest'})
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn('9.9.9.9', data['blocked']['ips'])
        # now test unblock endpoint
        r = self.client.post('/admin/abuse/unblock', headers={'X-ADMIN-TOKEN': 'admintest'}, data=json.dumps({'ip':'9.9.9.9'}), content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(self.fake.sismember('abuse:blacklist:ip', '9.9.9.9'))


if __name__ == '__main__':
    unittest.main()
