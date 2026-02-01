"""Pluggable LLM backend abstractions.

Provides simple backend interfaces for local transformers, remote HTTP APIs,
and optional llama.cpp / vLLM backends. These are lightweight wrappers used
by `ai_server.py` to call generate/stream operations.

This module contains minimal implementations and fallbacks; it's safe to
import even if optional dependencies are missing.
"""
from typing import Iterator, Optional
import json
import requests


class BaseBackend:
    def generate(self, prompt: str, max_length: int = 200) -> str:
        raise NotImplementedError()

    def stream_generate(self, prompt: str, max_length: int = 200) -> Iterator[str]:
        # yield text chunks (strings)
        raise NotImplementedError()


class RemoteHTTPBackend(BaseBackend):
    def __init__(self, url: str, api_key: Optional[str] = None):
        self.url = url.rstrip('/')
        self.api_key = api_key

    def _headers(self):
        h = {'Content-Type': 'application/json'}
        if self.api_key:
            h['Authorization'] = 'Bearer ' + self.api_key
        return h

    def generate(self, prompt: str, max_length: int = 200) -> str:
        resp = requests.post(self.url + '/generate', headers=self._headers(), json={'prompt': prompt, 'max_length': int(max_length)}, timeout=60)
        resp.raise_for_status()
        try:
            return resp.json().get('reply') or resp.text
        except Exception:
            return resp.text

    def stream_generate(self, prompt: str, max_length: int = 200):
        # returns an iterator of text chunks by reading server-sent lines
        resp = requests.post(self.url + '/generate', headers=self._headers(), json={'prompt': prompt, 'max_length': int(max_length), 'stream': True}, stream=True, timeout=60)
        resp.raise_for_status()
        def it():
            for raw in resp.iter_lines(decode_unicode=True):
                if raw is None:
                    continue
                line = raw.strip()
                if not line:
                    continue
                # try to parse JSON payload
                payload = line
                if line.startswith('data:'):
                    payload = line[len('data:'):].strip()
                try:
                    j = json.loads(payload)
                    # if structured, try common keys
                    if isinstance(j, dict) and 'chunk' in j:
                        yield j.get('chunk')
                    elif isinstance(j, dict) and 'reply' in j:
                        yield j.get('reply')
                    else:
                        yield json.dumps(j)
                except Exception:
                    yield payload
        return it()


class LocalTransformersBackend(BaseBackend):
    def __init__(self, generator_callable):
        # generator_callable should be a callable that accepts (prompt, max_length)
        self._gen = generator_callable

    def generate(self, prompt: str, max_length: int = 200) -> str:
        out = self._gen(prompt, max_length=max_length, do_sample=True, top_k=50, num_return_sequences=1)
        try:
            return out[0].get('generated_text') if isinstance(out, list) and out else str(out)
        except Exception:
            return str(out)

    def stream_generate(self, prompt: str, max_length: int = 200):
        # Transformers pipeline in this repo does not support token streaming;
        # fallback to single-chunk generation for compatibility.
        text = self.generate(prompt, max_length=max_length)
        def it():
            yield text
        return it()


def get_backend_from_cfg(cfg: dict, model_dir: Optional[str] = None, generator_getter: Optional[callable] = None) -> BaseBackend:
    btype = cfg.get('type', 'local')
    if btype == 'remote':
        return RemoteHTTPBackend(cfg.get('remote_url'), api_key=cfg.get('remote_key'))
    # local: try to use provided generator_getter to create transformers-based backend
    if generator_getter is not None:
        try:
            gen = generator_getter()
            return LocalTransformersBackend(gen)
        except Exception:
            pass
    # fallback: remote backend pointing to remote_url if provided
    if cfg.get('remote_url'):
        return RemoteHTTPBackend(cfg.get('remote_url'), api_key=cfg.get('remote_key'))
    # last-resort: raise
    raise RuntimeError('No suitable backend available (check LLM_BACKEND and configuration)')
