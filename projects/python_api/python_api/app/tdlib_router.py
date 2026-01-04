from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from .. import config
from ..tdlib_client import get_client, TDLibNotAvailable
import asyncio
import json
import redis
import os
import uuid
import time
from pathlib import Path

router = APIRouter()

# single global client for simplicity
_td_client = None


@router.post('/connect')
def connect_tdlib(payload: dict = None, request: Request = None):
    global _td_client
    prefer_dummy = payload.get('dummy', False) if payload else False
    # Si es build de GitHub, no permitir uso de tokens oficiales
    if os.getenv('GITHUB_BUILD') == '1':
        return {
            'status': 'github_demo',
            'message': 'No se pueden usar funciones con tokens oficiales en esta build. Ejemplo de respuesta:',
            'example': {
                'user': 'demo',
                'actions': ['enviar mensaje', 'consultar estado'],
                'result': 'ok (simulado)'
            }
        }
    try:
        _td_client = get_client(prefer_dummy=prefer_dummy)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    try:
        _td_client.start()
        if hasattr(_td_client, 'set_event_handler'):
            try:
                _r = redis.from_url(config.REDIS_URL)
            except Exception:
                _r = None
            def _on_event(ev):
                try:
                    msg = ev if isinstance(ev, (str, bytes)) else json.dumps(ev, default=str)
                except Exception:
                    msg = str(ev)
                try:
                    asyncio.get_event_loop().create_task(ws_mgr.broadcast(msg))
                except Exception:
                    try:
                        asyncio.run(ws_mgr.broadcast(msg))
                    except Exception:
                        pass
                try:
                    if _r is not None:
                        _r.lpush('tdlib:events', msg)
                        _r.ltrim('tdlib:events', 0, 999)
                except Exception:
                    pass
            try:
                _td_client.set_event_handler(_on_event)
            except Exception:
                pass
    except Exception:
        pass
    return { 'status': 'started', 'dummy': prefer_dummy }


@router.post('/auth/start')
def auth_start(payload: dict):
    """Start an auth flow. Payload: { phone: '+1234...' }.
    This will store a short code in Redis (or a temp file) for verification.
    """
    phone = (payload or {}).get('phone')
    if not phone:
        raise HTTPException(status_code=400, detail='phone required')
    code = '12345'
    try:
        r = redis.from_url(config.REDIS_URL)
    except Exception:
        r = None
    # detect automatically if this phone has a stored password in Redis
    require_password = False
    try:
        r = redis.from_url(config.REDIS_URL)
    except Exception:
        r = None
    if r:
        try:
            # password stored under key 'tdlib:password:<phone>' (plain for scaffold)
            pwk = f'tdlib:password:{phone}'
            if r.exists(pwk):
                require_password = True
        except Exception:
            require_password = False

    data = { 'phone': phone, 'status': 'code_sent', 'code': code, 'ts': int(time.time()), 'require_password': require_password }
    if r:
        try:
            r.set('tdlib:auth', json.dumps(data, default=str), ex=300)
        except Exception:
            pass
    else:
        try:
            repo_root = Path(__file__).resolve().parents[2]
            (repo_root / 'tmp_tdlib_auth.json').write_text(json.dumps(data))
        except Exception:
            pass
    # return require_password indicator so UI can show password field automatically
    return { 'status': 'code_sent', 'require_password': data.get('require_password', False) }


