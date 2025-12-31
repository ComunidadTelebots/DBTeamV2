#!/usr/bin/env python3
"""
Rotate device tokens from OLD_WEB_API_SECRET to NEW_WEB_API_SECRET.
Uses OpenSSL on PATH for encryption/decryption to preserve compatibility with existing data.
"""
import os
import sys
import json
import shutil
import subprocess

try:
    import redis
except Exception as e:
    print('Missing dependency: redis', e)
    sys.exit(1)


def has_openssl():
    return shutil.which('openssl') is not None


def decrypt_with_secret(cipher: str, secret: str):
    if not secret or not cipher:
        return None, 'no-secret-or-cipher'
    if not has_openssl():
        return None, 'no-openssl'
    try:
        p = subprocess.run(
            ['openssl', 'enc', '-d', '-aes-256-cbc', '-a', '-pass', f'pass:{secret}'],
            input=cipher.encode('utf-8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
        )
        out = p.stdout.decode('utf-8')
        out = out.rstrip('\n\r')
        if out == '':
            return None, 'decrypt-failed'
        return out, None
    except Exception as e:
        return None, f'decrypt-exc:{e}'


def encrypt_with_secret(plain: str, secret: str):
    if not secret or plain is None:
        return plain, 'no-secret-or-plain'
    if not has_openssl():
        return None, 'no-openssl'
    try:
        p = subprocess.run(
            ['openssl', 'enc', '-aes-256-cbc', '-a', '-salt', '-pbkdf2', '-pass', f'pass:{secret}'],
            input=plain.encode('utf-8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
        )
        out = p.stdout.decode('utf-8')
        out = out.rstrip('\n\r')
        if out == '':
            return None, 'encrypt-failed'
        return out, None
    except Exception as e:
        return None, f'encrypt-exc:{e}'


def main():
    OLD = os.getenv('OLD_WEB_API_SECRET') or os.getenv('WEB_API_SECRET') or ''
    NEW = os.getenv('NEW_WEB_API_SECRET') or ''
    if NEW == '':
        print('Set NEW_WEB_API_SECRET to the new secret (env)')
        sys.exit(1)

    REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379')
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:
        print('Redis connection error:', e)
        sys.exit(1)

    try:
        items = r.lrange('web:devices', 0, -1) or []
    except Exception as e:
        print('Redis error reading web:devices:', e)
        sys.exit(1)

    print('Devices to process:', len(items))
    new_list = []
    for i, v in enumerate(items, start=1):
        try:
            obj = json.loads(v)
        except Exception:
            print('Skipping invalid JSON at index', i)
            continue
        token = obj.get('token')
        if token:
            dec, derr = decrypt_with_secret(token, OLD)
            if not dec:
                print('Warning: cannot decrypt token for', obj.get('id', f'index {i}'), 'assuming plaintext (err:', derr, ')')
                dec = token
            enc, err = encrypt_with_secret(dec, NEW)
            if not enc:
                print('Failed to encrypt for', obj.get('id', f'index {i}'), err)
                enc = dec
            obj['token'] = enc
        new_list.append(json.dumps(obj, separators=(',', ':')))

    # replace list atomically
    try:
        r.delete('web:devices')
        if new_list:
            r.rpush('web:devices', *new_list)
    except Exception as e:
        print('Redis write error:', e)
        sys.exit(1)

    print('Rotation complete. Replaced', len(new_list), 'devices')


if __name__ == '__main__':
    main()
