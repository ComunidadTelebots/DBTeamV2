from fastapi import FastAPI
app = FastAPI()
from fastapi.responses import RedirectResponse

# Redirección de la raíz a index.html
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/index.html")
from fastapi import Request
# Estado de traducciones aplicadas (para owner)
from fastapi import HTTPException
import json
@app.get('/translations/applied')
def get_applied_translations(request: Request):
    # Solo owner puede ver traducciones aplicadas
    sess = None
    try:
        if hasattr(request, 'session'):
            sess = request.session
        else:
            # Intentar obtener sesión por header
            auth = request.headers.get('authorization')
            if auth and auth.lower().startswith('bearer '):
                token = auth.split(None, 1)[1]
                v = r.get(f'web:session:{token}')
                if v:
                    dec = v.decode() if isinstance(v, bytes) else v
                    try:
                        sess = json.loads(dec)
                    except Exception:
                        pass
    except Exception:
        sess = None
    if not sess or not sess.get('is_owner'):
        raise HTTPException(status_code=403, detail='Solo owner puede ver traducciones aplicadas')
    out = []
    for m in r.lrange('web:applied_translations', 0, -1) or []:
        try:
            obj = json.loads(m)
            out.append(obj)
        except Exception:
            continue
    return { 'translations': out[-50:] }
from fastapi import Request
from .config import BOT_TOKEN, WEB_API_KEY, WEB_API_SECRET, WEB_API_ORIGIN, REDIS_URL
from fastapi import FastAPI
from pathlib import Path
import logging
app = FastAPI()
logging.basicConfig(level=logging.INFO)
try:
    import redis
    r = redis.from_url(REDIS_URL)
    r.ping()
    logging.info(f"[DBTeamV2] Redis conectado correctamente: {REDIS_URL}")
except Exception as e:
    logging.error(f"[DBTeamV2] Error conectando a Redis: {e}")
from .config import BOT_TOKEN, WEB_API_KEY, WEB_API_SECRET, WEB_API_ORIGIN, REDIS_URL
# --- Endpoints para gestión de traducciones aplicadas ---
@app.get('/translations/applied')
def get_applied_translations(request: Request):
    sess = request.session if hasattr(request, 'session') else None
    if not sess or not sess.get('is_owner'):
        raise HTTPException(status_code=403, detail='Solo owner puede ver traducciones aplicadas')
    out = []
    for m in r.lrange('web:applied_translations', 0, -1) or []:
        try:
            obj = json.loads(m)
            out.append(obj)
        except Exception:
            continue
    return { 'translations': out[-50:] }

@app.post('/translations/reject')
def reject_translation(payload: dict, request: Request):
    sess = request.session if hasattr(request, 'session') else None
    if not sess or not sess.get('is_owner'):
        raise HTTPException(status_code=403, detail='Solo owner puede rechazar traducciones')
    tid = payload.get('id')
    if not tid:
        raise HTTPException(status_code=400, detail='ID requerido')
    items = r.lrange('web:applied_translations', 0, -1) or []
    new_items = [m for m in items if not (json.loads(m).get('id') == tid)]
    r.delete('web:applied_translations')
    for m in new_items:
        r.rpush('web:applied_translations', m)
    return { 'status': 'rejected' }
# --- Endpoint para enviar traducción por Telegram ---
@app.post('/translations/send_telegram')
def send_translation_telegram(payload: dict, request: Request):
    sess = request.session if hasattr(request, 'session') else None
    if not sess or not sess.get('is_trans_admin'):
        raise HTTPException(status_code=403, detail='Solo admin de traducciones puede enviar')
    txt = payload.get('text')
    mode = payload.get('mode', 'group')
    user = payload.get('user', '').strip()
    if not txt:
        raise HTTPException(status_code=400, detail='Texto requerido')
    token = os.environ.get('BOT_TOKEN', None) or BOT_TOKEN
    if mode == 'private':
        if not user or not user.startswith('@'):
            raise HTTPException(status_code=400, detail='Usuario Telegram inválido')
        # Obtener el user_id por username (requiere método extra si no está en caché)
        # Aquí se asume que el bot puede enviar por username
        chat_id = user
    else:
        chat_id = os.environ.get('TRANSLATION_TELEGRAM_ID', None) or '-100123456789'
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    body = { 'chat_id': chat_id, 'text': f"Traducción enviada: {txt}" }
    resp = requests.post(url, json=body)
    if not resp.ok:
        raise HTTPException(status_code=500, detail=resp.text)
    return { 'status': 'sent' }
