"""Helpers for streaming SSE and parsing downstream LLM streams.

This module keeps parsing and SSE-related utilities separate so ai_server
can import them without being cluttered.
"""
from typing import Iterator, Dict, Any
import json

def parse_sse_stream_lines(lines: Iterator[str]) -> Iterator[Dict[str, Any]]:
    """Parses an iterator of SSE-like lines into discrete JSON/text events.

    Yields dicts like {"type":"data", "text":"..."} or {"type":"json", ...}
    """
    buf = []
    for line in lines:
        if not line:
            continue
        s = line.strip()
        if s == '':
            continue
        if s.startswith('data:'):
            payload = s[len('data:'):].strip()
            if payload == '[DONE]':
                yield {"type": "done"}
                continue
            try:
                j = json.loads(payload)
                yield {"type": "json", "data": j}
            except Exception:
                yield {"type": "data", "text": payload}
        else:
            # non standard, try json
            try:
                j = json.loads(s)
                yield {"type": "json", "data": j}
            except Exception:
                yield {"type": "data", "text": s}


def sse_event_generator(resp_iter) -> Iterator[str]:
    """Normalize a response iterator (lines or bytes) into text lines.

    Accepts either an iterator of bytes/chunks or strings. Yields decoded lines.
    """
    for chunk in resp_iter:
        if chunk is None:
            continue
        if isinstance(chunk, bytes):
            try:
                chunk = chunk.decode('utf-8')
            except Exception:
                chunk = chunk.decode('latin-1', errors='ignore')
        if isinstance(chunk, str):
            for l in chunk.split('\n'):
                yield l
        else:
            yield str(chunk)
