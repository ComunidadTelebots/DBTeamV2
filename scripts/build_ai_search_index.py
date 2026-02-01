#!/usr/bin/env python3
"""
Build an embeddings+FAISS index over repository text files.

This script attempts to use `sentence-transformers` to compute embeddings and `faiss`
to build a similarity index. It writes two files under
`projects/bot/python_bot/data/`:

- `ai_index_faiss.pkl` : pickle containing embeddings (numpy), paths, docs and optional serialized FAISS bytes.
- `ai_index.pkl` : a compatibility file (pickle) containing minimal metadata (paths, docs) so older TF-IDF based code can still read docs.

If `sentence-transformers` is not available the script falls back to the existing TF-IDF approach (requires scikit-learn).

Usage:
  python scripts/build_ai_search_index.py --root . --out projects/bot/python_bot/data/ai_index_faiss.pkl
"""
import argparse
from pathlib import Path
import pickle
import sys
import os
import json

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'projects' / 'bot' / 'python_bot' / 'data'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH_FAISS = OUT_DIR / 'ai_index_faiss.pkl'
OUT_PATH_LEGACY = OUT_DIR / 'ai_index.pkl'

EXTS = ('.md', '.txt', '.py', '.html', '.htm', '.json')


def collect_files(root: Path):
    docs = []
    paths = []
    for p in root.rglob('*'):
        if not (p.is_file() and p.suffix.lower() in EXTS):
            continue
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        if len(text.strip()) < 20:
            continue
        # chunk file into overlapping passages
        chunk_size = 1000
        overlap = 200
        start = 0
        L = len(text)
        idx = 0
        while start < L:
            end = min(L, start + chunk_size)
            chunk = text[start:end].strip()
            if chunk:
                # store as dict with metadata
                docs.append({'text': chunk, 'source': str(p.relative_to(root)), 'start': start, 'end': end, 'chunk_id': idx})
                paths.append(str(p.relative_to(root)) + f"::chunk{idx}")
            if end == L:
                break
            start = end - overlap
            idx += 1
    return paths, docs


def build_with_embeddings(paths, docs, model_name='all-MiniLM-L6-v2'):
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        print('sentence-transformers not available:', e)
        return None
    try:
        import numpy as np
    except Exception:
        print('numpy required')
        return None

    model = SentenceTransformer(model_name)
    print('Computing embeddings with', model_name)
    texts = [d['text'] if isinstance(d, dict) else d for d in docs]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.asarray(embeddings).astype('float32')

    meta = {'embeddings': embeddings, 'paths': paths, 'docs': docs}

    # try to build FAISS index if available
    try:
        import faiss
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)
        meta['faiss_index_bytes'] = faiss.serialize_index(index)
        print('FAISS index created')
    except Exception as e:
        print('FAISS not available or failed to create index:', e)

    return meta


