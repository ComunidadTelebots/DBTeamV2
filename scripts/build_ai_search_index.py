#!/usr/bin/env python3
"""Build a simple TF-IDF search index over repository text files.

Usage: python scripts/build_ai_search_index.py
It will write the index to `projects/bot/python_bot/data/ai_index.pkl`.
"""
import os
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'projects' / 'bot' / 'python_bot' / 'data'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / 'ai_index.pkl'

EXTS = ('.md', '.txt', '.py', '.html', '.htm')


def collect_files(root: Path):
    docs = []
    paths = []
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in EXTS:
            try:
                text = p.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            if len(text.strip()) < 20:
                continue
            docs.append(text)
            paths.append(str(p.relative_to(root)))
    return paths, docs


def build_tfidf(paths, docs):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except Exception as e:
        print('scikit-learn not available, skipping TF-IDF build:', e)
        return None
    vec = TfidfVectorizer(stop_words='english', max_features=20000)
    mat = vec.fit_transform(docs)
    return {'vectorizer': vec, 'matrix': mat, 'paths': paths, 'docs': docs}


def main():
    repo_root = ROOT
    print('Collecting files...')
    paths, docs = collect_files(repo_root)
    print(f'Collected {len(docs)} documents')
    index = build_tfidf(paths, docs)
    with open(OUT_PATH, 'wb') as f:
        pickle.dump(index, f)
    print('Index saved to', OUT_PATH)


if __name__ == '__main__':
    main()