# --- Endpoints de notificación manual minichat ---
@app.post('/mini_chat/notify_telegram')
def mini_chat_notify_telegram(payload: dict, request: Request):
    sess = request.session if hasattr(request, 'session') else None
    if not sess or not sess.get('is_admin'):
        raise HTTPException(status_code=403, detail='Solo admin puede notificar')
    txt = payload.get('text')
    if not txt:
        raise HTTPException(status_code=400, detail='Texto requerido')
    # Enviar mensaje por Telegram al creador
    creator_chat_id = os.environ.get('CREATOR_TELEGRAM_ID', None) or '-100123456789'  # Cambia por el chat real
    token = os.environ.get('BOT_TOKEN', None) or BOT_TOKEN
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    body = { 'chat_id': creator_chat_id, 'text': f"Mensaje minichat: {txt}" }
    resp = requests.post(url, json=body)
    if not resp.ok:
        raise HTTPException(status_code=500, detail=resp.text)
    return { 'status': 'notified' }

@app.post('/mini_chat/notify_email')
def mini_chat_notify_email(payload: dict, request: Request):
    sess = request.session if hasattr(request, 'session') else None
    if not sess or not sess.get('is_admin'):
        raise HTTPException(status_code=403, detail='Solo admin puede notificar')
    txt = payload.get('text')
    if not txt:
        raise HTTPException(status_code=400, detail='Texto requerido')
    # Enviar email al creador (ajusta email y método)
    import smtplib
    from email.mime.text import MIMEText
    creator_email = os.environ.get('CREATOR_EMAIL', None) or 'admin@tudominio.com'
    msg = MIMEText(f"Mensaje minichat: {txt}")
    msg['Subject'] = 'Nuevo mensaje minichat DBTeam'
    msg['From'] = 'noreply@tudominio.com'
    msg['To'] = creator_email
    try:
        s = smtplib.SMTP('localhost')
        s.sendmail(msg['From'], [creator_email], msg.as_string())
        s.quit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return { 'status': 'notified' }
# --- Endpoints minichat admin-creador ---
@app.get('/mini_chat/messages')
def mini_chat_messages(request: Request):
    sess = request.session if hasattr(request, 'session') else None
    if not sess or not sess.get('is_admin'):
        raise HTTPException(status_code=403, detail='Solo admin puede ver el chat')
    msgs = []
    for m in r.lrange('web:mini_chat', 0, -1) or []:
        try:
            obj = json.loads(m)
            msgs.append(obj)
        except Exception:
            continue
    return { 'messages': msgs[-40:] }

@app.post('/mini_chat/send')
def mini_chat_send(payload: dict, request: Request):
    sess = request.session if hasattr(request, 'session') else None
    if not sess or not sess.get('is_admin'):
        raise HTTPException(status_code=403, detail='Solo admin puede enviar mensajes')
    txt = payload.get('text')
    if not txt:
        raise HTTPException(status_code=400, detail='Texto requerido')
    msg = { 'from': sess.get('user'), 'text': txt, 'ts': int(time.time()) }
    r.rpush('web:mini_chat', json.dumps(msg))
    # Opcional: notificar al creador por Telegram, email, etc.
    return { 'status': 'sent' }
# --- Solicitudes de admin de traducciones ---
from fastapi import Request, HTTPException
import uuid

def is_owner_request(request: Request) -> bool:
    sess = request.session if hasattr(request, 'session') else None
    return bool(sess and sess.get('is_owner'))

