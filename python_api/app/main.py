from fastapi import FastAPI, Request, HTTPException
from typing import Optional, Any
from fastapi.responses import JSONResponse
import os
from pathlib import Path
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


def get_session_from_request(request: Request) -> Optional[dict]:
    # Return session dict if Authorization Bearer token corresponds to a stored session
    auth = request.headers.get('authorization')
    if auth and auth.lower().startswith('bearer '):
        token = auth.split(None, 1)[1]
        v = r.get(f'web:session:{token}')
        if v:
            dec = decrypt_value(v.decode()) if isinstance(v, bytes) else decrypt_value(v)
            if dec:
                try:
                    return json.loads(dec)
                except Exception:
                    return None
    return None

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
def get_messages(request: Request, limit: int = 20):
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
def get_devices(request: Request):
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
def add_device(payload: dict, request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('id') or not payload.get('token'):
        raise HTTPException(status_code=400, detail='invalid payload, require id and token')
    enc = encrypt_value(payload.get('token'))
    obj = { 'id': payload.get('id'), 'name': payload.get('name') or payload.get('id'), 'token': enc }
    r.rpush('web:devices', json.dumps(obj))
    return { 'status': 'added' }

@app.post('/send')
def send_message(payload: dict, request: Request):
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
def send_user(payload: dict, request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('chat_id') or not payload.get('text'):
        raise HTTPException(status_code=400, detail='invalid payload, require chat_id and text')
    outobj = { 'chat_id': payload.get('chat_id'), 'text': payload.get('text') }
    if payload.get('device_id'):
        outobj['device_id'] = payload.get('device_id')
    r.rpush('web:outbox', json.dumps(outobj))
    return { 'status': 'queued' }


@app.post('/ai')
def ai_generate(payload: dict, request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('prompt'):
        raise HTTPException(status_code=400, detail='invalid payload, require prompt')
    provider = payload.get('provider', 'local')
    model = payload.get('model', 'gpt2')

    if provider == 'local':
        try:
            from transformers import pipeline
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'transformers not installed: {e}')
        try:
            gen = pipeline('text-generation', model=model)
            params = {
                'max_length': int(payload.get('max_length', 128)),
                'do_sample': bool(payload.get('do_sample', True)),
                'top_k': int(payload.get('top_k', 50)),
                'num_return_sequences': int(payload.get('num_return_sequences', 1)),
            }
            res = gen(payload.get('prompt'), **params)
            return { 'provider': 'local', 'model': model, 'result': res }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    elif provider == 'huggingface':
        hf_key = os.getenv('HUGGINGFACE_API_KEY', '')
        if not hf_key:
            raise HTTPException(status_code=500, detail='HUGGINGFACE_API_KEY not set')
        hf_model = model
        url = f'https://api-inference.huggingface.co/models/{hf_model}'
        headers = {'Authorization': f'Bearer {hf_key}'}
        body = { 'inputs': payload.get('prompt'), 'parameters': payload.get('parameters', {}) }
        resp = requests.post(url, headers=headers, json=body)
        if not resp.ok:
            raise HTTPException(status_code=500, detail=resp.text)
        return resp.json()

    elif provider == 'openai':
        openai_key = os.getenv('OPENAI_API_KEY', '')
        if not openai_key:
            raise HTTPException(status_code=500, detail='OPENAI_API_KEY not set')
        data = { 'model': model, 'prompt': payload.get('prompt'), 'max_tokens': int(payload.get('max_tokens', 150)) }
        headers = { 'Authorization': f'Bearer {openai_key}', 'Content-Type': 'application/json' }
        resp = requests.post('https://api.openai.com/v1/completions', headers=headers, json=data)
        if not resp.ok:
            raise HTTPException(status_code=500, detail=resp.text)
        return resp.json()

    else:
        raise HTTPException(status_code=400, detail='unknown provider')

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


@app.get('/settings/backup')
def settings_backup(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    # fetch stored settings from redis key 'web:settings'
    v = r.get('web:settings')
    if not v:
        return {}
    try:
        return json.loads(v)
    except Exception:
        return {}


@app.post('/settings/restore')
def settings_restore(payload: dict, request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail='invalid payload, expect JSON object')
    # store whole settings object in redis
    try:
        r.set('web:settings', json.dumps(payload))
        return { 'status': 'ok' }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/settings/favicon')
def upload_favicon(payload: dict, request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    # payload should include either user_id or use session
    user = get_session_from_request(request)
    user_id = None
    if user and user.get('id'):
        user_id = str(user.get('id'))
    else:
        user_id = str(payload.get('user_id')) if payload.get('user_id') else None
    if not user_id:
        raise HTTPException(status_code=400, detail='user id not provided')
    favicon_b64 = payload.get('favicon')
    if not favicon_b64:
        raise HTTPException(status_code=400, detail='favicon (base64) required')
    try:
        # validate base64
        _ = base64.b64decode(favicon_b64)
        r.set(f'web:settings:favicon:{user_id}', favicon_b64)
        return { 'status': 'ok' }
    except Exception as e:
        raise HTTPException(status_code=400, detail='invalid base64')


@app.get('/settings/favicon/{user_id}')
def get_favicon(user_id: str):
    v = r.get(f'web:settings:favicon:{user_id}')
    if not v:
        raise HTTPException(status_code=404, detail='not found')
    try:
        b = base64.b64decode(v if isinstance(v, bytes) else v)
        return JSONResponse(content=b, media_type='image/png')
    except Exception:
        raise HTTPException(status_code=500, detail='cannot decode favicon')


@app.get('/pages.json')
def pages_list():
    """Return a JSON list of available web pages. If `web/pages.json` exists, return it.
    Otherwise scan the `web/` directory for HTML files and return href/label pairs.
    """
    # locate repository root from this file: ../../
    try:
        repo_root = Path(__file__).resolve().parents[2]
    except Exception:
        repo_root = Path('.')
    web_dir = repo_root / 'web'
    pages_json = web_dir / 'pages.json'
    if pages_json.exists():
        try:
            return json.loads(pages_json.read_text(encoding='utf-8'))
        except Exception:
            pass

    out = []
    try:
        if web_dir.exists() and web_dir.is_dir():
            for p in sorted(web_dir.glob('*.html')):
                href = p.name
                name = p.stem.replace('_', ' ').replace('-', ' ')
                label = name.title()
                if label.lower() == 'index':
                    label = 'Inicio'
                out.append({'href': href, 'label': label})
    except Exception:
        pass
    return out
