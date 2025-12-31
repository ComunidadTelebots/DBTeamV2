from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import redis
import json
import hashlib
import hmac
import secrets
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import requests
from .config import BOT_TOKEN, WEB_API_KEY, WEB_API_SECRET, WEB_API_ORIGIN, REDIS_URL

app = FastAPI()
r = redis.from_url(REDIS_URL)

def derive_key(secret: str) -> bytes:
    if not secret:
        return None
    salt = b'dbteam-salt'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return key

FERNET_KEY = derive_key(WEB_API_SECRET) if WEB_API_SECRET else None
FERNET = Fernet(FERNET_KEY) if FERNET_KEY else None

def encrypt_value(plain: str) -> str:
    if not FERNET:
        return plain
    return FERNET.encrypt(plain.encode()).decode()

def decrypt_value(cipher: str) -> str:
    if not FERNET:
        return cipher
    try:
        return FERNET.decrypt(cipher.encode()).decode()
    except Exception:
        return None

def check_auth(request: Request) -> bool:
    if not WEB_API_KEY:
        return True
    auth = request.headers.get('authorization')
    xapi = request.headers.get('x-api-key')
    if xapi and xapi == WEB_API_KEY:
        return True
    if auth and auth.lower().startswith('bearer '):
        token = auth.split(None, 1)[1]
        if token == WEB_API_KEY:
            return True
        # check session
        v = r.get(f'web:session:{token}')
        if v:
            dec = decrypt_value(v.decode()) if isinstance(v, bytes) else decrypt_value(v)
            if dec:
                try:
                    json.loads(dec)
                    return True
                except Exception:
                    return False
    return False

@app.middleware('http')
async def cors_and_auth(request: Request, call_next):
    # simple CORS handling for preflight
    if request.method == 'OPTIONS':
        return JSONResponse(status_code=200, content='')
    response = await call_next(request)
    response.headers['Access-Control-Allow-Origin'] = WEB_API_ORIGIN
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-API-Key'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

@app.get('/messages')
def get_messages(limit: int = 20, request: Request = None):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    items = r.lrange('web:messages', 0, limit-1) or []
    out = []
    for it in items:
        try:
            out.append(json.loads(it))
        except Exception:
            continue
    return out

@app.get('/devices')
def get_devices(request: Request = None):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    items = r.lrange('web:devices', 0, -1) or []
    out = []
    for it in items:
        try:
            obj = json.loads(it)
            out.append({ 'id': obj.get('id'), 'name': obj.get('name') })
        except Exception:
            continue
    return out

@app.post('/devices/add')
def add_device(payload: dict, request: Request = None):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('id') or not payload.get('token'):
        raise HTTPException(status_code=400, detail='invalid payload, require id and token')
    enc = encrypt_value(payload.get('token'))
    obj = { 'id': payload.get('id'), 'name': payload.get('name') or payload.get('id'), 'token': enc }
    r.rpush('web:devices', json.dumps(obj))
    return { 'status': 'added' }

@app.post('/send')
def send_message(payload: dict, request: Request = None):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('chat_id') or not payload.get('text'):
        raise HTTPException(status_code=400, detail='invalid payload, require chat_id and text')
    token_to_use = BOT_TOKEN
    if payload.get('device_id'):
        items = r.lrange('web:devices', 0, -1) or []
        for it in items:
            try:
                obj = json.loads(it)
                if obj.get('id') == payload.get('device_id') and obj.get('token'):
                    dec = decrypt_value(obj.get('token'))
                    if dec:
                        token_to_use = dec
                    else:
                        token_to_use = obj.get('token')
                    break
            except Exception:
                continue
    if not token_to_use:
        raise HTTPException(status_code=500, detail='no BOT_TOKEN available')
    url = f'https://api.telegram.org/bot{token_to_use}/sendMessage'
    body = { 'chat_id': payload.get('chat_id'), 'text': payload.get('text') }
    resp = requests.post(url, json=body)
    if not resp.ok:
        raise HTTPException(status_code=500, detail=resp.text)
    return resp.json()

@app.post('/send_user')
def send_user(payload: dict, request: Request = None):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('chat_id') or not payload.get('text'):
        raise HTTPException(status_code=400, detail='invalid payload, require chat_id and text')
    outobj = { 'chat_id': payload.get('chat_id'), 'text': payload.get('text') }
    if payload.get('device_id'):
        outobj['device_id'] = payload.get('device_id')
    r.rpush('web:outbox', json.dumps(outobj))
    return { 'status': 'queued' }

@app.post('/auth')
def auth(payload: dict):
    # verify Telegram login widget
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail='BOT_TOKEN not set on server')
    if not payload or not payload.get('hash'):
        raise HTTPException(status_code=400, detail='invalid auth payload')
    parts = [k for k in payload.keys() if k != 'hash']
    parts.sort()
    data_check = '\n'.join([f"{k}={payload[k]}" for k in parts])
    key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    calc = hmac.new(key, data_check.encode(), hashlib.sha256).hexdigest()
    if calc != payload.get('hash'):
        raise HTTPException(status_code=401, detail='invalid signature')
    token = secrets.token_hex(32)
    sess = { 'id': payload.get('id'), 'first_name': payload.get('first_name'), 'last_name': payload.get('last_name'), 'username': payload.get('username') }
    sess_raw = json.dumps(sess)
    enc = encrypt_value(sess_raw)
    r.setex(f'web:session:{token}', 3600, enc)
    return { 'token': token, 'ttl': 3600 }
