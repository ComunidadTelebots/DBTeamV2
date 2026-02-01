#!/usr/bin/env python3
"""
Build embeddings for repository text files and save a pickle index that `rag_server.py` can load.

Output: projects/bot/python_bot/data/ai_index_faiss.pkl

This script is intentionally conservative and depends on `sentence-transformers` and optionally `faiss`.
If `faiss` is available, it will include a serialized FAISS index bytes in the saved pickle.

Usage: python scripts/ai_improved/build_embeddings.py --src README.md --out projects/bot/python_bot/data/ai_index_faiss.pkl
"""
import argparse
from pathlib import Path
import os
import pickle
import sys
import json
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

try:
    import faiss
except Exception:
    faiss = None


TEXT_EXT = {'.md', '.txt', '.py', '.html', '.json'}


def collect_files(root: Path):
    files = []
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in TEXT_EXT:
            files.append(p)
    return files


def read_text(p: Path):
    try:
        return p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.', help='Repository root to scan')
    parser.add_argument('--out', default='projects/bot/python_bot/data/ai_index_faiss.pkl')
    parser.add_argument('--model', default='all-MiniLM-L6-v2')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    files = collect_files(root)
    print(f'Found {len(files)} candidate files under {root}')

    docs = []
    paths = []
    for f in files:
        txt = read_text(f).strip()
        if not txt:
            continue
        docs.append(txt)
        paths.append(str(f.relative_to(root)))

    if not docs:
        print('No documents collected, aborting')
        sys.exit(1)

    if SentenceTransformer is None:
        print('sentence-transformers not installed. pip install sentence-transformers', file=sys.stderr)
        sys.exit(2)

    model = SentenceTransformer(args.model)
    embeddings = model.encode(docs, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.asarray(embeddings).astype('float32')

    meta = {'embeddings': embeddings, 'paths': paths, 'docs': docs}

    if faiss is not None:
        try:
            dim = embeddings.shape[1]
            index = faiss.IndexFlatIP(dim)
            index.add(embeddings)
            # serialize index to bytes
            index_bytes = faiss.serialize_index(index)
            meta['faiss_index_bytes'] = index_bytes
            print('FAISS index created and serialized')
        except Exception as e:
            print('FAISS create failed:', e)

    with open(str(out), 'wb') as fh:
        pickle.dump(meta, fh)

    print('Saved index to', out)


if __name__ == '__main__':
    main()
