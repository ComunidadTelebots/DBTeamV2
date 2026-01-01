import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot.log')

class Handler(BaseHTTPRequestHandler):
    def _auth_ok(self):
        secret = os.getenv('WEB_API_SECRET')
        if not secret:
            return True
        auth = self.headers.get('Authorization','')
        if auth.startswith('Bearer '):
            token = auth.split(' ',1)[1].strip()
            return token == secret
        return False

    def _send_json(self, obj, status=200):
        b = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if not self._auth_ok():
            self._send_json({'error':'unauthorized'}, status=401)
            return
        url = urlparse(self.path)
        if url.path == '/' or url.path == '/stats':
            # return minimal stats
            info = {'status':'ok', 'note':'temporary server'}
            self._send_json(info)
            return
        if url.path == '/messages':
            try:
                with open(LOG_PATH, 'rb') as f:
                    data = f.read().splitlines()[-200:]
                objs = [{'line': l.decode('utf-8', errors='replace')} for l in data]
            except Exception:
                objs = []
            self._send_json(objs)
            return
        self._send_json({'error':'not_found'}, status=404)

    def log_message(self, format, *args):
        return

def run():
    host = '0.0.0.0'
    port = 8081
    server = HTTPServer((host, port), Handler)
    print(f"temp_stats_server listening on {host}:{port}")
    server.serve_forever()

if __name__ == '__main__':
    run()
