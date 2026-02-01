#!/usr/bin/env python3
"""
Minimal RAG server: exposes `/rag/query` which uses a precomputed embeddings index
stored under `projects/bot/python_bot/data/ai_index_faiss.pkl` (or ai_index_faiss.* files).

This is intentionally lightweight: it attempts to use `numpy` + `pickle` and `sentence_transformers`
for query embeddings. If FAISS is present and an index file exists, it will use FAISS.

Usage (dev): python python_api/rag_server.py --host 127.0.0.1 --port 8083
"""
import os
import argparse
from pathlib import Path
import json
import pickle
import numpy as np
from flask import Flask, request, jsonify

app = Flask(__name__)

INDEX_META = Path(__file__).resolve().parents[0].parents[0] / 'projects' / 'bot' / 'python_bot' / 'data' / 'ai_index_faiss.pkl'

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

try:
    import faiss
except Exception:
    faiss = None


def load_index():
    if not INDEX_META.exists():
        return None
    with open(str(INDEX_META), 'rb') as fh:
        meta = pickle.load(fh)
    # meta expected keys: 'embeddings' (np.ndarray), 'paths' (list), 'docs' (list)
    return meta


@app.route('/rag/query', methods=['POST'])
def rag_query():
    data = request.get_json(force=True) or {}
    q = data.get('q') or data.get('query') or ''
    top_k = int(data.get('top_k', 5))
    if not q:
        return jsonify({'error': 'q (query) required'}), 400

    meta = load_index()
    if meta is None:
        return jsonify({'error': 'index not found', 'hint': f"Run scripts/ai_improved/build_embeddings.py to build {INDEX_META.name}"}), 404

    # compute query embedding
    if SentenceTransformer is None:
        return jsonify({'error': 'sentence-transformers not installed; install with `pip install sentence-transformers`'}), 500

    model = SentenceTransformer('all-MiniLM-L6-v2')
    q_emb = model.encode([q], normalize_embeddings=True)

    embeddings = meta.get('embeddings')
    paths = meta.get('paths')
    docs = meta.get('docs')

    if embeddings is None or len(embeddings) == 0:
        return jsonify({'error': 'empty index'}), 500

    # Use FAISS if available and saved index present
    results = []
    try:
        if faiss is not None and meta.get('faiss_index_bytes'):
            # reconstruct index from bytes
            index_bytes = meta.get('faiss_index_bytes')
            iv = faiss.deserialize_index(index_bytes)
            D, I = iv.search(np.asarray(q_emb).astype('float32'), top_k)
            scores = D[0].tolist()
            ids = I[0].tolist()
            for sid, sc in zip(ids, scores):
                if sid < 0:
                    continue
                results.append({'path': paths[sid], 'doc': docs[sid], 'score': float(sc)})
        else:
            # fallback: cosine similarity with numpy (embeddings expected normalized)
            # ensure shapes
            emb = np.asarray(embeddings)
            qv = np.asarray(q_emb)[0]
            if emb.ndim == 1:
                emb = emb[np.newaxis, :]
            sims = (emb @ qv).astype(float)
            idx = np.argsort(-sims)[:top_k]
            for i in idx:
                results.append({'path': paths[int(i)], 'doc': docs[int(i)], 'score': float(sims[int(i)])})
    except Exception as e:
        return jsonify({'error': 'search failed', 'detail': str(e)}), 500

    return jsonify({'query': q, 'results': results})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8083)
    args = parser.parse_args()
    app.run(host=args.host, port=args.port)