@router.post('/auth/check')
def auth_check(payload: dict):
    """Check code. Payload: { code: '12345' }"""
    code = (payload or {}).get('code')
    password = (payload or {}).get('password')
    user = (payload or {}).get('user')
    # Permitir login demo/demo123 solo si variable de entorno GITHUB_BUILD=1
    if os.getenv('GITHUB_BUILD') == '1' and user == 'demo' and password == 'demo123':
        return { 'status': 'ok', 'user': 'demo', 'token': 'demo-token' }
    if not code:
        raise HTTPException(status_code=400, detail='code required')
    try:
        r = redis.from_url(config.REDIS_URL)
    except Exception:
        r = None
    data = None
    if r:
        try:
            v = r.get('tdlib:auth')
            if v:
                data = json.loads(v)
        except Exception:
            data = None
    else:
        try:
            repo_root = Path(__file__).resolve().parents[2]
            p = repo_root / 'tmp_tdlib_auth.json'
            if p.exists():
                data = json.loads(p.read_text())
        except Exception:
            data = None
    if not data:
        raise HTTPException(status_code=404, detail='no auth flow')
    if code == data.get('code'):
        # If this flow requires a password and none was provided, ask client to supply it
        if data.get('require_password') and not password:
            return JSONResponse(content={ 'status': 'password_required' })

        # If password required and provided, verify against stored password in Redis
        if data.get('require_password') and password:
            try:
                # try to read stored password (scaffold stores plain text under tdlib:password:<phone>)
                pw_key = f'tdlib:password:{data.get("phone")}'
                stored = None
                if r:
                    try:
                        v = r.get(pw_key)
                        if v:
                            stored = v.decode() if isinstance(v, bytes) else v
                    except Exception:
                        stored = None
                # If stored exists, compare; otherwise accept (scaffold fallback)
                if stored is not None:
                    if password != stored:
                        return JSONResponse(status_code=403, content={ 'status': 'password_mismatch', 'message': 'no coincide' })
                    else:
                        data['password_used'] = True
                else:
                    # no stored password to verify against — accept but mark used
                    data['password_used'] = True
            except Exception:
                # on error, reject
                return JSONResponse(status_code=500, content={ 'status': 'error', 'message': 'password check failed' })

        data['status'] = 'ready'
        data['session_id'] = uuid.uuid4().hex
        if r:
            try:
                r.set('tdlib:auth', json.dumps(data, default=str))
            except Exception:
                pass
        else:
            try:
                repo_root = Path(__file__).resolve().parents[2]
                (repo_root / 'tmp_tdlib_auth.json').write_text(json.dumps(data))
            except Exception:
                pass
        return { 'status': 'ok', 'session_id': data['session_id'] }
    raise HTTPException(status_code=403, detail='invalid code')


@router.get('/auth/status')
def auth_status():
    try:
        r = redis.from_url(config.REDIS_URL)
    except Exception:
        r = None
    data = None
    if r:
        try:
            v = r.get('tdlib:auth')
            if v:
                data = json.loads(v)
        except Exception:
            data = None
    else:
        try:
            repo_root = Path(__file__).resolve().parents[2]
            p = repo_root / 'tmp_tdlib_auth.json'
            if p.exists():
                data = json.loads(p.read_text())
        except Exception:
            data = None
    if not data:
        return { 'status': 'none' }
    masked = dict(data)
    if 'code' in masked:
        masked['code'] = '*****'
    return masked


@router.post('/disconnect')
def disconnect_tdlib():
    global _td_client
    if _td_client:
        try:
            _td_client.stop()
        except Exception:
            pass
        _td_client = None
    return { 'status': 'stopped' }


@router.post('/send')
def send_message(payload: dict, request: Request):
    if not payload or not payload.get('chat_id') or not payload.get('text'):
        raise HTTPException(status_code=400, detail='chat_id and text required')
    global _td_client
    if not _td_client:
        raise HTTPException(status_code=503, detail='tdlib client not connected')
    try:
        # support optional attachment_url in payload
        attachment = payload.get('attachment_url') if isinstance(payload, dict) else None
        res = _td_client.send_message(payload.get('chat_id'), payload.get('text'))
        # if attachment present, return it in result for UI
        if attachment:
            try:
                # include attachment metadata
                return { 'status': 'ok', 'result': res, 'attachment': attachment }
            except Exception:
                pass
        return { 'status': 'ok', 'result': res }
    except TDLibNotAvailable:
        raise HTTPException(status_code=501, detail='tdlib bindings not available on server')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/chats')
def list_chats(limit: int = 100):
    global _td_client
    if not _td_client:
        raise HTTPException(status_code=503, detail='tdlib client not connected')
    try:
        chats = _td_client.get_chats(limit=limit)
        return chats
    except TDLibNotAvailable:
        raise HTTPException(status_code=501, detail='tdlib bindings not available on server')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/messages')
def get_messages(limit: int = 100):
    """Return recent TDLib events stored in Redis (if available)."""
    try:
        r = redis.from_url(config.REDIS_URL)
    except Exception:
        r = None
    out = []
    if r:
        try:
            items = r.lrange('tdlib:events', 0, limit-1) or []
            for it in items:
                try:
                    if isinstance(it, bytes):
                        s = it.decode()
                    else:
                        s = it
                    out.append(json.loads(s) if s and s[0] in '{["' else s)
                except Exception:
                    out.append(it)
        except Exception:
            out = []
    return out


