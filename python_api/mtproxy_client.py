"""Simple helper to query MTProxy stats endpoints or probe TCP connectivity.

This module is used by `mtproxy_server.py` and by web UI pages that
fetch `/mtproxy/stats` from the local probe server.
"""
from __future__ import annotations
import os
import json
import socket
import time
from typing import Optional, Dict, Any
import requests


def get_remote_stats(url: str, timeout: float = 3.0) -> Dict[str, Any]:
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        content_type = r.headers.get('Content-Type','')
        if 'application/json' in content_type:
            return {'ok': True, 'source': url, 'data': r.json()}
        else:
            # return raw text wrapped
            return {'ok': True, 'source': url, 'data': {'text': r.text}}
    except Exception as e:
        return {'ok': False, 'source': url, 'error': str(e)}


def probe_tcp(host: str, port: int, timeout: float = 2.0) -> Dict[str, Any]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    start = time.time()
    try:
        s.connect((host, port))
        latency = (time.time() - start) * 1000.0
        s.close()
        return {'ok': True, 'host': host, 'port': port, 'latency_ms': round(latency, 2)}
    except Exception as e:
        return {'ok': False, 'host': host, 'port': port, 'error': str(e)}


def gather_mtproxy_stats(url: Optional[str] = None, host: Optional[str] = None, port: Optional[int] = None) -> Dict[str, Any]:
    """Gather stats using environment configuration.

    Priority:
      - If MTPROXY_STATS_URL is set -> HTTP GET that URL and return JSON/text.
      - Else -> TCP probe to MTPROXY_HOST:MTPROXY_PORT and return reachability/latency.
    """
    # allow overrides from caller
    if url:
        return get_remote_stats(url)
    env_url = os.getenv('MTPROXY_STATS_URL')
    if env_url:
        return get_remote_stats(env_url)

    if host is None:
        host = os.getenv('MTPROXY_HOST', '127.0.0.1')
    if port is None:
        try:
            port = int(os.getenv('MTPROXY_PORT', os.getenv('MTPROXY_STATS_PORT', '443')))
        except Exception:
            port = 443
    return probe_tcp(host, port)
