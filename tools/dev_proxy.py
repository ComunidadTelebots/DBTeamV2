#!/usr/bin/env python3
"""
Development server: serves the `web/` static files on http://127.0.0.1:8000
and proxies API requests to the local backends to avoid CORS during development.

Usage:
  pip install flask requests
  python tools/dev_proxy.py

It proxies paths starting with: /stream/, /admin/, /monitor/, /torrents/, /models/, /bot/, /ai/
"""
from flask import Flask, request, Response, send_from_directory
import requests
import os

app = Flask(__name__, static_folder=None)
ROOT = os.path.join(os.path.dirname(__file__), '..')
WEB_DIR = os.path.abspath(os.path.join(ROOT, 'web'))
BACKEND = 'http://127.0.0.1:8082'
AI_BACKEND = 'http://127.0.0.1:8081'

# add a proxy prefix for the official Nextcloud instance; requests to
# /nextcloud-proxy/... will be forwarded to http://127.0.0.1:8085 with the
# prefix stripped so Nextcloud sees requests at '/'.
PROXY_PREFIXES = ('stream/', 'admin/', 'monitor/', 'torrents/', 'models/', 'bot/', 'ai/', 'nextcloud-proxy/')


def proxy_request(path, backend):
    url = backend.rstrip('/') + path
    # build headers dict from incoming request, skipping Host to avoid conflicts
    headers = {k: v for k, v in request.headers.items() if k.lower() != 'host'}
    try:
        # debug: print basic incoming request info to help diagnose multipart handling
        try:
            info = f"PROXY INCOMING: {request.method} {path} Content-Type: {request.headers.get('Content-Type')} Content-Length: {request.headers.get('Content-Length')} HasFiles: {bool(request.files)} FormKeys: {list(request.form.keys())}\n"
            print(info.strip())
            if request.files:
                print('PROXY FILES:', [ (n, fh.filename) for n, fh in request.files.items() ])
            # also append to a log file so we can inspect from the agent
            try:
                with open(os.path.join(os.path.dirname(__file__), 'dev_proxy.log'), 'a', encoding='utf-8') as lf:
                    lf.write(info)
                    if request.files:
                        lf.write('FILES: ' + ','.join([f"{n}:{fh.filename}" for n, fh in request.files.items() ]) + '\n')
            except Exception:
                pass
        except Exception:
            pass
        # files handling: Flask provides request.files, requests accepts files mapping
        files = None
        data = None
        if request.files:
            files = {}
            for name, fh in request.files.items():
                files[name] = (fh.filename, fh.stream, fh.mimetype)
            # include form fields in data
            data = request.form.to_dict()
        else:
            data = request.get_data() if request.get_data() else None

        # If we're forwarding files, let `requests` build the multipart
        # Content-Type (with boundary). Remove any incoming Content-Type
        # / Content-Length so it doesn't conflict.
        if files:
            # remove Content-Type/Content-Length in either casing so
            # requests can build the multipart Content-Type with boundary
            headers.pop('Content-Type', None)
            headers.pop('content-type', None)
            headers.pop('Content-Length', None)
            headers.pop('content-length', None)

        resp = requests.request(
            method=request.method,
            url=url,
            params=request.args,
            headers=headers,
            data=None if files else data,
            files=files,
            stream=True,
            timeout=10
        )
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(name, value) for name, value in resp.raw.headers.items() if name.lower() not in excluded_headers]
        return Response(resp.raw.read(), status=resp.status_code, headers=response_headers)
    except requests.exceptions.RequestException as e:
        return Response('Backend request failed: %s' % str(e), status=502)


@app.route('/', defaults={'path': 'owner.html'})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def all_routes(path):
    # Proxy if path starts with any prefix
    for p in PROXY_PREFIXES:
        if path.startswith(p):
            if p == 'nextcloud-proxy/':
                backend = 'http://127.0.0.1:8085'
                # strip the prefix so backend receives root-relative path
                new_path = '/' + path[len(p):]
                return proxy_request(new_path, backend)
            backend = AI_BACKEND if path.startswith('ai/') else BACKEND
            return proxy_request('/' + path, backend)

    # Serve static files from web/
    target = os.path.join(WEB_DIR, path)
    if os.path.exists(target) and os.path.isfile(target):
        return send_from_directory(WEB_DIR, path)

    # Fallback to owner.html
    return send_from_directory(WEB_DIR, 'owner.html')


if __name__ == '__main__':
    print('Serving web/ on http://127.0.0.1:8000 and proxying API to 127.0.0.1:8082')
    app.run(host='127.0.0.1', port=8000, debug=False)
