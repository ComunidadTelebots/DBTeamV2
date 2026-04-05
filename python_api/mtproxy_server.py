#!/usr/bin/env python3
"""Lightweight MTProxy probe server.

Exposes:
 - GET /mtproxy/stats -> JSON with reachability/http stats
 - GET /mtproxy/health -> { status: 'ok' }

Behavior:
 - If env `MTPROXY_STATS_URL` is set, performs an HTTP GET against it and returns the result.
 - Otherwise, performs a TCP probe to `MTPROXY_HOST`:`MTPROXY_PORT` (defaults: 127.0.0.1:443).

This is intentionally non-destructive and only probes connectivity/HTTP endpoints.
"""
from __future__ import annotations
import os
import json
from flask import Flask, jsonify, request
from uuid import uuid4
import threading
from pathlib import Path

# storage file for persistent server entries
DATA_FILE = Path(__file__).resolve().parent.parent / 'data' / 'mtproxy_servers.json'
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_servers():
    try:
        if DATA_FILE.exists():
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        return []
    return []


def _save_servers(srvs):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(srvs, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


_SERVERS_LOCK = threading.Lock()

try:
    from python_api.mtproxy_client import gather_mtproxy_stats
except Exception:
    # fallback relative import if module path differs
    from mtproxy_client import gather_mtproxy_stats

app = Flask(__name__)


@app.route('/mtproxy/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


@app.route('/mtproxy/stats', methods=['GET'])
def stats():
    try:
        server_id = request.args.get('server_id')
        if server_id:
            with _SERVERS_LOCK:
                servers = _load_servers()
            srv = next((s for s in servers if s.get('id') == server_id), None)
            if not srv:
                return jsonify({'status': 'error', 'error': 'server not found'}), 404
            # prefer stats_url then host/port
            url = srv.get('stats_url')
            host = srv.get('host')
            port = srv.get('port')
            data = gather_mtproxy_stats(url=url, host=host, port=port)
            return jsonify({'status': 'ok', 'server': srv, 'result': data})

        # no server_id -> use default gather
        data = gather_mtproxy_stats()
        return jsonify({'status': 'ok', 'result': data})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500



@app.route('/mtproxy/servers', methods=['GET'])
def list_servers():
    owner = request.args.get('owner_id')
    with _SERVERS_LOCK:
        servers = _load_servers()
    if owner:
        servers = [s for s in servers if s.get('owner_id') == owner]
    return jsonify({'status': 'ok', 'servers': servers})


@app.route('/mtproxy/servers', methods=['POST'])
def add_server():
    body = request.get_json(force=True, silent=True) or {}
    name = body.get('name') or body.get('label') or 'mtproto'
    host = body.get('host')
    port = body.get('port')
    stats_url = body.get('stats_url')
    owner_id = body.get('owner_id')
    new = {'id': str(uuid4()), 'name': name, 'host': host, 'port': port, 'stats_url': stats_url, 'owner_id': owner_id}
    with _SERVERS_LOCK:
        servers = _load_servers()
        servers.append(new)
        _save_servers(servers)
    return jsonify({'status': 'ok', 'server': new}), 201


@app.route('/mtproxy/servers/<server_id>', methods=['PUT'])
def update_server(server_id):
    body = request.get_json(force=True, silent=True) or {}
    with _SERVERS_LOCK:
        servers = _load_servers()
        idx = next((i for i, s in enumerate(servers) if s.get('id') == server_id), None)
        if idx is None:
            return jsonify({'status': 'error', 'error': 'not found'}), 404
        servers[idx].update({k: v for k, v in body.items() if k in ('name','host','port','stats_url','owner_id')})
        _save_servers(servers)
    return jsonify({'status': 'ok', 'server': servers[idx]})


@app.route('/mtproxy/servers/<server_id>', methods=['DELETE'])
def delete_server(server_id):
    with _SERVERS_LOCK:
        servers = _load_servers()
        new = [s for s in servers if s.get('id') != server_id]
        if len(new) == len(servers):
            return jsonify({'status': 'error', 'error': 'not found'}), 404
        _save_servers(new)
    return jsonify({'status': 'ok'})


def main():
    host = os.getenv('MTPROXY_BIND_HOST', '127.0.0.1')
    port = int(os.getenv('MTPROXY_BIND_PORT', os.getenv('MTPROXY_SERVER_PORT', '8082')))
    print(f"Starting mtproxy probe server on {host}:{port}")
    app.run(host=host, port=port)


if __name__ == '__main__':
    main()
