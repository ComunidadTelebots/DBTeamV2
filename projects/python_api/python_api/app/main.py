from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import shlex
import platform
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
import time
import uuid
import hmac as _hmaclib
import re
# Load configuration from a local `config.py` if present; otherwise fall back to env vars
try:
    from .config import BOT_TOKEN, WEB_API_KEY, WEB_API_SECRET, WEB_API_ORIGIN, REDIS_URL
except Exception:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    WEB_API_KEY = os.getenv('WEB_API_KEY')
    WEB_API_SECRET = os.getenv('WEB_API_SECRET')
    WEB_API_ORIGIN = os.getenv('WEB_API_ORIGIN')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')

app = FastAPI()
r = redis.from_url(REDIS_URL)

# Configure CORS middleware early. If WEB_API_ORIGIN is set, allow only that origin;
# otherwise allow common localhost origins used during development.
if WEB_API_ORIGIN:
    _origins = [WEB_API_ORIGIN]
else:
    _origins = [
        'http://127.0.0.1:8080',
        'http://localhost:8080',
        'http://127.0.0.1:8000',
        'http://localhost:8000',
        'https://cas.chat',
    ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# server start time for uptime reporting
START_TIME = int(time.time())

# Optional: auto-register a bot token on server startup if provided via env var
AUTO_REGISTER_BOT_TOKEN = os.getenv('AUTO_REGISTER_BOT_TOKEN')

def _register_bot_token_on_startup(token: str):
    if not token:
        return None
    try:
        resp = requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=10)
    except Exception as e:
        print('auto-register: telegram error', e)
        return None
    if not resp.ok:
        print('auto-register: telegram returned not ok', resp.text)
        return None
    try:
        data = resp.json()
    except Exception:
        data = { 'ok': False }
    result = data.get('result') if isinstance(data, dict) else None
    bot_id = None
    bot_name = None
    if result:
        bot_id = result.get('id')
        bot_name = result.get('username') or result.get('first_name')
    device_id = f'bot:{bot_id}' if bot_id else f'bot:{secrets.token_hex(6)}'
    device_name = bot_name or device_id
    enc = encrypt_value(token)
    obj = { 'id': device_id, 'name': device_name, 'token': enc }
    try:
        items = r.lrange('web:devices', 0, -1) or []
        exists = False
        for it in items:
            try:
                cur = json.loads(it)
                if cur.get('id') == obj['id']:
                    exists = True
                    break
            except Exception:
                continue
        if not exists:
            r.rpush('web:devices', json.dumps(obj))
            print('auto-register: device registered', device_id)
        else:
            print('auto-register: device already present', device_id)
    except Exception as e:
        print('auto-register: failed to persist device', e)
    return obj


@app.on_event('startup')
def _auto_register_startup_event():
    if AUTO_REGISTER_BOT_TOKEN:
        try:
            _register_bot_token_on_startup(AUTO_REGISTER_BOT_TOKEN)
        except Exception as e:
            print('auto-register startup exception:', e)

# Note: static files will be mounted at the end of this module so API routes
# (including /tdlib) are registered first and not shadowed by StaticFiles.

# Include tdlib router (scaffold). If import fails, register a JSON fallback
TDLIB_AVAILABLE = True
try:
    from .tdlib_router import router as tdlib_router
    app.include_router(tdlib_router, prefix='/tdlib')
    print('tdlib router included')
except Exception as _e:
    TDLIB_AVAILABLE = False
    print('tdlib router import failed:', repr(_e))
    # Provide minimal JSON endpoints to surface an explicit error instead of HTML
    from fastapi import APIRouter
    fallback = APIRouter()
    @fallback.post('/connect')
    def tdlib_connect_fallback():
        raise HTTPException(status_code=501, detail='tdlib router not available on server')

    @fallback.post('/disconnect')
    def tdlib_disconnect_fallback():
        raise HTTPException(status_code=501, detail='tdlib router not available on server')

    @fallback.post('/send')
    def tdlib_send_fallback():
        raise HTTPException(status_code=501, detail='tdlib router not available on server')

    @fallback.get('/chats')
    def tdlib_chats_fallback():
        raise HTTPException(status_code=501, detail='tdlib router not available on server')

    @fallback.get('/messages')
    def tdlib_messages_fallback():
        raise HTTPException(status_code=501, detail='tdlib router not available on server')

    app.include_router(fallback, prefix='/tdlib')

# Process control: define named processes and commands to start them
REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = REPO_ROOT / 'run'
RUN_DIR.mkdir(parents=True, exist_ok=True)

