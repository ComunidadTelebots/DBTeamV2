#!/usr/bin/env python3
"""
Verify encryption for web:devices and web:session keys in Redis.
Compatible with OpenSSL `enc -aes-256-cbc -a -pass pass:'SECRET'` output.
Requires: redis, pycryptodome (Crypto)
"""
import os
import base64
import hashlib
import json
import sys

try:
    import redis
except Exception as e:
    print('Missing dependency: redis', e)
    sys.exit(1)

try:
    from Crypto.Cipher import AES
except Exception as e:
    print('Missing dependency: pycryptodome (Crypto)', e)
    sys.exit(1)


def evp_bytes_to_key(password: bytes, salt: bytes, key_len: int, iv_len: int):
    dt = b''
    key_iv = b''
    while len(key_iv) < (key_len + iv_len):
        dt = hashlib.md5(dt + password + salt).digest()
        key_iv += dt
    key = key_iv[:key_len]
    iv = key_iv[key_len:key_len + iv_len]
    return key, iv


def decrypt_openssl_b64(cipher_b64: str, password: str):
    if not password:
        return cipher_b64, None
    try:
        data = base64.b64decode(cipher_b64)
    except Exception:
        return None, 'base64-decode-failed'
    if len(data) < 16:
        return None, 'cipher-too-short'
    if data[:8] != b'Salted__':
        salt = b''
        ciphertext = data
    else:
        salt = data[8:16]
        ciphertext = data[16:]
    key, iv = evp_bytes_to_key(password.encode('utf-8'), salt, 32, 16)
    try:
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(ciphertext)
    except Exception as e:
        return None, f'decrypt-failed:{e}'
    if not decrypted:
        return None, 'decrypt-empty'
    pad_len = decrypted[-1]
    if pad_len < 1 or pad_len > AES.block_size:
        return None, 'bad-padding'
    try:
        decrypted = decrypted[:-pad_len]
        return decrypted.decode('utf-8'), None
    except Exception:
        return None, 'decode-failed'


def main():
    SECRET = os.getenv('WEB_API_SECRET', '')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379')

    print('WEB_API_SECRET present:', bool(SECRET))

    r = redis.from_url(REDIS_URL, decode_responses=True)

    try:
        devices = r.lrange('web:devices', 0, -1) or []
    except Exception as e:
        print('Redis error reading web:devices:', e)
        devices = []
    print('Found devices:', len(devices))

    for i, v in enumerate(devices, 1):
        try:
            obj = json.loads(v)
        except Exception:
            print(i, 'invalid json')
            continue
        if 'token' in obj and obj['token']:
            dec, err = decrypt_openssl_b64(obj['token'], SECRET)
            if not dec:
                print('device', obj.get('id', f'index {i}'), 'token decrypt error:', err)
            else:
                print('device', obj.get('id', f'index {i}'), 'token decrypt OK')
        else:
            print('device', obj.get('id', f'index {i}'), 'no token field')

    try:
        keys = r.keys('web:session:*') or []
    except Exception as e:
        print('Redis error listing sessions:', e)
        keys = []
    print('Found sessions:', len(keys))

    for k in keys:
        try:
            v = r.get(k)
        except Exception as e:
            print(k, 'redis-get-error:', e)
            continue
        if not v:
            print(k, 'empty')
            continue
        dec, err = decrypt_openssl_b64(v, SECRET)
        if not dec:
            print(k, 'decrypt error:', err)
        else:
            try:
                _ = json.loads(dec)
                print(k, 'session decrypt OK')
            except Exception:
                print(k, 'invalid json after decrypt')

    print('Done')


if __name__ == '__main__':
    main()