@router.post('/upload')
async def upload_file(file: UploadFile = File(...)):
    """Accept a multipart file upload and save it under web/uploads so it is
    served by the static files mount. Returns JSON with `url` pointing to the file."""
    try:
        repo_root = Path(__file__).resolve().parents[2]
    except Exception:
        repo_root = Path('.')
    uploads_dir = repo_root / 'web' / 'uploads'
    uploads_dir.mkdir(parents=True, exist_ok=True)
    # generate safe name
    ext = Path(file.filename).suffix or ''
    fname = f"{uuid.uuid4().hex}{ext}"
    dest = uploads_dir / fname
    try:
        with dest.open('wb') as fh:
            content = await file.read()
            fh.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # Return relative URL under web/ so StaticFiles serves it
    return { 'url': f'/uploads/{fname}', 'filename': file.filename, 'size': dest.stat().st_size }


@router.post('/message/edit')
def edit_message(payload: dict, request: Request):
    """Edit a message text. Payload: { id: '<event id>', text: 'new text' }
    This scaffold will record an 'edited' event and broadcast it.
    """
    if not payload or not payload.get('id') or 'text' not in payload:
        raise HTTPException(status_code=400, detail='id and text required')
    # authorization: if WEB_API_KEY is set, require it
    api_key = getattr(config, 'WEB_API_KEY', None)
    if api_key:
        auth_header = None
        try:
            auth_header = request.headers.get('authorization') or request.headers.get('x-web-api-key') or request.headers.get('x-api-key')
        except Exception:
            auth_header = None
        token = None
        if auth_header:
            ah = auth_header.strip()
            if ah.lower().startswith('bearer '):
                token = ah.split(None,1)[1]
            else:
                token = ah
        if token != api_key:
            raise HTTPException(status_code=403, detail='forbidden')

    mid = payload.get('id')
    new_text = payload.get('text')
    # create an edited event
    ev = { 'type': 'edited', 'id': mid, 'text': new_text, 'ts': int(time.time()) }
    # push to redis and broadcast
    try:
        r = redis.from_url(config.REDIS_URL)
        r.lpush('tdlib:events', json.dumps(ev, default=str))
        r.ltrim('tdlib:events', 0, 999)
    except Exception:
        pass
    try:
        asyncio.get_event_loop().create_task(ws_mgr.broadcast(json.dumps(ev, default=str)))
    except Exception:
        try:
            asyncio.run(ws_mgr.broadcast(json.dumps(ev, default=str)))
        except Exception:
            pass
    return { 'status': 'ok', 'edited': mid }


@router.post('/message/delete')
def delete_message(payload: dict, request: Request):
    """Delete a message. Payload: { id: '<event id>' } — records a 'deleted' event."""
    if not payload or not payload.get('id'):
        raise HTTPException(status_code=400, detail='id required')
    # authorization: if WEB_API_KEY is set, require it
    api_key = getattr(config, 'WEB_API_KEY', None)
    if api_key:
        auth_header = None
        try:
            auth_header = request.headers.get('authorization') or request.headers.get('x-web-api-key') or request.headers.get('x-api-key')
        except Exception:
            auth_header = None
        token = None
        if auth_header:
            ah = auth_header.strip()
            if ah.lower().startswith('bearer '):
                token = ah.split(None,1)[1]
            else:
                token = ah
        if token != api_key:
            raise HTTPException(status_code=403, detail='forbidden')

    mid = payload.get('id')
    ev = { 'type': 'deleted', 'id': mid, 'ts': int(time.time()) }
    try:
        r = redis.from_url(config.REDIS_URL)
        r.lpush('tdlib:events', json.dumps(ev, default=str))
        r.ltrim('tdlib:events', 0, 999)
    except Exception:
        pass
    try:
        asyncio.get_event_loop().create_task(ws_mgr.broadcast(json.dumps(ev, default=str)))
    except Exception:
        try:
            asyncio.run(ws_mgr.broadcast(json.dumps(ev, default=str)))
        except Exception:
            pass
    return { 'status': 'ok', 'deleted': mid }


class WebSocketManager:
    def __init__(self):
        self.active = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active.discard(websocket)

    async def broadcast(self, message: str):
        to_remove = []
        for ws in list(self.active):
            try:
                await ws.send_text(message)
            except Exception:
                to_remove.append(ws)
        for ws in to_remove:
            self.disconnect(ws)


ws_mgr = WebSocketManager()


@router.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await ws_mgr.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # echo for now; real events should come from TDLib client and be pushed
            await websocket.send_text(json.dumps({'echo': data}))
    except WebSocketDisconnect:
        ws_mgr.disconnect(websocket)