@app.post('/trans_admin/request')
def request_trans_admin(payload: dict, request: Request):
    """Solicita crear un nuevo admin de traducciones. Solo admins de traducciones pueden solicitar."""
    sess = request.session if hasattr(request, 'session') else None
    if not sess or not sess.get('is_trans_admin'):
        raise HTTPException(status_code=403, detail='Solo admin de traducciones puede solicitar')
    user = payload.get('user')
    pw = payload.get('pass')
    if not user or not pw:
        raise HTTPException(status_code=400, detail='user y pass requeridos')
    req_id = str(uuid.uuid4())
    obj = { 'id': req_id, 'user': user, 'pass': pw, 'by': sess.get('user'), 'ts': int(time.time()), 'status': 'pending' }
    r.hset('web:trans_admin_requests', req_id, json.dumps(obj))
    return { 'status': 'pending', 'id': req_id }

@app.get('/trans_admin/requests')
def list_trans_admin_requests(request: Request):
    """Lista solicitudes pendientes de admin de traducciones. Solo owner puede verlas."""
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo owner puede ver solicitudes')
    out = []
    for k, v in (r.hgetall('web:trans_admin_requests') or {}).items():
        try:
            obj = json.loads(v)
            out.append(obj)
        except Exception:
            continue
    return { 'requests': out }

@app.post('/trans_admin/approve')
def approve_trans_admin(payload: dict, request: Request):
    """Aprueba o rechaza una solicitud de admin de traducciones. Solo owner puede aprobar/rechazar."""
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo owner puede aprobar')
    req_id = payload.get('id')
    approve = bool(payload.get('approve'))
    v = r.hget('web:trans_admin_requests', req_id)
    if not v:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')
    obj = json.loads(v)
    if obj.get('status') != 'pending':
        raise HTTPException(status_code=409, detail='Ya procesada')
    if approve:
        # Crear el usuario como admin de traducciones
        user_key = f'web:user:{obj["user"]}'
        if r.exists(user_key):
            obj['status'] = 'rejected'
            r.hset('web:trans_admin_requests', req_id, json.dumps(obj))
            return { 'status': 'rejected', 'reason': 'Usuario ya existe' }
        def hash_password(password: str) -> str:
            import secrets, hashlib
            salt = secrets.token_bytes(16)
            dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
            return salt.hex() + ':' + dk.hex()
        hashed = hash_password(obj['pass'])
        user_obj = { 'pw': hashed, 'created_at': int(time.time()), 'is_admin': False, 'is_trans_admin': True }
        r.set(user_key, json.dumps(user_obj))
        obj['status'] = 'approved'
        r.hset('web:trans_admin_requests', req_id, json.dumps(obj))
        return { 'status': 'approved', 'user': obj['user'] }
    else:
        obj['status'] = 'rejected'
        r.hset('web:trans_admin_requests', req_id, json.dumps(obj))
        return { 'status': 'rejected' }
# Endpoint para crear administradores desde la web
@app.post('/admin/create')
def admin_create(payload: dict, request: Request):
    if not is_owner_request(request):
        return JSONResponse({'error': 'Unauthorized'}, status_code=403)
    user = (payload.get('user') or '').strip()
    passwd = (payload.get('pass') or '')
    if not user or not passwd:
        return JSONResponse({'error': 'Usuario y contraseña requeridos'}, status_code=400)
    # Guardar en Redis como admin
    key = f'web:admin:{user.lower()}'
    obj = { 'user': user, 'pass': passwd, 'is_admin': True }
    r.set(key, json.dumps(obj))
    return { 'status': 'ok', 'user': user }


