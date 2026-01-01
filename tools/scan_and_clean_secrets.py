#!/usr/bin/env python3
"""
Simple scanner and optional cleaner for common repository secrets.

Usage:
  python tools/scan_and_clean_secrets.py --scan
  python tools/scan_and_clean_secrets.py --clean  # will backup changed files
  python tools/scan_and_clean_secrets.py --serve  # starts localhost:8000 with /scan and /clean endpoints

This script is intentionally conservative: `--scan` only reports; `--clean` replaces detected values
with placeholders after backing up originals under `.secrets_backup/`.
"""
import argparse
import http.server
import json
import os
import re
import shutil
import socketserver
import threading
import uuid
from datetime import datetime
from urllib.parse import urlparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BACKUP_DIR = os.path.join(ROOT, '.secrets_backup')
INCIDENTS_FILE = os.path.join(ROOT, 'data', 'status_incidents.json')

PATTERNS = {
    'TELEGRAM_BOT_TOKEN': re.compile(r"\b\d{8,}:AA[0-9A-Za-z_-]{35}\b"),
    'WEB_API_SECRET_BASE64': re.compile(r"[A-Za-z0-9_\-]{16,}={0,2}"),
    'AWS_ACCESS_KEY_ID': re.compile(r"AKIA[0-9A-Z]{16}"),
    'AWS_SECRET_ACCESS_KEY': re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])"),
    'GITHUB_PAT': re.compile(r"ghp_[A-Za-z0-9]{36}"),
    'PRIVATE_KEY_PEM': re.compile(r"-----BEGIN (RSA |)PRIVATE KEY-----"),
}

TEXT_FILE_EXTS = ('.py', '.ps1', '.bat', '.sh', '.env', '.txt', '.md', '.yml', '.yaml', '.json')


def is_text_file(path):
    _, ext = os.path.splitext(path)
    return ext.lower() in TEXT_FILE_EXTS


def scan_repo():
    findings = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # skip .git, .venv and node_modules directories
        if any(x in dirpath for x in ('.git', '.venv', 'node_modules')) or dirpath.startswith(BACKUP_DIR):
            continue
        for f in filenames:
            path = os.path.join(dirpath, f)
            if not is_text_file(path):
                continue
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                    data = fh.read()
            except Exception:
                continue
            for name, pat in PATTERNS.items():
                for m in pat.finditer(data):
                    span = m.span()
                    excerpt = data[max(0, span[0]-20):min(len(data), span[1]+20)]
                    findings.append({'file': os.path.relpath(path, ROOT), 'type': name, 'match': m.group(0), 'excerpt': excerpt})
    return findings