PROCESS_DEFS = {
    'python_bot': {
        'cmd': ['python', str(REPO_ROOT / 'python_bot' / 'bot.py')],
        'cwd': str(REPO_ROOT)
    },
    'lua_bot': {
        'cmd': ['lua', str(REPO_ROOT / 'bot' / 'bot.lua')],
        'cwd': str(REPO_ROOT)
    }
}

def pidfile_for(name: str) -> Path:
    return RUN_DIR / f"{name}.pid"

def logfile_for(name: str) -> Path:
    return RUN_DIR / f"{name}.log"

def is_pid_running(pid: int) -> bool:
    try:
        if platform.system() == 'Windows':
            # os.kill with 0 works on Windows in Python 3.8+
            os.kill(pid, 0)
        else:
            os.kill(pid, 0)
        return True
    except Exception:
        return False

def read_pid(name: str):
    p = pidfile_for(name)
    if not p.exists():
        return None
    try:
        return int(p.read_text(encoding='utf-8').strip())
    except Exception:
        return None

def start_process(name: str):
    if name not in PROCESS_DEFS:
        raise ValueError('unknown process')
    prog = PROCESS_DEFS[name]
    logp = logfile_for(name)
    pidp = pidfile_for(name)
    # open log file
    lf = open(str(logp), 'ab')
    # spawn detached process
    if platform.system() == 'Windows':
        # CREATE_NEW_PROCESS_GROUP to detach
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        p = subprocess.Popen(prog['cmd'], cwd=prog.get('cwd'), stdout=lf, stderr=subprocess.STDOUT, creationflags=creationflags)
    else:
        p = subprocess.Popen(prog['cmd'], cwd=prog.get('cwd'), stdout=lf, stderr=subprocess.STDOUT, close_fds=True)
    # write pid
    try:
        pidp.write_text(str(p.pid), encoding='utf-8')
    except Exception:
        pass
    return p.pid

def process_status(name: str):
    pid = read_pid(name)
    running = False
    if pid:
        running = is_pid_running(pid)
    return { 'name': name, 'pid': pid, 'running': running, 'log': str(logfile_for(name)) }



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


# Static files mount moved to the end of this file to avoid shadowing API routes.

@app.middleware('http')
async def cors_and_auth(request: Request, call_next):
    # Authentication passthrough middleware. Leave CORS handling to CORSMiddleware.
    response = await call_next(request)
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


@app.post('/translations/suggest')
def suggest_translation(payload: dict, request: Request):
    """Accept a translation suggestion. Payload: {lang, key, value, author (opt), comment (opt)}"""
    if not payload or not payload.get('lang') or not payload.get('key'):
        raise HTTPException(status_code=400, detail='invalid payload, require lang and key')
    sid = uuid.uuid4().hex
    obj = {
        'id': sid,
        'lang': payload.get('lang'),
        'scope': payload.get('scope') or 'bot',
        'key': payload.get('key'),
        'value': payload.get('value', ''),
        'author': payload.get('author') or None,
        'comment': payload.get('comment') or None,
        'status': 'pending',
        'created_at': int(time.time())
    }
    r.set(f'web:translation:suggestion:{sid}', json.dumps(obj))
    r.rpush('web:translation:suggestions', sid)
    return { 'status': 'ok', 'id': sid }


def is_admin_request(request: Request) -> bool:
    if not check_auth(request):
        return False
    sess = get_session_from_request(request)
    if sess and sess.get('is_admin'):
        return True
    xapi = request.headers.get('x-api-key')
    if xapi and WEB_API_KEY and xapi == WEB_API_KEY:
        return True
    return False