# Endpoints para gestionar usuarios desde el panel Owner
@app.get('/admin/users')
def admin_list_users(request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo owner')
    out = []
    try:
        for k in r.scan_iter(match='web:user:*'):
            try:
                v = r.get(k)
                if not v:
                    continue
                s = v.decode() if isinstance(v, bytes) else v
                obj = json.loads(s)
                name = k.decode().split(':', 2)[-1] if isinstance(k, bytes) else k.split(':', 2)[-1]
                out.append({ 'user': name, 'created_at': obj.get('created_at'), 'is_admin': bool(obj.get('is_admin')), 'is_trans_admin': bool(obj.get('is_trans_admin', False)), 'is_translator': bool(obj.get('is_translator', False)), 'is_publisher': bool(obj.get('is_publisher', False)) })
            except Exception:
                continue
    except Exception:
        raise HTTPException(status_code=500, detail='error listing users')
    return { 'users': out }


@app.post('/admin/users')
def admin_create_user(payload: dict, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo owner')
    if not payload or not payload.get('user') or not payload.get('pass'):
        raise HTTPException(status_code=400, detail='user and pass required')
    user = (payload.get('user') or '').strip()
    passwd = payload.get('pass')
    if not user:
        raise HTTPException(status_code=400, detail='user required')

    user_key = f'web:user:{user}'
    if r.exists(user_key):
        raise HTTPException(status_code=409, detail='user exists')

    def _hash_password(password: str) -> str:
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return salt.hex() + ':' + dk.hex()

    hashed = _hash_password(passwd)
    # Normalize trans_perms: accept list or dict
    perms = payload.get('trans_perms', {})
    def normalize_perms(p):
        if isinstance(p, list):
            return { str(x): True for x in p }
        if isinstance(p, dict):
            out = {}
            for kk, vv in p.items():
                k = str(kk)
                if isinstance(vv, dict):
                    # nested components map
                    out[k] = { str(ck): bool(cv) for ck, cv in vv.items() }
                elif isinstance(vv, list):
                    out[k] = { str(x): True for x in vv }
                else:
                    out[k] = bool(vv)
            return out
        return {}
    perms = normalize_perms(perms)

    obj = {
        'pw': hashed,
        'created_at': int(time.time()),
        'is_admin': bool(payload.get('is_admin', False)),
        'is_trans_admin': bool(payload.get('is_trans_admin', False)),
        'is_translator': bool(payload.get('is_translator', False)),
        'is_publisher': bool(payload.get('is_publisher', False)),
        'trans_perms': perms
    }
    r.set(user_key, json.dumps(obj))
    return { 'status': 'created', 'user': user }


@app.post('/admin/users/reset')
def admin_reset_user(payload: dict, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo owner')
    user = payload.get('user') if payload else None
    passwd = payload.get('pass') if payload else None
    if not user or not passwd:
        raise HTTPException(status_code=400, detail='user and pass required')
    user_key = f'web:user:{user}'
    if not r.exists(user_key):
        raise HTTPException(status_code=404, detail='user not found')

    def _hash_password(password: str) -> str:
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return salt.hex() + ':' + dk.hex()

    hashed = _hash_password(passwd)
    try:
        raw = r.get(user_key)
        obj = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        obj['pw'] = hashed
        r.set(user_key, json.dumps(obj))
    except Exception:
        raise HTTPException(status_code=500, detail='error resetting password')
    return { 'status': 'ok' }


@app.delete('/admin/users/{user}')
def admin_delete_user(user: str, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo owner')
    user_key = f'web:user:{user}'
    if not r.exists(user_key):
        raise HTTPException(status_code=404, detail='user not found')
    try:
        r.delete(user_key)
    except Exception:
        raise HTTPException(status_code=500, detail='error deleting user')
# Return deletion result
    return { 'status': 'deleted', 'user': user }


@app.post('/admin/users/{user}/trans_perms')
def admin_set_trans_perms(user: str, payload: dict, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo owner')
    user_key = f'web:user:{user}'
    if not r.exists(user_key):
        raise HTTPException(status_code=404, detail='user not found')
    try:
        raw = r.get(user_key)
        obj = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        perms = payload.get('trans_perms', {})
        def normalize(p):
            if isinstance(p, list):
                return { str(x): True for x in p }
            if isinstance(p, dict):
                out = {}
                for kk, vv in p.items():
                    k = str(kk)
                    if isinstance(vv, dict):
                        out[k] = { str(ck): bool(cv) for ck, cv in vv.items() }
                    elif isinstance(vv, list):
                        out[k] = { str(x): True for x in vv }
                    else:
                        out[k] = bool(vv)
                return out
            return {}
        perms = normalize(perms)
        obj['trans_perms'] = perms
        r.set(user_key, json.dumps(obj))
    except Exception:
        raise HTTPException(status_code=500, detail='error setting trans perms')
    return { 'ok': True }


@app.get('/admin/users/{user}/trans_perms')
def admin_get_trans_perms(user: str, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo owner')
    user_key = f'web:user:{user}'
    if not r.exists(user_key):
        raise HTTPException(status_code=404, detail='user not found')
    try:
        raw = r.get(user_key)
        obj = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        return { 'trans_perms': obj.get('trans_perms', {}) }
    except Exception:
        raise HTTPException(status_code=500, detail='error getting trans perms')

# --- Middleware global para control de IP y auditoría de accesos ---
from fastapi.responses import JSONResponse
@app.middleware('http')
async def ip_whitelist_and_audit(request: Request, call_next):
    allowed = {'127.0.0.1', '::1', '192.168.1.1'} # Personaliza según tu red
    ip = request.client.host if request and request.client else None
    user = None
    try:
        user = get_session_from_request(request)
    except Exception:
        user = None
    path = request.url.path
    # Registrar acceso en el log de auditoría
    try:
        from pathlib import Path
        import time
        _audit_log_path = Path(__file__).resolve().parents[2] / 'logs' / 'lang_audit.log'
        _audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(_audit_log_path, 'a', encoding='utf-8') as f:
            ts = int(time.time())
            f.write(f"{ts}|ACCESS|{(user.get('username') if user else '-')}|{ip}|{path}\n")
    except Exception:
        pass
    if ip not in allowed:
        return JSONResponse({'error': 'IP no autorizada'}, status_code=403)
    response = await call_next(request)
    return response
# Auditoría de acciones sensibles
import threading
_audit_lock = threading.Lock()
_audit_log_path = Path(__file__).resolve().parents[2] / 'logs' / 'lang_audit.log'
def log_lang_action(action, user, ip):
    with _audit_lock:
        try:
            _audit_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(_audit_log_path, 'a', encoding='utf-8') as f:
                ts = int(time.time())
                f.write(f"{ts}|{action}|{user}|{ip}\n")
        except Exception:
            pass

def get_audit_logs():
    logs = []
    if not _audit_log_path.exists():
        return logs
    with open(_audit_log_path, encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) == 4:
                ts, action, user, ip = parts
                logs.append({ 'ts': int(ts), 'action': action, 'user': user, 'ip': ip })
            elif len(parts) == 5:
                ts, action, user, ip, path = parts
                logs.append({ 'ts': int(ts), 'action': action, 'user': user, 'ip': ip, 'path': path })
    return logs[::-1][:100]

@app.get('/audit/lang_actions')
def audit_lang_actions(request: Request):
    if not is_owner_request(request):
        return JSONResponse({'error': 'Unauthorized'}, status_code=403)
    return get_audit_logs()
# Endpoint para listar idiomas disponibles en un scope
@app.get('/i18n/list/{scope}')
def is_owner_request(request: Request) -> bool:
    # Puedes mejorar esto con tu lógica de owner/admin
    user = get_session_from_request(request)
    return user and (user.get('is_owner') or user.get('is_admin'))

def allowed_ip(request: Request) -> bool:
    # Whitelist de IPs permitidas (puedes personalizar)
    allowed = {'127.0.0.1', '::1', '192.168.1.1'}
    ip = request.client.host if request and request.client else None
    return ip in allowed

@app.get('/i18n/list/{scope}')
def list_langs(scope: str, request: Request):
    user = get_session_from_request(request)
    ip = request.client.host if request and request.client else '-'
    if not is_owner_request(request) or not allowed_ip(request):
        log_lang_action('DENIED_LIST', user.get('username') if user else '-', ip)
        return JSONResponse({'error': 'Unauthorized'}, status_code=403)
    repo_root = Path(__file__).resolve().parents[2]
    i18n_dir = repo_root / 'web' / 'i18n' / scope
    if not i18n_dir.exists():
        return []
    langs = []
    for f in i18n_dir.glob('*.json'):
        code = f.stem.lower()
        if code.isalpha() and 2 <= len(code) <= 5:
            langs.append(code)
    log_lang_action('LIST', user.get('username') if user else '-', ip)
    return sorted(langs)
# Endpoint para crear un nuevo archivo de idioma (bot o web)
from fastapi import Body
@app.post('/translations/create_lang')
def create_lang(payload: dict = Body(...), request: Request = None):
    user = get_session_from_request(request)
    ip = request.client.host if request and request.client else '-'
    if not is_owner_request(request) or not allowed_ip(request):
        log_lang_action('DENIED_CREATE', user.get('username') if user else '-', ip)
        return JSONResponse({'error': 'Unauthorized'}, status_code=403)
    lang = (payload.get('lang') or '').strip().lower()
    scope = (payload.get('scope') or 'bot').strip().lower()
    if not lang or not lang.isalpha() or not (2 <= len(lang) <= 5):
        return JSONResponse({'error': 'Código de idioma inválido'}, status_code=400)
    repo_root = Path(__file__).resolve().parents[2]
    i18n_dir = repo_root / 'web' / 'i18n' / scope
    i18n_dir.mkdir(parents=True, exist_ok=True)
    lang_file = i18n_dir / f"{lang}.json"
    if lang_file.exists():
        return JSONResponse({'error': 'El archivo ya existe'}, status_code=409)
    base_file = i18n_dir / 'en.json'
    if base_file.exists():
        import shutil
        shutil.copy(str(base_file), str(lang_file))
    else:
        lang_file.write_text(json.dumps({"_note": "Traducción inicial generada"}, ensure_ascii=False, indent=2), encoding='utf-8')
    log_lang_action('CREATE', user.get('username') if user else '-', ip)
    return { 'status': 'ok', 'file': str(lang_file) }
from fastapi import APIRouter
router = APIRouter()

import os
# --- Endpoint para obtener datos de bot Telegram por token ---
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post('/api/get_telegram_bot_info')
async def get_telegram_bot_info(request: Request):
    data = await request.json()
    token = data.get('token', '').strip()
    if not token:
        return JSONResponse({'ok': False, 'error': 'Token requerido'}, status_code=400)
    try:
        url = f'https://api.telegram.org/bot{token}/getMe'
        resp = requests.get(url)
        if not resp.ok:
            # Detectar si el bot está bloqueado por la API
            if resp.status_code == 403 or 'blocked' in resp.text.lower():
                return JSONResponse({'ok': False, 'blocked': True, 'error': 'El bot ha sido bloqueado por la API de Telegram.'}, status_code=403)
            return JSONResponse({'ok': False, 'error': 'No se pudo consultar Telegram'}, status_code=400)
        info = resp.json().get('result', {})
        # Avatar: getUserProfilePhotos
        avatar_url = ''
        try:
            photos_url = f'https://api.telegram.org/bot{token}/getUserProfilePhotos?user_id={info.get("id")}&limit=1'
            photos_resp = requests.get(photos_url)
            if photos_resp.ok:
                photos = photos_resp.json().get('result', {}).get('photos', [])
                if photos and photos[0]:
                    # Get file_id
                    file_id = photos[0][0].get('file_id')
                    # Get file path
                    file_resp = requests.get(f'https://api.telegram.org/bot{token}/getFile?file_id={file_id}')
                    if file_resp.ok:
                        file_path = file_resp.json().get('result', {}).get('file_path')
                        if file_path:
                            avatar_url = f'https://api.telegram.org/file/bot{token}/{file_path}'
        except Exception:
            pass
        return JSONResponse({
            'ok': True,
            'name': info.get('first_name', '') + ((' ' + info.get('last_name', '')) if info.get('last_name') else ''),
            'username': info.get('username', ''),
            'id': info.get('id', ''),
            'avatar': avatar_url,
            'status': 'Activo'
        })
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)
# --- Endpoints para bots de usuario ---
import json
USER_BOTS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'user_bots.json')

def read_user_bots():
    try:
        with open(USER_BOTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def write_user_bots(bots):
    try:
        with open(USER_BOTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(bots, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

@app.get('/api/get_user_bots')
async def get_user_bots():
    bots = read_user_bots()
    return JSONResponse({'bots': bots})

@app.post('/api/set_user_bots')
async def set_user_bots(request: Request):
    data = await request.json()
    bots = data.get('bots', [])
    ok = write_user_bots(bots)
    return JSONResponse({'success': ok})
# --- Endpoint ejemplo: grupos y usuarios activos en vivo ---

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get('/api/live_groups_users')
async def live_groups_users():
    # Simulación: datos de ejemplo
    groups = [
        {'id': '-100123456789', 'name': 'Grupo Principal', 'status': 'activo'},
        {'id': '-100987654321', 'name': 'Grupo Afiliado', 'status': 'activo'}
    ]
    users = [
        {'id': '123456', 'name': 'Owner', 'username': 'owneruser', 'status': 'online'},
        {'id': '654321', 'name': 'Afiliado', 'username': 'afiliado1', 'status': 'online'}
    ]
    return JSONResponse({'groups': groups, 'users': users})
@router.get('/ownerlock/tgchannel')
async def get_tg_channel():
    tg_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'tg_notify_channel.txt')
    channel = ''
    if os.path.exists(tg_path):
        with open(tg_path, 'r', encoding='utf-8') as f:
            channel = f.read().strip()
    return { 'channel': channel }
@router.post('/ownerlock/tgchannel')
async def set_tg_channel(request: Request):
    data = await request.json()
    channel = str(data.get('channel', '')).strip()
    user_id = str(data.get('user_id', ''))
    tg_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'tg_notify_channel.txt')
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        return JSONResponse({'ok': False, 'error': 'BOT_TOKEN no configurado'}, status_code=400)
    # Check bot is admin in channel
    import requests
    try:
        url = f'https://api.telegram.org/bot{bot_token}/getChatAdministrators?chat_id={channel}'
        resp = requests.get(url)
        if not resp.ok:
            return JSONResponse({'ok': False, 'error': 'No se pudo consultar administradores del canal'}, status_code=400)
        admins = resp.json().get('result', [])
        bot_is_admin = False
        user_is_admin = False
        for adm in admins:
            if adm.get('user', {}).get('is_bot') and adm.get('user', {}).get('username'):
                if adm['user']['username'].lower() == os.getenv('BOT_USERNAME', '').lower():
                    bot_is_admin = True
            if user_id and str(adm.get('user', {}).get('id')) == user_id:
                user_is_admin = True
        if not bot_is_admin:
            return JSONResponse({'ok': False, 'error': 'El bot no es administrador del canal. Agrégalo y vuelve a intentar.'}, status_code=400)
        if not user_is_admin:
            return JSONResponse({'ok': False, 'error': 'Solo el dueño o administrador del canal puede configurar esto.'}, status_code=403)
        with open(tg_path, 'w', encoding='utf-8') as f:
            f.write(channel)
        return JSONResponse({'ok': True, 'channel': channel})
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)
@router.get('/ownerlock/groups')
async def ownerlock_groups():
    group_lock_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'group_lock.flag')
    groups = []
    if os.path.exists(group_lock_path):
        with open(group_lock_path, 'r') as f:
            groups = [line.strip() for line in f if line.strip()]
    return { 'groups': groups }

@router.post('/ownerlock/groups/toggle')
async def ownerlock_groups_toggle(request: Request):
    group_lock_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'group_lock.flag')
    data = await request.json()
    group_id = str(data.get('group_id'))
    lock = bool(data.get('lock', False))
    groups = set()
    if os.path.exists(group_lock_path):
        with open(group_lock_path, 'r') as f:
            groups = set(line.strip() for line in f if line.strip())
    if lock:
        groups.add(group_id)
    else:
        groups.discard(group_id)
    with open(group_lock_path, 'w') as f:
        for gid in groups:
            f.write(str(gid)+'\n')
    return { 'groups': list(groups) }

@router.post('/ownerlock/groups/leave')
async def ownerlock_groups_leave(request: Request):
    # This should trigger the bot to leave the group via Telegram API (requires bot integration)
    # For now, just return success; actual leave logic should be handled by the bot process
    data = await request.json()
    group_id = str(data.get('group_id'))
    # IPC: append group_id to leave queue file for bot to process
    leave_queue_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'leave_group_queue.txt')
    try:
        with open(leave_queue_path, 'a') as f:
            f.write(str(group_id)+'\n')
    except Exception:
        pass
    return JSONResponse({'left': group_id})
OWNERLOCK_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'ownerlock.flag')
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
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
# from .config import BOT_TOKEN, WEB_API_KEY, WEB_API_SECRET, WEB_API_ORIGIN, REDIS_URL

