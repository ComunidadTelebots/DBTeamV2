"""RAG retrieval utilities: load/save index, embedding helpers and retrieval.

This module centralizes retrieval logic so `ai_server.py` (or other services)
can optionally import and use it without duplicating code.
"""
from pathlib import Path
from typing import Optional, List, Dict, Any
import pickle
import json

def load_index(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if path is None:
        repo = Path(__file__).resolve().parents[1]
        path = repo / 'projects' / 'bot' / 'python_bot' / 'data' / 'ai_index_faiss.pkl'
    p = Path(path)
    if not p.exists():
        return None
    try:
        with open(str(p), 'rb') as fh:
            meta = pickle.load(fh)
        return meta
    except Exception:
        return None


def save_index(meta: Dict[str, Any], path: str) -> bool:
    try:
        with open(path, 'wb') as fh:
            pickle.dump(meta, fh)
        return True
    except Exception:
        return False


def ensure_embedder(name: str = 'all-MiniLM-L6-v2'):
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None
    try:
        return SentenceTransformer(name)
    except Exception:
        return None


def retrieve_embeddings(meta: Dict[str, Any], q_emb, top_k: int = 5):
    try:
        import numpy as np
    except Exception:
        return []
    embeddings = meta.get('embeddings')
    paths = meta.get('paths')
    docs = meta.get('docs')
    if embeddings is None or len(embeddings) == 0:
        return []
    try:
        try:
            import faiss
        except Exception:
            faiss = None
        if faiss is not None and meta.get('faiss_index_bytes'):
            iv = faiss.deserialize_index(meta.get('faiss_index_bytes'))
            D, I = iv.search(np.asarray(q_emb).astype('float32'), top_k)
            ids = I[0].tolist(); scores = D[0].tolist()
            out = []
            for sid, sc in zip(ids, scores):
                if sid < 0:
                    continue
                out.append({'path': paths[sid], 'doc': docs[sid], 'score': float(sc)})
            return out
        emb = np.asarray(embeddings)
        qv = np.asarray(q_emb)[0]
        sims = (emb @ qv).astype(float)
        idx = np.argsort(-sims)[:top_k]
        out = []
        for i in idx:
            out.append({'path': paths[int(i)], 'doc': docs[int(i)], 'score': float(sims[int(i)])})
        return out
    except Exception:
        return []


def hybrid_retrieve(meta: Dict[str, Any], q_emb, query: str, top_k: int = 5, alpha: float = 0.6):
    """Combine embedding similarity with TF-IDF ranking.

    Returns list of results with fields: path, doc, score, emb_score, tfidf_score
    """
    try:
        import numpy as np
    except Exception:
        return retrieve_embeddings(meta, q_emb, top_k=top_k)

    emb_cands = retrieve_embeddings(meta, q_emb, top_k=max(top_k * 3, 20))
    emb_map = {}
    for r in emb_cands:
        try:
            idx = meta.get('paths', []).index(r.get('path'))
        except Exception:
            idx = None
        emb_map[idx] = float(r.get('score', 0.0))

    docs = meta.get('docs') or []
    texts = [d.get('text') if isinstance(d, dict) else str(d) for d in docs]

    tfidf_vec = meta.get('_tfidf_vectorizer')
    tfidf_mat = meta.get('_tfidf_matrix')
    if tfidf_vec is None or tfidf_mat is None:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            tfidf_vec = TfidfVectorizer(stop_words='english', max_features=20000)
            tfidf_mat = tfidf_vec.fit_transform(texts)
            meta['_tfidf_vectorizer'] = tfidf_vec
            meta['_tfidf_matrix'] = tfidf_mat
        except Exception:
            tfidf_vec = None
            tfidf_mat = None

    tfidf_scores = None
    if tfidf_vec is not None and tfidf_mat is not None:
        try:
            qv = tfidf_vec.transform([query])
            from sklearn.metrics.pairwise import linear_kernel
            sim = linear_kernel(qv, tfidf_mat).flatten()
            tfidf_scores = sim
        except Exception:
            tfidf_scores = None

    results = []
    N = len(texts)
    emb_vals = np.array(list(emb_map.values())) if emb_map else np.array([0.0])
    emb_max = float(np.max(emb_vals)) if emb_vals.size else 0.0
    tfidf_max = float(tfidf_scores.max()) if tfidf_scores is not None and len(tfidf_scores) else 0.0

    candidate_idxs = set(k for k in emb_map.keys() if k is not None)
    if tfidf_scores is not None:
        top_tfidf = list(np.argsort(-tfidf_scores)[: max(top_k * 5, 50)])
        candidate_idxs.update(top_tfidf)
    if not candidate_idxs:
        candidate_idxs = set(range(min(N, top_k)))

    for idx in candidate_idxs:
        if idx is None or idx < 0 or idx >= N:
            continue
        emb_s = float(emb_map.get(idx, 0.0))
        tf_s = float(tfidf_scores[idx]) if (tfidf_scores is not None and idx < len(tfidf_scores)) else 0.0
        emb_norm = (emb_s / emb_max) if emb_max > 0 else emb_s
        tf_norm = (tf_s / tfidf_max) if tfidf_max > 0 else tf_s
        combined = alpha * emb_norm + (1.0 - alpha) * tf_norm
        results.append({'path': meta.get('paths', [])[idx] if meta.get('paths') and idx < len(meta.get('paths')) else None,
                        'doc': texts[idx], 'score': float(combined), 'emb_score': float(emb_s), 'tfidf_score': float(tf_s)})

    results = sorted(results, key=lambda x: -x.get('score', 0.0))[:top_k]
    return results
