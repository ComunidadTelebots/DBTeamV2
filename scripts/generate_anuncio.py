#!/usr/bin/env python3
"""
Standalone anuncio generator.
Usage:
  python scripts/generate_anuncio.py --prompt "texto" [--title "Titulo"] [--max-length 150] [--save] [--post-url http://localhost:8000/api/anuncios]

Behavior:
 - Try to use `transformers` locally. If not available, POST to local AI server at 127.0.0.1:8081/ai/gpt2.
 - Prints generated text. If `--save` will write JSON into `data/anuncios/<id>.json`.
 - If `--post-url` provided, will POST the anuncio payload to that URL.
No changes made to existing server code.
"""
import argparse
import json
import os
import time
import random
import sys

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    HAS_TRANSFORMERS = True
except Exception:
    HAS_TRANSFORMERS = False

import requests
from pathlib import Path


def gen_with_transformers(prompt, max_length=150):
    cache_dir = './models/gpt2'
    tokenizer = AutoTokenizer.from_pretrained('gpt2', cache_dir=cache_dir)
    model = AutoModelForCausalLM.from_pretrained('gpt2', cache_dir=cache_dir)
    gen = pipeline('text-generation', model=model, tokenizer=tokenizer, device=-1)
    out = gen(prompt, max_length=max_length, do_sample=True, top_k=50, num_return_sequences=1)
    text = out[0].get('generated_text') if isinstance(out, list) and out else str(out)
    return text


def gen_with_ai_server(prompt, max_length=150, host='127.0.0.1', port=8081):
    url = f'http://{host}:{port}/ai/gpt2'
    try:
        r = requests.post(url, json={'prompt': prompt, 'max_length': max_length}, timeout=20)
        r.raise_for_status()
        j = r.json()
        # server returns {'reply': text} or {'error':...}
        if 'reply' in j:
            return j['reply']
        # tolerant
        return j.get('result') or j.get('text') or ''
    except Exception as e:
        raise RuntimeError(f'AI server request failed: {e}')


def save_anuncio(title, contenido):
    repo_root = Path(__file__).resolve().parents[0]
    # repo layout: scripts/ -> repo root is parent of scripts
    repo_root = repo_root.parents[0]
    anuncios_dir = repo_root / 'data' / 'anuncios'
    anuncios_dir.mkdir(parents=True, exist_ok=True)
    aid = str(int(time.time()*1000)) + str(random.randint(100, 999))
    anuncio = {
        'id': aid,
        'titulo': title,
        'contenido': contenido,
        'usuario': {'username': 'ia', 'is_admin': False},
        'estado': 'pendiente',
        'created_at': int(time.time())
    }
    fpath = anuncios_dir / f"{aid}.json"
    with open(fpath, 'w', encoding='utf-8') as fh:
        json.dump(anuncio, fh, ensure_ascii=False, indent=2)
    return anuncio, str(fpath)


def post_anuncio(post_url, titulo, contenido):
    payload = {'titulo': titulo, 'contenido': contenido, 'usuario': {'username': 'ia', 'is_admin': True}}
    try:
        r = requests.post(post_url, json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--prompt', required=True)
    p.add_argument('--title', default='Anuncio IA')
    p.add_argument('--max-length', type=int, default=150)
    p.add_argument('--save', action='store_true')
    p.add_argument('--post-url', default=None)
    p.add_argument('--use-server', action='store_true', help='Force using local AI server instead of transformers')
Quiero que arranques la wen entera para ver si hay     p.add_argument('--stub', action='store_true', help='Use a quick stub (no external calls)')
    args = p.parse_args()

    prompt = args.prompt
    max_length = args.max_length
    text = None

    if args.stub:
        print('Using stub generator (no external calls).')
        text = prompt + '\n\n[GENERATED-STUB]'
    elif HAS_TRANSFORMERS and not args.use_server:
        try:
            print('Generating with local transformers...')
            text = gen_with_transformers(prompt, max_length=max_length)
        except Exception as e:
            print(f'Local generation failed: {e}', file=sys.stderr)
            print('Falling back to AI server...')

    if text is None:
        try:
            text = gen_with_ai_server(prompt, max_length=max_length)
        except Exception as e:
            print(f'AI generation failed: {e}', file=sys.stderr)
            print('Falling back to stub generator.')
            text = prompt + '\n\n[GENERATED-STUB]'

    print('\n--- Generated anuncio ---\n')
    print(text)
    print('\n-------------------------\n')

    if args.save:
        anuncio, path = save_anuncio(args.title, text)
        print(f'Saved anuncio to: {path}')

    if args.post_url:
        res = post_anuncio(args.post_url, args.title, text)
        print('POST result:', res)


if __name__ == '__main__':
    main()