def backup_file(path):
    rel = os.path.relpath(path, ROOT)
    dst = os.path.join(BACKUP_DIR, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(path, dst)


def clean_repo():
    findings = scan_repo()
    cleaned = []
    for item in findings:
        path = os.path.join(ROOT, item['file'])
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                data = fh.read()
        except Exception:
            continue
        # conservative replacement: replace exact match with a placeholder
        placeholder = f"<REDACTED_{item['type']}>"
        if item['match'] in data:
            backup_file(path)
            new = data.replace(item['match'], placeholder)
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(new)
            cleaned.append({'file': item['file'], 'replaced': item['match'], 'placeholder': placeholder})
    return {'cleaned': cleaned, 'backup_dir': os.path.relpath(BACKUP_DIR, ROOT)}


def load_incidents():
    try:
        os.makedirs(os.path.dirname(INCIDENTS_FILE), exist_ok=True)
        if not os.path.exists(INCIDENTS_FILE):
            with open(INCIDENTS_FILE, 'w', encoding='utf-8') as fh:
                json.dump([], fh)
        with open(INCIDENTS_FILE, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return []


def save_incident(obj):
    inc = load_incidents()
    # assign id and defaults
    obj.setdefault('id', str(uuid.uuid4()))
    obj.setdefault('status', 'open')
    obj.setdefault('created_at', datetime.utcnow().isoformat())
    inc.append(obj)
    with open(INCIDENTS_FILE, 'w', encoding='utf-8') as fh:
        json.dump(inc, fh, indent=2)


def close_incident(incident_id, closed_by=None, note=None):
    inc = load_incidents()
    changed = False
    for item in inc:
        if str(item.get('id')) == str(incident_id) and item.get('status') != 'closed':
            item['status'] = 'closed'
            item['closed_at'] = datetime.utcnow().isoformat()
            if closed_by:
                item['closed_by'] = closed_by
            if note:
                item['close_note'] = note
            changed = True
            break
    if changed:
        with open(INCIDENTS_FILE, 'w', encoding='utf-8') as fh:
            json.dump(inc, fh, indent=2)
    return changed


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        # quick status summary
        if parsed.path == '/status':
            s = summarize_status()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(s, indent=2).encode('utf-8'))
            return
        if parsed.path == '/scan':
            findings = scan_repo()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(findings, indent=2).encode('utf-8'))
            return
        elif parsed.path == '/incidents':
            items = load_incidents()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(items, indent=2).encode('utf-8'))
            return
        elif parsed.path == '/clean':
            result = clean_repo()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, indent=2).encode('utf-8'))
            return
        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/incidents':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8') if length else '{}'
            try:
                obj = json.loads(body)
            except Exception:
                obj = {'note': body}
            # enrich
            obj.setdefault('reported_by', obj.get('reported_by', 'local'))
            save_incident(obj)
            self.send_response(201)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'result': 'ok', 'incident': obj}).encode('utf-8'))
            return
        elif parsed.path == '/incidents/close':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8') if length else '{}'
            try:
                payload = json.loads(body)
            except Exception:
                payload = {}
            incident_id = payload.get('id')
            closed_by = payload.get('closed_by')
            note = payload.get('note')
            if not incident_id:
                self.send_response(400)
                self.end_headers()
                return
            ok = close_incident(incident_id, closed_by=closed_by, note=note)
            if ok:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'result': 'ok', 'id': incident_id}).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
            return
        # fallback
        self.send_response(404)
        self.end_headers()


def serve(port=8000):
    os.chdir(ROOT)
    with socketserver.TCPServer(('127.0.0.1', port), Handler) as httpd:
        print(f"Serving scan endpoints at http://127.0.0.1:{port}/scan and /clean")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('Shutting down')


def summarize_status():
    findings = scan_repo()
    incidents = load_incidents()
    # default component list
    comps = [
        {'id': 'api', 'name': 'API', 'status': 'operational'},
        {'id': 'bot', 'name': 'Bot', 'status': 'operational'},
        {'id': 'web', 'name': 'Web UI', 'status': 'operational'},
        {'id': 'db', 'name': 'Database', 'status': 'operational'},
    ]
    # heuristics to mark degraded components
    for f in findings:
        m = f.get('match','')
        path = f.get('file','')
        if 'bot' in path or 'BOT_TOKEN' in m:
            next((c for c in comps if c['id']=='bot'), None)['status'] = 'partial'
        if 'python_api' in path or any(k in m for k in ('WEB_API_SECRET','OPENAI_API_KEY','HUGGINGFACE_API_KEY')):
            next((c for c in comps if c['id']=='api'), None)['status'] = 'partial'
        if '.venv' in path or 'ai_index.pkl' in path:
            next((c for c in comps if c['id']=='web'), None)['status'] = 'partial'

    # if any open incident exists, escalate global
    open_inc = [i for i in incidents if i.get('status','open')!='closed']
    global_status = 'operational' if (not findings and not open_inc) else 'degraded'
    return {
        'global_status': global_status,
        'findings_count': len(findings),
        'open_incidents': len(open_inc),
        'components': comps,
        'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
        'findings': findings,
        'incidents': incidents
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan', action='store_true')
    parser.add_argument('--clean', action='store_true')
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()

    if args.scan:
        findings = scan_repo()
        print(json.dumps(findings, indent=2))
        return
    if args.clean:
        res = clean_repo()
        print(json.dumps(res, indent=2))
        return
    if args.serve:
        serve(args.port)
        return
    parser.print_help()


if __name__ == '__main__':
    main()