def build_tfidf(paths, docs):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except Exception as e:
        print('scikit-learn not available:', e)
        return None
    vec = TfidfVectorizer(stop_words='english', max_features=20000)
    mat = vec.fit_transform(docs)
    return {'vectorizer': vec, 'matrix': mat, 'paths': paths, 'docs': docs}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.', help='Repository root')
    parser.add_argument('--out', default=str(OUT_PATH_FAISS))
    parser.add_argument('--model', default='all-MiniLM-L6-v2', help='Sentence-transformers model name or local path')
    parser.add_argument('--hf-token', default=None, help='Hugging Face token (or set HUGGINGFACE_HUB_TOKEN env var)')
    parser.add_argument('--faiss-out', default='', help='Optional path to write serialized FAISS bytes')
    parser.add_argument('--incremental', action='store_true', help='Append to existing index if present')
    parser.add_argument('--max-files', type=int, default=0, help='Limit number of files processed (0 = all)')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    print('Collecting files...')
    paths, docs = collect_files(root)
    if args.max_files and len(docs) > args.max_files:
        print(f'Limiting to first {args.max_files} document chunks (of {len(docs)})')
        paths = paths[:args.max_files]
        docs = docs[:args.max_files]
    print(f'Collected {len(docs)} document chunks')

    # Try embeddings flow first
    # Export HF token if provided
    hf_token = args.hf_token or os.environ.get('HUGGINGFACE_HUB_TOKEN') or os.environ.get('HF_TOKEN')
    if hf_token:
        os.environ['HUGGINGFACE_HUB_TOKEN'] = hf_token

    meta = None

    # If incremental and existing index exists, try to load and append
    if args.incremental and OUT_PATH_FAISS.exists():
        try:
            with open(str(OUT_PATH_FAISS), 'rb') as fh:
                existing = pickle.load(fh)
            print('Loaded existing index for incremental update')
            # find new docs not in existing.paths
            existing_paths = existing.get('paths', [])
            new_items = []
            new_paths = []
            for p, d in zip(paths, docs):
                if p not in existing_paths:
                    new_paths.append(p)
                    new_items.append(d)
            if new_items:
                print(f'Found {len(new_items)} new chunks to append')
                new_meta = build_with_embeddings(new_paths, new_items, model_name=args.model)
                if new_meta is not None:
                    try:
                        import numpy as _np
                        emb_existing = existing.get('embeddings')
                        emb_new = new_meta.get('embeddings')
                        if emb_existing is None:
                            emb_combined = emb_new
                        else:
                            emb_combined = _np.vstack([emb_existing, emb_new])
                        existing['embeddings'] = emb_combined
                        existing['paths'] = existing.get('paths', []) + new_meta.get('paths', [])
                        existing['docs'] = existing.get('docs', []) + new_meta.get('docs', [])
                        # rebuild FAISS index from combined embeddings if faiss bytes present
                        try:
                            import faiss
                            dim = emb_combined.shape[1]
                            idx = faiss.IndexFlatIP(dim)
                            idx.add(emb_combined)
                            existing['faiss_index_bytes'] = faiss.serialize_index(idx)
                        except Exception:
                            pass
                        meta = existing
                    except Exception as e:
                        print('Failed to merge embeddings for incremental update:', e)
                        meta = None
                else:
                    print('Failed to compute embeddings for new items; skipping incremental')
            else:
                print('No new items to append; using existing index')
                meta = existing
        except Exception as e:
            print('Could not load existing index for incremental mode:', e)

    if meta is None:
        meta = build_with_embeddings(paths, docs, model_name=args.model)
    if meta is not None:
        # Ensure embeddings numpy arrays are standard Python types for pickle
        try:
            # convert numpy arrays to ndarray of float32 if present
            import numpy as _np
            if isinstance(meta.get('embeddings'), _np.ndarray):
                meta['embeddings'] = meta['embeddings'].astype('float32')
        except Exception:
            pass

        with open(args.out, 'wb') as fh:
            pickle.dump(meta, fh)
        # write legacy minimal index as well
        legacy = {'paths': meta.get('paths', paths), 'docs': meta.get('docs', docs)}
        with open(str(OUT_PATH_LEGACY), 'wb') as fh:
            pickle.dump(legacy, fh)
        print('Saved embeddings index to', args.out)
        print('Saved legacy index to', OUT_PATH_LEGACY)
        # optionally write faiss bytes to a separate file
        if args.faiss_out and meta.get('faiss_index_bytes'):
            try:
                with open(args.faiss_out, 'wb') as fh:
                    fh.write(meta.get('faiss_index_bytes'))
                print('Saved faiss bytes to', args.faiss_out)
            except Exception as e:
                print('Failed to write faiss bytes to faiss_out:', e)
        return

    # fallback to TF-IDF
    print('Falling back to TF-IDF index')
    idx = build_tfidf(paths, docs)
    if idx is None:
        print('No index could be built; install sentence-transformers or scikit-learn')
        sys.exit(2)
    with open(str(OUT_PATH_LEGACY), 'wb') as fh:
        pickle.dump(idx, fh)
    print('Saved TF-IDF index to', OUT_PATH_LEGACY)


if __name__ == '__main__':
    main()