@app.get('/translations/suggestions')
def list_suggestions(request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    ids = r.lrange('web:translation:suggestions', 0, -1) or []
    out = []
    for sid in ids:
        try:
            sid_str = sid.decode() if isinstance(sid, bytes) else sid
            data = r.get(f'web:translation:suggestion:{sid_str}')
            if data:
                out.append(json.loads(data))
        except Exception:
            continue
    return out


@app.post('/translations/apply')
def apply_suggestion(payload: dict, request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    sid = payload.get('id') if payload else None
    if not sid:
        raise HTTPException(status_code=400, detail='id required')
    data = r.get(f'web:translation:suggestion:{sid}')
    if not data:
        raise HTTPException(status_code=404, detail='suggestion not found')
    sug = json.loads(data)
    try:
        repo_root = Path(__file__).resolve().parents[2]
    except Exception:
        repo_root = Path('.')
    scope = sug.get('scope') or payload.get('scope') or 'bot'
    i18n_dir = repo_root / 'web' / 'i18n' / scope
    i18n_dir.mkdir(parents=True, exist_ok=True)
    lang_file = i18n_dir / f"{sug['lang']}.json"
    cur = {}
    if lang_file.exists():
        try:
            cur = json.loads(lang_file.read_text(encoding='utf-8'))
        except Exception:
            cur = {}
    cur[sug['key']] = sug['value']
    lang_file.write_text(json.dumps(cur, indent=2, ensure_ascii=False), encoding='utf-8')
    sug['status'] = 'applied'
    applied_by = get_session_from_request(request)
    sug['applied_by'] = applied_by if applied_by else {'api_key': True}
    sug['applied_at'] = int(time.time())
    r.set(f'web:translation:suggestion:{sid}', json.dumps(sug))
    return { 'status': 'applied', 'id': sid }


@app.post('/processes/restart')
def processes_restart(payload: dict, request: Request):
    """Restart a named process. Payload: { name: 'python_bot' }
    Requires admin privileges (WEB_API_KEY or admin session).
    """
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('name'):
        raise HTTPException(status_code=400, detail='name required')
    name = payload.get('name')
    if name not in PROCESS_DEFS:
        raise HTTPException(status_code=400, detail='unknown process')
    try:
        pid = start_process(name)
        return { 'status': 'started', 'name': name, 'pid': pid }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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


@app.delete('/devices/{device_id}')
def delete_device(device_id: str, request: Request):
    """Remove a registered device by id from `web:devices` list."""
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    try:
        items = r.lrange('web:devices', 0, -1) or []
        kept = []
        found = False
        for it in items:
            try:
                obj = json.loads(it)
                if obj.get('id') == device_id:
                    found = True
                    continue
                kept.append(json.dumps(obj))
            except Exception:
                # if parse fails, keep original raw
                kept.append(it if isinstance(it, str) else (it.decode() if isinstance(it, bytes) else str(it)))
        # replace list atomically
        try:
            r.delete('web:devices')
        except Exception:
            pass
        for v in kept:
            try:
                r.rpush('web:devices', v)
            except Exception:
                continue
        if not found:
            raise HTTPException(status_code=404, detail='device not found')
        return { 'status': 'deleted', 'id': device_id }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/bot/verify')
def bot_verify(payload: dict, request: Request):
    """Verify a Telegram Bot token, register it as a device and import local bot data.
    Payload: { token: '<bot token>', id: '<optional device id>', name: '<optional name>' }
    Returns registered device info and imported data (infohashes, allowed_senders).
    """
    if not payload or not payload.get('token'):
        raise HTTPException(status_code=400, detail='token required')
    token = payload.get('token')
    # verify token with Telegram getMe
    try:
        resp = requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=10)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not resp.ok:
        raise HTTPException(status_code=400, detail=f'telegram error: {resp.text}')
    try:
        data = resp.json()
    except Exception:
        data = { 'ok': False }
    result = data.get('result') if isinstance(data, dict) else None
    bot_id = None
    bot_name = None
    if result:
        bot_id = result.get('id')
        bot_name = result.get('username') or result.get('first_name')

    # attempt to fetch a profile photo URL for the bot (best-effort)
    photo_url = None
    try:
        if bot_id:
            p = requests.get(f'https://api.telegram.org/bot{token}/getUserProfilePhotos', params={'user_id': bot_id, 'limit': 1}, timeout=10)
            if p.ok:
                pj = p.json()
                pres = pj.get('result') if isinstance(pj, dict) else None
                photos = pres.get('photos') if pres else None
                if photos and len(photos) > 0 and isinstance(photos[0], list):
                    sizes = photos[0]
                    if sizes:
                        file_id = sizes[-1].get('file_id')
                        if file_id:
                            gf = requests.get(f'https://api.telegram.org/bot{token}/getFile', params={'file_id': file_id}, timeout=10)
                            if gf.ok:
                                gfj = gf.json()
                                gfres = gfj.get('result') if isinstance(gfj, dict) else None
                                file_path = gfres.get('file_path') if gfres else None
                                if file_path:
                                    photo_url = f'https://api.telegram.org/file/bot{token}/{file_path}'
    except Exception:
        photo_url = None

    # choose device id
    device_id = payload.get('id') or (f'bot:{bot_id}' if bot_id else f'bot:{secrets.token_hex(6)}')
    device_name = payload.get('name') or bot_name or device_id

    # store encrypted token as a web device (reuse existing structure)
    enc = encrypt_value(token)
    obj = { 'id': device_id, 'name': device_name, 'token': enc }
    # avoid duplicates
    try:
        items = r.lrange('web:devices', 0, -1) or []
        exists = False
        for it in items:
            try:
                cur = json.loads(it)
                if cur.get('id') == obj['id']:
                    exists = True
                    break
            except Exception:
                continue
        if not exists:
            r.rpush('web:devices', json.dumps(obj))
    except Exception:
        # best-effort: ignore storage errors
        pass

    # Import bot-local data stored under storage prefix `dbteam:` (infohashes, allowed_senders)
    infohashes = []
    try:
        for ih in (r.smembers('dbteam:infohashes') or set()):
            try:
                infohashes.append(ih.decode() if isinstance(ih, bytes) else ih)
            except Exception:
                continue
    except Exception:
        infohashes = []

    allowed_senders = {}
    try:
        for k in r.scan_iter(match='dbteam:allowed_senders:*'):
            try:
                keyname = k.decode() if isinstance(k, bytes) else k
                parts = keyname.split(':')
                chatid = parts[-1]
                members = r.smembers(keyname) or set()
                allowed_senders[str(chatid)] = [int(x) for x in [(m.decode() if isinstance(m, bytes) else m) for m in members]]
            except Exception:
                continue
    except Exception:
        allowed_senders = {}

    return { 'status': 'ok', 'device': { 'id': device_id, 'name': device_name }, 'infohashes': infohashes, 'allowed_senders': allowed_senders, 'getMe': result, 'photo_url': photo_url }


@app.get('/bot/data')
def bot_data(request: Request):
    """Return imported bot-local data (infohashes and allowed_senders) for the web UI."""
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    infohashes = []
    try:
        for ih in (r.smembers('dbteam:infohashes') or set()):
            try:
                infohashes.append(ih.decode() if isinstance(ih, bytes) else ih)
            except Exception:
                continue
    except Exception:
        infohashes = []
    allowed_senders = {}
    try:
        for k in r.scan_iter(match='dbteam:allowed_senders:*'):
            try:
                keyname = k.decode() if isinstance(k, bytes) else k
                parts = keyname.split(':')
                chatid = parts[-1]
                members = r.smembers(keyname) or set()
                allowed_senders[str(chatid)] = [int(x) for x in [(m.decode() if isinstance(m, bytes) else m) for m in members]]
            except Exception:
                continue
    except Exception:
        allowed_senders = {}
    return { 'infohashes': infohashes, 'allowed_senders': allowed_senders }


@app.post('/bot/files')
def bot_files(payload: dict, request: Request):
    """Best-effort: list files uploaded by the bot by scanning recent getUpdates.
    Payload: { token: '<bot token>', limit: 50 }
    Returns: list of { chat_id, date, type, file_id, file_name (opt), file_url }
    Note: this only sees updates available via getUpdates (webhook bots may not have history here).
    """
    if not payload or not payload.get('token'):
        raise HTTPException(status_code=400, detail='token required')
    token = payload.get('token')
    limit = int(payload.get('limit', 50))
    try:
        resp = requests.get(f'https://api.telegram.org/bot{token}/getUpdates', params={'limit': limit}, timeout=10)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not resp.ok:
        raise HTTPException(status_code=400, detail=f'telegram error: {resp.text}')
    try:
        data = resp.json()
    except Exception:
        data = { 'result': [] }
    updates = data.get('result') if isinstance(data, dict) else []
    out_files = []
    for u in updates:
        for msgkey in ('message', 'edited_message'):
            msg = u.get(msgkey)
            if not msg:
                continue
            frm = msg.get('from') or {}
            if not frm.get('is_bot'):
                continue
            chat = msg.get('chat') or {}
            chat_id = chat.get('id')
            date = msg.get('date')
            # check common attachment types
            file_id = None
            ftype = None
            fname = None
            if 'photo' in msg and msg.get('photo'):
                sizes = msg.get('photo')
                if isinstance(sizes, list) and sizes:
                    file_id = sizes[-1].get('file_id')
                    ftype = 'photo'
            if not file_id and msg.get('document'):
                file_id = msg['document'].get('file_id')
                fname = msg['document'].get('file_name')
                ftype = 'document'
            if not file_id and msg.get('video'):
                file_id = msg['video'].get('file_id')
                ftype = 'video'
            if not file_id and msg.get('audio'):
                file_id = msg['audio'].get('file_id')
                ftype = 'audio'
            if not file_id and msg.get('voice'):
                file_id = msg['voice'].get('file_id')
                ftype = 'voice'
            if file_id:
                # resolve file path
                try:
                    gf = requests.get(f'https://api.telegram.org/bot{token}/getFile', params={'file_id': file_id}, timeout=10)
                    if gf.ok:
                        gfj = gf.json()
                        gfres = gfj.get('result') if isinstance(gfj, dict) else None
                        file_path = gfres.get('file_path') if gfres else None
                        if file_path:
                            file_url = f'https://api.telegram.org/file/bot{token}/{file_path}'
                        else:
                            file_url = None
                    else:
                        file_url = None
                except Exception:
                    file_url = None
                out_files.append({ 'chat_id': chat_id, 'date': date, 'type': ftype, 'file_id': file_id, 'file_name': fname, 'file_url': file_url })
    return { 'files': out_files }

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


@app.post('/bot/send')
def bot_send(payload: dict, request: Request):
    """Alias endpoint to send via server-side Bot API. Accepts {chat_id, text, attachment_url (opt), device_id (opt)}"""
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('chat_id'):
        raise HTTPException(status_code=400, detail='chat_id required')
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

    # choose send method depending on presence of attachment and file type
    attach = payload.get('attachment_url')
    try:
        if attach and re.search(r'\.(jpg|jpeg|png|gif|webp)(\?|$)', str(attach).lower()):
            url = f'https://api.telegram.org/bot{token_to_use}/sendPhoto'
            body = { 'chat_id': payload.get('chat_id'), 'photo': attach, 'caption': payload.get('text', '') }
        else:
            url = f'https://api.telegram.org/bot{token_to_use}/sendMessage'
            body = { 'chat_id': payload.get('chat_id'), 'text': payload.get('text', '') }
        resp = requests.post(url, json=body)
        if not resp.ok:
            raise HTTPException(status_code=500, detail=resp.text)
        return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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


@app.post('/auth/login')
def auth_login(payload: dict):
    """Simple login endpoint for the web UI.
    Accepts either { "api_key": "..." } or { "user": "...", "pass": "..." }.
    If the provided api_key or pass equals `WEB_API_KEY` the request is accepted and
    a session token is returned. The session includes `is_admin` when authenticated
    with the API key.
    """
    if not payload:
        raise HTTPException(status_code=400, detail='invalid payload')
    # api_key path
    if payload.get('api_key'):
        if WEB_API_KEY and payload.get('api_key') == WEB_API_KEY:
            token = secrets.token_hex(32)
            sess = { 'user': 'api_key_user', 'is_admin': True }
            enc = encrypt_value(json.dumps(sess))
            r.setex(f'web:session:{token}', 3600, enc)
            return { 'token': token, 'ttl': 3600 }
        else:
            raise HTTPException(status_code=401, detail='invalid api_key')

    # username/password path — first check stored users in Redis
    user = payload.get('user')
    passwd = payload.get('pass')
    if not user or not passwd:
        raise HTTPException(status_code=400, detail='user and pass required')

    def _verify_password(stored: str, password: str) -> bool:
        try:
            salt_hex, dk_hex = stored.split(':')
            salt = bytes.fromhex(salt_hex)
            dk = bytes.fromhex(dk_hex)
            test = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
            return _hmaclib.compare_digest(test, dk)
        except Exception:
            return False

    user_key = f'web:user:{user}'
    stored = r.get(user_key)
    if stored:
        try:
            obj = json.loads(stored)
            pw = obj.get('pw')
            if pw and _verify_password(pw, passwd):
                token = secrets.token_hex(32)
                sess = { 'user': user, 'is_admin': bool(obj.get('is_admin')) }
                enc = encrypt_value(json.dumps(sess))
                r.setex(f'web:session:{token}', 3600, enc)
                return { 'token': token, 'ttl': 3600 }
            else:
                raise HTTPException(status_code=401, detail='invalid credentials')
        except Exception:
            raise HTTPException(status_code=500, detail='error reading user')

    # fallback: use WEB_API_KEY as password backend if set
    if WEB_API_KEY and passwd == WEB_API_KEY:
        token = secrets.token_hex(32)
        sess = { 'user': user, 'is_admin': False }
        enc = encrypt_value(json.dumps(sess))
        r.setex(f'web:session:{token}', 3600, enc)
        return { 'token': token, 'ttl': 3600 }
    raise HTTPException(status_code=401, detail='invalid credentials')


@app.post('/auth/register')
def auth_register(payload: dict):
    """Register a new user: payload { user, pass, is_admin (opt) }.
    Stores a salted PBKDF2-SHA256 hash in Redis under `web:user:<user>`.
    """
    if not payload or not payload.get('user') or not payload.get('pass'):
        raise HTTPException(status_code=400, detail='user and pass required')
    user = payload.get('user')
    passwd = payload.get('pass')
    user_key = f'web:user:{user}'
    if r.exists(user_key):
        raise HTTPException(status_code=409, detail='user exists')

    def _hash_password(password: str) -> str:
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return salt.hex() + ':' + dk.hex()

    hashed = _hash_password(passwd)
    obj = { 'pw': hashed, 'created_at': int(time.time()), 'is_admin': bool(payload.get('is_admin', False)) }
    r.set(user_key, json.dumps(obj))
    return { 'status': 'created', 'user': user }


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


@app.get('/status')
def status_info(request: Request):
    """Return basic status information: uptime, current time, redis health and pages."""
    now = int(time.time())
    uptime = now - START_TIME
    redis_status = {'ok': False}
    try:
        # ping and some info
        redis_status['ok'] = bool(r.ping())
        info = r.info()
        redis_status['connected_clients'] = info.get('connected_clients')
        redis_status['used_memory_human'] = info.get('used_memory_human')
    except Exception as e:
        redis_status['error'] = str(e)

    pages = []
    try:
        repo_root = Path(__file__).resolve().parents[2]
        p = repo_root / 'web' / 'pages.json'
        if p.exists():
            pages = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        pages = []

    # gather counts (safe: use scan/llen, avoid exposing secret values)
    counts = {}
    try:
        counts['messages'] = r.llen('web:messages')
    except Exception:
        counts['messages'] = None
    try:
        counts['devices'] = r.llen('web:devices')
    except Exception:
        counts['devices'] = None
    try:
        counts['translation_suggestions'] = r.llen('web:translation:suggestions')
    except Exception:
        counts['translation_suggestions'] = None
    # count users and sessions via scan_iter (may be approximate but safe)
    try:
        users = 0
        for _ in r.scan_iter(match='web:user:*'):
            users += 1
        counts['users'] = users
    except Exception:
        counts['users'] = None
    try:
        sessions = 0
        for _ in r.scan_iter(match='web:session:*'):
            sessions += 1
        counts['sessions'] = sessions
    except Exception:
        counts['sessions'] = None

    # count how many sessions were created via API key (if we can decrypt sessions)
    api_key_sessions = None
    try:
        api_key_sessions = 0
        for k in r.scan_iter(match='web:session:*'):
            v = r.get(k)
            if not v:
                continue
            raw = v.decode() if isinstance(v, bytes) else v
            dec = decrypt_value(raw) if FERNET else None
            if not dec:
                continue
            try:
                obj = json.loads(dec)
            except Exception:
                continue
            if obj and obj.get('user') == 'api_key_user':
                api_key_sessions += 1
    except Exception:
        api_key_sessions = None

    # build list of masked session ids created via API key
    api_key_session_ids = None
    try:
        api_key_session_ids = []
        for k in r.scan_iter(match='web:session:*'):
            keyname = k.decode() if isinstance(k, bytes) else k
            token_part = keyname.split(':',2)[2] if ':' in keyname else keyname
            v = r.get(k)
            if not v:
                continue
            raw = v.decode() if isinstance(v, bytes) else v
            dec = decrypt_value(raw) if FERNET else None
            if not dec:
                continue
            try:
                obj = json.loads(dec)
            except Exception:
                continue
            if obj and obj.get('user') == 'api_key_user':
                t = token_part or ''
                if not t:
                    continue
                if len(t) <= 10:
                    masked = t[:2] + '***' + t[-2:]
                else:
                    masked = t[:6] + '***' + t[-4:]
                api_key_session_ids.append(masked)
    except Exception:
        api_key_session_ids = None

    # include devices list (id and name only) without revealing stored tokens
    devices_list = None
    try:
        devices_list = []
        items = r.lrange('web:devices', 0, -1) or []
        for it in items:
            try:
                obj = json.loads(it.decode() if isinstance(it, bytes) else it)
                devices_list.append({'id': obj.get('id'), 'name': obj.get('name')})
            except Exception:
                continue
    except Exception:
        devices_list = None

    # include TTL (seconds remaining) for sessions created via API key (masked ids)
    api_key_sessions_with_ttl = None
    try:
        api_key_sessions_with_ttl = []
        for k in r.scan_iter(match='web:session:*'):
            keyname = k.decode() if isinstance(k, bytes) else k
            token_part = keyname.split(':',2)[2] if ':' in keyname else keyname
            v = r.get(k)
            if not v:
                continue
            raw = v.decode() if isinstance(v, bytes) else v
            dec = decrypt_value(raw) if FERNET else None
            if not dec:
                continue
            try:
                obj = json.loads(dec)
            except Exception:
                continue
            if obj and obj.get('user') == 'api_key_user':
                ttl = None
                try:
                    ttl_val = r.ttl(k)
                    # redis returns -2 if key missing, -1 if no expire
                    if isinstance(ttl_val, int) and ttl_val >= 0:
                        ttl = int(ttl_val)
                except Exception:
                    ttl = None
                t = token_part or ''
                if not t:
                    continue
                if len(t) <= 10:
                    masked = t[:2] + '***' + t[-2:]
                else:
                    masked = t[:6] + '***' + t[-4:]
                api_key_sessions_with_ttl.append({'id': masked, 'ttl_seconds': ttl})
    except Exception:
        api_key_sessions_with_ttl = None

    # applied translations: count suggestion keys with status == 'applied'
    try:
        applied = 0
        per_lang = {}
        for sid in r.scan_iter(match='web:translation:suggestion:*'):
            try:
                data = r.get(sid)
                if not data:
                    continue
                obj = json.loads(data)
                if obj.get('status') == 'applied':
                    applied += 1
                    lang = obj.get('lang') or 'unknown'
                    per_lang[lang] = per_lang.get(lang, 0) + 1
            except Exception:
                continue
        counts['translation_suggestions_applied'] = applied
        counts['translation_suggestions_applied_per_lang'] = per_lang
    except Exception:
        counts['translation_suggestions_applied'] = None

    api_info = {
        'web_api_key_set': bool(WEB_API_KEY),
        'web_api_origin': WEB_API_ORIGIN or None,
        'bot_token_set': bool(BOT_TOKEN),
    }

    # include masked api key info (never reveal full key)
    try:
        if WEB_API_KEY:
            k = str(WEB_API_KEY)
            # show first 2 and last 2 characters with length
            if len(k) <= 6:
                masked = k[0:1] + '***' + k[-1:]
            else:
                masked = k[0:2] + '***' + k[-2:]
            api_info['web_api_key_masked'] = masked
            api_info['web_api_key_length'] = len(k)
        else:
            api_info['web_api_key_masked'] = None
            api_info['web_api_key_length'] = 0
    except Exception:
        api_info['web_api_key_masked'] = None
        api_info['web_api_key_length'] = None

    api_info['sessions_via_api_key'] = api_key_sessions
    api_info['sessions_via_api_key_ids'] = api_key_session_ids


    supported_endpoints = [
        {'path': '/status', 'method': 'GET', 'desc': 'Server status, uptime, redis and pages'},
        {'path': '/auth/register', 'method': 'POST', 'desc': 'Register a new user (user, pass) stored in Redis'},
        {'path': '/auth/login', 'method': 'POST', 'desc': 'Login using api_key or user/pass, returns session token'},
        {'path': '/translations/suggest', 'method': 'POST', 'desc': 'Submit a translation suggestion'},
        {'path': '/translations/suggestions', 'method': 'GET', 'desc': 'List pending translation suggestions (admin)'},
        {'path': '/translations/apply', 'method': 'POST', 'desc': 'Apply a suggestion to i18n files (admin)'}
    ]

    explanations = {
        'time': 'Current server unix timestamp',
        'uptime': 'Seconds since the server process started',
        'redis.ok': 'Whether Redis responded to a ping',
        'redis.connected_clients': 'Number of clients connected to Redis (if available)',
        'redis.used_memory_human': 'Human-readable Redis memory usage (if available)',
        'counts': 'Counts of items stored in Redis relevant to the web UI',
        'api_info': 'Flags that describe configured API-related settings (do not include secret values)',
        'supported_endpoints': 'Important API endpoints and short descriptions'
    }

    # i18n file stats: file size and number of keys
    i18n_stats = {}
    try:
        repo_root = Path(__file__).resolve().parents[2]
        i18n_dir = repo_root / 'web' / 'i18n'
        if i18n_dir.exists() and i18n_dir.is_dir():
            for p in sorted(i18n_dir.glob('*.json')):
                try:
                    txt = p.read_text(encoding='utf-8')
                    js = json.loads(txt)
                    i18n_stats[p.name] = { 'bytes': p.stat().st_size, 'keys': len(js) }
                except Exception:
                    i18n_stats[p.name] = { 'bytes': None, 'keys': None }
    except Exception:
        i18n_stats = {}

    # try to determine current commit SHA from .git
    git_sha = None
    git_last = None
    try:
        repo_root = Path(__file__).resolve().parents[2]
        head = (repo_root / '.git' / 'HEAD')
        if head.exists():
            htxt = head.read_text(encoding='utf-8').strip()
            if htxt.startswith('ref:'):
                ref = htxt.split(None,1)[1].strip()
                ref_file = repo_root / '.git' / ref
                if ref_file.exists():
                    git_sha = ref_file.read_text(encoding='utf-8').strip()
                else:
                    # try packed-refs
                    packed = repo_root / '.git' / 'packed-refs'
                    if packed.exists():
                        for line in packed.read_text(encoding='utf-8').splitlines():
                            if line.startswith('#') or not line.strip():
                                continue
                            parts = line.split()
                            if len(parts) == 2 and parts[1] == ref:
                                git_sha = parts[0]
                                break
            else:
                # HEAD contains SHA directly
                git_sha = htxt
        # try to get last commit author/message from logs if available
        logs = repo_root / '.git' / 'logs' / 'HEAD'
        if logs.exists():
            try:
                last = logs.read_text(encoding='utf-8').strip().splitlines()[-1]
                # format: <oldsha> <newsha> <author>\t<message>
                parts = last.split('\t')
                msg = parts[1] if len(parts) > 1 else ''
                pre = parts[0].split()
                # pre contains oldsha newsha and author+timestamp
                oldsha = pre[0] if len(pre) > 0 else None
                newsha = pre[1] if len(pre) > 1 else None
                author = ' '.join(pre[2:]) if len(pre) > 2 else None
                git_last = { 'sha': newsha or git_sha, 'author': author, 'message': msg }
            except Exception:
                git_last = None
    except Exception:
        git_sha = None

    # include new fields in explanations
    explanations['counts.translation_suggestions_applied'] = 'Number of translation suggestions that have been applied'
    explanations['i18n_stats'] = 'Per-language i18n JSON file size and number of keys'
    explanations['git_sha'] = 'Current commit SHA read from .git (if available)'

    # TDLib status: attempt to inspect tdlib_router module for client and ws state
    tdlib_status = { 'available': False }
    try:
        import importlib
        tdmod = importlib.import_module('python_api.app.tdlib_router')
        tdlib_status['available'] = True
        _td = getattr(tdmod, '_td_client', None)
        tdlib_status['client_present'] = bool(_td)
        if _td is not None:
            try:
                tdlib_status['client_type'] = type(_td).__name__
            except Exception:
                tdlib_status['client_type'] = None
            try:
                tdlib_status['client_running'] = bool(getattr(_td, '_running', False))
            except Exception:
                tdlib_status['client_running'] = None
        # websocket manager active connections
        try:
            ws_mgr = getattr(tdmod, 'ws_mgr', None)
            tdlib_status['ws_connections'] = len(getattr(ws_mgr, 'active', [])) if ws_mgr is not None else 0
        except Exception:
            tdlib_status['ws_connections'] = None
        # auth flow stored in redis (if present)
        try:
            auth_raw = r.get('tdlib:auth')
            if auth_raw:
                try:
                    auth_obj = json.loads(auth_raw)
                except Exception:
                    auth_obj = None
                if auth_obj:
                    masked = dict(auth_obj)
                    if 'code' in masked:
                        masked['code'] = '*****'
                    tdlib_status['auth'] = masked
                else:
                    tdlib_status['auth'] = None
            else:
                tdlib_status['auth'] = None
        except Exception:
            tdlib_status['auth'] = None
        # recent events count and last item
        try:
            ev_count = r.llen('tdlib:events')
            tdlib_status['events_count'] = ev_count
            last = r.lindex('tdlib:events', 0)
            if last:
                try:
                    if isinstance(last, bytes):
                        s = last.decode()
                    else:
                        s = last
                    tdlib_status['last_event'] = json.loads(s) if s and s[0] in '{["' else s
                except Exception:
                    tdlib_status['last_event'] = str(last)
            else:
                tdlib_status['last_event'] = None
        except Exception:
            tdlib_status['events_count'] = None
            tdlib_status['last_event'] = None
    except Exception:
        tdlib_status = { 'available': False }

    return {
        'status': 'ok',
        'time': now,
        'uptime': uptime,
        'redis': redis_status,
        'counts': counts,
        'api_info': api_info,
        'supported_endpoints': supported_endpoints,
        'pages': pages,
        'i18n_stats': i18n_stats,
        'git_sha': git_sha,
        'git_last': git_last,
        'processes': [ process_status(n) for n in PROCESS_DEFS.keys() ],
        'tdlib': tdlib_status,
        'explanations': explanations
    }


# Finally, mount the web/ static files so API routes are registered first
try:
    repo_root = Path(__file__).resolve().parents[2]
    web_dir = repo_root / 'web'
    if web_dir.exists():
        app.mount('/', StaticFiles(directory=str(web_dir), html=True), name='web')
except Exception:
    pass