r = redis.from_url(REDIS_URL)
app = FastAPI()
r = redis.from_url(REDIS_URL)
r = redis.from_url(REDIS_URL)
app.include_router(router)
r = redis.from_url(REDIS_URL)

# --- Main/Affiliate Channels Backend ---
MAIN_CHANNEL_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'main_channel.txt')
AFFILIATE_CHANNELS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'affiliate_channels.txt')

def read_file_safe(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ''

def write_file_safe(path, content):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content.strip())
        return True
    except Exception:
        return False

@app.post('/api/set_main_channel')
async def set_main_channel(request: Request):
    data = await request.json()
    channel = data.get('channel', '').strip()
    ok = write_file_safe(MAIN_CHANNEL_FILE, channel)
    return JSONResponse({'success': ok})

@app.get('/api/get_main_channel')
async def get_main_channel():
    channel = read_file_safe(MAIN_CHANNEL_FILE)
    return JSONResponse({'channel': channel})

@app.post('/api/set_affiliate_channels')
async def set_affiliate_channels(request: Request):
    data = await request.json()
    channels = data.get('channels', '').strip()
    ok = write_file_safe(AFFILIATE_CHANNELS_FILE, channels)
    return JSONResponse({'success': ok})

@app.get('/api/get_affiliate_channels')
async def get_affiliate_channels():
    channels = read_file_safe(AFFILIATE_CHANNELS_FILE)
    return JSONResponse({'channels': channels})

