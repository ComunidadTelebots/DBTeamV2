import os
import json
import threading
import time
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

from python_bot import main as bot_main
from python_bot.storage import storage
from python_bot.utils import send_telegram_message

WEB_API_SECRET = os.getenv('WEB_API_SECRET')
LOGIN_TTL = 300  # seconds

class LoginHandler(BaseHTTPRequestHandler):
    def _send_json(self, code, obj):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        self.end_headers()

    def _auth_ok(self):
        auth = self.headers.get('Authorization','')
        if auth.startswith('Bearer '):
            token = auth.split(' ',1)[1].strip()
            return token == WEB_API_SECRET
        return False

    def do_POST(self):
        if self.path == '/login/request':
            length = int(self.headers.get('Content-Length','0'))
            body = self.rfile.read(length).decode('utf-8')
            try:
                data = json.loads(body)
            except Exception:
                data = parse_qs(body)
            username = (data.get('username') or data.get('user') or data.get('u'))
            if isinstance(username, list):
                username = username[0]
            if not username:
                return self._send_json(400, {'error':'missing username'})

            # resolve target chat id: prefer numeric id, otherwise look up stored username mapping
            target_chat = None
            try:
                s = str(username).strip()
                if s.startswith('@'):
                    uname = s.lstrip('@').lower()
                    mapped = storage.get(f'uname:{uname}')
                    if mapped:
                        try:
                            target_chat = int(mapped)
                        except Exception:
                            target_chat = None
                    else:
                        return self._send_json(400, {'error':'user_not_seen', 'message':'User must start a chat with the bot first'})
                else:
                    # accept numeric id directly
                    try:
                        target_chat = int(s)
                    except Exception:
                        return self._send_json(400, {'error':'invalid_user', 'message':'Provide @username or numeric id'})
            except Exception:
                return self._send_json(400, {'error':'invalid_user'})

            # generate code and associate with username/target
            code = secrets.token_urlsafe(6)
            key = f'weblogin:{code}'
            storage.set(key, json.dumps({'user': username, 'created': int(time.time())}))
            # send via bot to numeric chat id asynchronously to avoid blocking the HTTP server
            try:
                token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
                text = f'Login code for web: {code} (valid {LOGIN_TTL}s)'
                def _send_async():
                    try:
                        send_telegram_message(str(target_chat), text, token=token, timeout=8)
                    except Exception:
                        # best-effort: ignore failures here; admin can fetch code via WEB_API_SECRET
                        pass
                thr = threading.Thread(target=_send_async, daemon=True)
                thr.start()
            except Exception:
                # ignore send threading errors
                pass
            return self._send_json(200, {'ok':True})

        if self.path == '/login/verify':
            length = int(self.headers.get('Content-Length','0'))
            body = self.rfile.read(length).decode('utf-8')
            try:
                data = json.loads(body)
            except Exception:
                data = parse_qs(body)
            code = (data.get('code') or data.get('c'))
            if isinstance(code, list):
                code = code[0]
            if not code:
                return self._send_json(400, {'error':'missing code'})
            key = f'weblogin:{code}'
            raw = storage.get(key)
            if not raw:
                return self._send_json(403, {'error':'invalid_or_expired'})
            try:
                payload = json.loads(raw)
            except Exception:
                payload = None
            if not payload:
                return self._send_json(403, {'error':'invalid_payload'})
            if int(time.time()) - int(payload.get('created',0)) > LOGIN_TTL:
                return self._send_json(403, {'error':'expired'})
            # create session token
            session = secrets.token_urlsafe(24)
            s_key = f'weblogin_session:{session}'
            # attempt to resolve username to numeric id via Telegram API (optional)
            user_field = payload.get('user')
            resolved_id = None
            try:
                token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
                import requests
                chat_id = user_field if str(user_field).startswith('@') else f'@{user_field}'
                r = requests.get(f'https://api.telegram.org/bot{token}/getChat', params={'chat_id': chat_id}, timeout=5)
                jr = r.json() if r.content else {}
                if jr.get('ok') and jr.get('result') and 'id' in jr.get('result'):
                    resolved_id = jr['result']['id']
            except Exception:
                resolved_id = None
            session_payload = {'user': payload.get('user'), 'user_id': resolved_id, 'created': int(time.time())}
            storage.set(s_key, json.dumps(session_payload))
            # optionally record mapping user->session
            return self._send_json(200, {'ok':True, 'session': session})

        return self._send_json(404, {'error':'not_found'})

    def do_GET(self):
        if self.path.startswith('/login/info'):
            # info endpoint to verify session
            auth = self.headers.get('Authorization','')
            token = ''
            if auth.startswith('Bearer '):
                token = auth.split(' ',1)[1].strip()
            elif 'session' in self.path:
                parts = self.path.split('session=')
                if len(parts) > 1:
                    token = parts[1]
            if not token:
                return self._send_json(401, {'error':'missing_session'})
            s_key = f'weblogin_session:{token}'
            raw = storage.get(s_key)
            if not raw:
                return self._send_json(403, {'error':'invalid_session'})
            try:
                payload = json.loads(raw)
            except Exception:
                payload = None
            return self._send_json(200, {'ok':True, 'user': payload.get('user') if payload else None})
        return self._send_json(404, {'error':'not_found'})


def start_server(port=8082):
    server = HTTPServer(('0.0.0.0', port), LoginHandler)
    try:
        server.serve_forever()
    except Exception:
        pass


def setup(bot):
    # start background server thread
    t = threading.Thread(target=start_server, args=(int(os.getenv('WEB_LOGIN_PORT','8082')),), daemon=True)
    t.start()
    print("Plugin 'web_login' loaded and HTTP server started.")
    # register a lightweight message handler to map usernames to numeric ids
    try:
        def _store_username(update, context):
            try:
                user = None
                # Update may be a PTB Update object; try common accessors
                if hasattr(update, 'effective_user') and update.effective_user:
                    user = update.effective_user
                elif hasattr(update, 'message') and getattr(update, 'message') and getattr(update.message, 'from_user', None):
                    user = update.message.from_user
                if not user:
                    return
                uname = getattr(user, 'username', None)
                uid = getattr(user, 'id', None)
                if uname and uid:
                    try:
                        storage.set(f'uname:{uname.lower()}', str(uid))
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            bot.register_message_handler('text', _store_username, plugin='web_login')
        except Exception:
            # best-effort registration; ignore if bot object doesn't support it
            pass
    except Exception:
        pass
    # register a simple `/weblogin` command so users can request a code from the bot directly
    try:
        async def _weblogin_cmd(update, context):
            try:
                uid = None
                uname = None
                if hasattr(update, 'effective_user') and update.effective_user:
                    uid = getattr(update.effective_user, 'id', None)
                    uname = getattr(update.effective_user, 'username', None)
                if not uid:
                    return
                code = secrets.token_urlsafe(6)
                key = f'weblogin:{code}'
                storage.set(key, json.dumps({'user': str(uid), 'created': int(time.time())}))
                # store username mapping for future web->bot lookups
                if uname:
                    try:
                        storage.set(f'uname:{uname.lower()}', str(uid))
                    except Exception:
                        pass
                try:
                    await context.bot.send_message(chat_id=uid, text=f'Your web login code: {code} (valid {LOGIN_TTL}s)')
                except Exception:
                    pass
            except Exception:
                pass
        try:
            bot.register_command('weblogin', _weblogin_cmd, 'Get web login code', plugin='web_login')
        except Exception:
            pass
    except Exception:
        pass
