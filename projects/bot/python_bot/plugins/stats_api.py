"""Statistics API plugin.

Starts a small HTTP server in background exposing:
- GET /messages -> recent bot.log lines as JSON array
- GET /stats -> simple stats from `storage`

Also registers `/stats` command that returns a short summary inside Telegram.
"""
import os
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from typing import Any
from pathlib import Path
import traceback
import subprocess

from python_bot.storage import storage


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _get_logpath() -> str:
    repo = _repo_root()
    return str(repo / 'bot.log')


def _read_last_lines(path: str, limit: int = 200):
    try:
        with open(path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            block = 1024
            data = b''
            while size > 0 and data.count(b'\n') <= limit:
                read_size = min(block, size)
                f.seek(size - read_size)
                data = f.read(read_size) + data
                size -= read_size
            lines = data.splitlines()[-limit:]
            return [l.decode('utf-8', errors='replace') for l in lines]
    except Exception:
        return []


class _StatsHandler(BaseHTTPRequestHandler):
    def _auth_ok(self):
        secret = os.getenv('WEB_API_SECRET')
        if not secret:
            return True
        auth = self.headers.get('Authorization','')
        if auth.startswith('Bearer '):
            token = auth.split(' ',1)[1].strip()
            if token == secret:
                return True
            # allow session tokens issued by web_login: look up weblogin_session:<token>
            try:
                from python_bot.storage import storage as _storage
                s = _storage.get(f'weblogin_session:{token}')
                if s:
                    try:
                        obj = json.loads(s)
                    except Exception:
                        obj = None
                    if obj:
                        # if resolved numeric user id present, treat numeric SUDO/creator as authorized
                        uid = obj.get('user_id')
                        if uid:
                            try:
                                # check env SUDO_USERS fallback
                                sudos_env = os.getenv('SUDO_USERS','')
                                if str(uid) in [s.strip() for s in sudos_env.split(',') if s.strip()]:
                                    return True
                            except Exception:
                                pass
                        # if no numeric id, accept valid session (best-effort)
                        return True
            except Exception:
                pass
            return False
        return False

    def _send_json(self, obj, status=200):
        b = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        # CORS headers to allow the web UI to fetch from another port
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        # Reply to preflight CORS requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        if not self._auth_ok():
            self._send_json({'error':'unauthorized'}, status=401)
            return
        url = urlparse(self.path)
        if url.path == '/' or url.path == '/stats':
            # gather stats
            info = storage.dump_settings()
            info['infohash_count'] = len(storage.list_infohashes()) if hasattr(storage, 'list_infohashes') else 0
            # expose configured web app urls if present
            try:
                info['webapp_url'] = os.getenv('WEBAPP_URL') or ''
                info['webapp_onion'] = os.getenv('WEBAPP_ONION') or ''
            except Exception:
                info['webapp_url'] = ''
                info['webapp_onion'] = ''
            # include pending queues if Redis available
            try:
                try:
                    import redis as _redis
                except Exception:
                    _redis = None
                if _redis is not None:
                    host = os.getenv('REDIS_HOST','127.0.0.1')
                    port = int(os.getenv('REDIS_PORT','6379'))
                    r = _redis.StrictRedis(host=host, port=port, db=0, decode_responses=True)
                    info['pending_outbox'] = int(r.llen('web:outbox') or 0)
                    info['pending_web_messages'] = int(r.llen('web:messages') or 0)
                else:
                    info['pending_outbox'] = 'n/a'
                    info['pending_web_messages'] = 'n/a'
            except Exception:
                info['pending_outbox'] = 'err'
                info['pending_web_messages'] = 'err'
            self._send_json(info)
            return
        if url.path == '/messages':
            logp = _get_logpath()
            lines = _read_last_lines(logp, limit=200)
            objs = []
            for l in lines:
                objs.append({'line': l})
            self._send_json(objs)
            return
        if url.path == '/torrents':
            # attempt to import stream_torrent plugin and read ACTIVE_TORRENTS
            try:
                from python_bot.plugins import stream_torrent as st
                data = list(st.ACTIVE_TORRENTS.values())
            except Exception:
                data = []
            self._send_json({'torrents': data})
            return
        if url.path == '/pending':
            # Serve pending .torrent files stored under pending_torrents/<user_id>/
            # Requires authorization (WEB_API_SECRET or valid session)
            if not self._auth_ok():
                self._send_json({'error':'unauthorized'}, status=401)
                return
            try:
                qs = url.query
                from urllib.parse import parse_qs, unquote
                params = parse_qs(qs)
                user = params.get('user', [None])[0]
                fname = params.get('file', [None])[0]
                if not user or not fname:
                    self._send_json({'error':'missing_params'}, status=400); return
                # sanitize path fragments
                user_safe = os.path.basename(user)
                file_safe = os.path.basename(unquote(fname))
                repo = _repo_root()
                fpath = str(repo / 'pending_torrents' / user_safe / file_safe)
                if not os.path.exists(fpath):
                    self._send_json({'error':'not_found'}, status=404); return
                # stream file
                try:
                    with open(fpath, 'rb') as fh:
                        data = fh.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/x-bittorrent')
                    self.send_header('Content-Length', str(len(data)))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(data)
                except Exception:
                    self._send_json({'error':'read_failed'}, status=500)
            except Exception:
                self._send_json({'error':'invalid_request'}, status=400)
            return
        # control endpoint (restart/start) via POST only; respond 405 for GET
        if url.path == '/control':
            self._send_json({'error':'method_not_allowed'}, status=405)
            return
        # not found
        self._send_json({'error':'not_found'}, status=404)

    def log_message(self, format, *args):
        # silence default logging
        return


def _run_server(host='0.0.0.0', port=8081):
    # allow setup() to define a richer handler (_ControlHandler)
    handler_cls = None
    for _ in range(20):
        handler_cls = globals().get('_ControlHandler') or globals().get('_StatsHandler')
        if handler_cls:
            break
        import time as _t
        _t.sleep(0.1)
    server = HTTPServer((host, port), handler_cls or _StatsHandler)
    try:
        # log server start
        try:
            with open(_get_logpath(), 'a', encoding='utf-8') as lf:
                lf.write(f"[stats_api] starting HTTP server on {host}:{port}\n")
        except Exception:
            pass
        server.serve_forever()
    except Exception:
        try:
            with open(_get_logpath(), 'a', encoding='utf-8') as lf:
                lf.write(f"[stats_api] server error:\n")
                lf.write(traceback.format_exc())
        except Exception:
            pass
        try:
            server.server_close()
        except Exception:
            pass


def setup(bot):
    # start HTTP server in background thread
    try:
        t = threading.Thread(target=_run_server, kwargs={'host':'0.0.0.0','port':8081}, daemon=True)
        t.start()
        try:
            with open(_get_logpath(), 'a', encoding='utf-8') as lf:
                lf.write('[stats_api] thread started\n')
        except Exception:
            pass
    except Exception:
        try:
            with open(_get_logpath(), 'a', encoding='utf-8') as lf:
                lf.write('[stats_api] failed to start thread\n')
                lf.write(traceback.format_exc())
        except Exception:
            pass

    async def stats_cmd(update: Any, context: Any):
        info = storage.dump_settings()
        info['infohash_count'] = len(storage.list_infohashes()) if hasattr(storage, 'list_infohashes') else 0
        try:
            await update.message.reply_text(f"Stats: chats={len(info.get('chats',[]))} infohashes={info.get('infohash_count')}")
        except Exception:
            pass

    bot.register_command('stats', stats_cmd, 'Show basic bot stats', plugin='stats_api')

    # add POST handler for control actions
    class _ControlHandler(_StatsHandler):
        def do_POST(self):
            if not self._auth_ok():
                self._send_json({'error':'unauthorized'}, status=401)
                return
            url = urlparse(self.path)
            if url.path != '/control':
                # allow /torrents control actions
                if url.path == '/torrents':
                    length = int(self.headers.get('Content-Length','0'))
                    body = self.rfile.read(length).decode('utf-8') if length>0 else ''
                    try:
                        data = json.loads(body) if body else {}
                    except Exception:
                        data = {}
                    action = data.get('action')
                    if action == 'stop':
                        tid = data.get('id')
                        if not tid:
                            self._send_json({'error':'missing_id'}, status=400); return
                        try:
                            from python_bot.plugins import stream_torrent as st
                            ok = st.stop_torrent(tid)
                            if ok:
                                self._send_json({'status':'stopped','id':tid})
                            else:
                                self._send_json({'error':'not_found','id':tid}, status=404)
                        except Exception as e:
                            self._send_json({'error':'stop_failed','detail': str(e)}, status=500)
                        return
                    self._send_json({'error':'not_found'}, status=404)
                    return
                self._send_json({'error':'not_found'}, status=404)
                return
            # read body
            length = int(self.headers.get('Content-Length','0'))
            body = self.rfile.read(length).decode('utf-8') if length>0 else ''
            try:
                data = json.loads(body) if body else {}
            except Exception:
                data = {}
            action = data.get('action')
            # allowed actions: restart
            if action == 'restart':
                # stop existing python_bot processes and start run_bot_alt.bat
                repo = _repo_root()
                run_script = str(repo / 'run_bot_alt.bat')
                token = data.get('token') or os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
                min_interval = str(data.get('min_interval') or os.getenv('TELEGRAM_MIN_INTERVAL') or '1.0')
                max_conc = str(data.get('max_concurrent') or os.getenv('TELEGRAM_MAX_CONCURRENT') or '1')
                try:
                    # stop processes via PowerShell command (best-effort)
                    kill_cmd = ["powershell", "-Command", "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'python_bot\\\\main.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"]
                    subprocess.run(kill_cmd, timeout=10)
                except Exception:
                    pass
                try:
                    if token:
                        subprocess.Popen([run_script, token, min_interval, max_conc], cwd=str(repo))
                    else:
                        # start without token (expects env)
                        subprocess.Popen([run_script], cwd=str(repo))
                    self._send_json({'status':'restarted'})
                except Exception as e:
                    self._send_json({'error':'start_failed','detail': str(e)}, status=500)
                return
            if action == 'update':
                # update targets: 'web' (projects/web/web) or 'bot' (repo root)
                target = data.get('target') or 'web'
                branch = data.get('branch') or None
                try:
                    repo = _repo_root()
                    if target == 'web':
                        web_path = str(repo / 'projects' / 'web' / 'web')
                        # optional branch checkout
                        if branch:
                            subprocess.run(['git', '-C', web_path, 'fetch', 'origin', branch], timeout=30)
                            subprocess.run(['git', '-C', web_path, 'checkout', branch], timeout=30)
                        g = subprocess.run(['git', '-C', web_path, 'pull'], capture_output=True, text=True, timeout=60)
                        # optional build command
                        build_cmd = data.get('build_cmd')
                        build_out = ''
                        if build_cmd:
                            try:
                                bproc = subprocess.run(build_cmd, shell=True, cwd=web_path, capture_output=True, text=True, timeout=300)
                                build_out = bproc.stdout + '\n' + bproc.stderr
                            except Exception as be:
                                build_out = f'build_failed: {be}'
                        self._send_json({'status':'updated','target':'web','git_stdout': g.stdout[:8000], 'build': build_out})
                        return
                    elif target == 'bot':
                        # pull repo and restart bot
                        g = subprocess.run(['git', '-C', str(repo), 'pull'], capture_output=True, text=True, timeout=60)
                        # then restart (reuse restart behavior)
                        run_script = str(repo / 'run_bot_alt.bat')
                        try:
                            kill_cmd = ["powershell", "-Command", "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'python_bot\\\\main.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"]
                            subprocess.run(kill_cmd, timeout=10)
                        except Exception:
                            pass
                        try:
                            if token:
                                subprocess.Popen([run_script, token, min_interval, max_conc], cwd=str(repo))
                            else:
                                subprocess.Popen([run_script], cwd=str(repo))
                        except Exception as e:
                            self._send_json({'error':'start_failed_after_update','detail': str(e),'git_stdout': g.stdout[:8000]}, status=500); return
                        self._send_json({'status':'updated_and_restarted','git_stdout': g.stdout[:8000]})
                        return
                    else:
                        self._send_json({'error':'invalid_target'}, status=400)
                        return
                except Exception as e:
                    self._send_json({'error':'update_failed','detail': str(e)}, status=500)
                return
            self._send_json({'error':'unsupported_action'}, status=400)

    # monkey-replace server's handler mapping to allow POST control
    # restart the server thread with new handler if needed (best-effort no-op)