# server start time for uptime reporting
START_TIME = int(time.time())

# Note: static files will be mounted at the end of this module so API routes
# (including /tdlib) are registered first and not shadowed by StaticFiles.

# Include tdlib router (scaffold). If import fails, register a JSON fallback
TDLIB_AVAILABLE = True
try:
#     from .tdlib_router import router as tdlib_router
    # app.include_router(tdlib_router, prefix='/tdlib')
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
            token_part = keyname.split(':', 2)[2] if ':' in keyname else keyname
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
            if obj and obj.get('user') != 'api_key_user':
                continue
            ttl = None
            try:
                ttl_val = r.ttl(k)
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

from fastapi import BackgroundTasks

@app.post('/run_setup_windows')
def run_setup_windows(background_tasks: BackgroundTasks):
    import subprocess
    try:
        background_tasks.add_task(subprocess.Popen, ["powershell", "./quick_setup_windows.ps1"], shell=True)
        return { 'status': 'started' }
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)

@app.post('/run_setup_ubuntu')
def run_setup_ubuntu(background_tasks: BackgroundTasks):
    import subprocess
    try:
        background_tasks.add_task(subprocess.Popen, ["bash", "./scripts/setup_ubuntu.sh"], shell=True)
        return { 'status': 'started' }
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)

@app.post('/create_owner')
def create_owner(payload: dict):
    """Crea el usuario owner si no existe."""
    user = (payload.get('user') or '').strip()
    passwd = (payload.get('pass') or '')
    if not user or not passwd:
        return JSONResponse({'detail': 'Usuario y contraseña requeridos'}, status_code=400)
    user_key = f'web:user:{user}'
    if r.exists(user_key):
        return JSONResponse({'detail': 'El usuario ya existe'}, status_code=409)
    def _hash_password(password: str) -> str:
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return salt.hex() + ':' + dk.hex()
    hashed = _hash_password(passwd)
    obj = { 'pw': hashed, 'created_at': int(time.time()), 'is_owner': True, 'is_admin': True }
    r.set(user_key, json.dumps(obj))
    return { 'status': 'created', 'user': user }
