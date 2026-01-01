"""AI-powered search plugin (small local model using TF-IDF).

Provides:
- Command: `/aisearch <query>` — sends top result as a message.
- Inline mode: `@YourBot <query>` — returns top K results as inline articles.

Requires building the index first with `python scripts/build_ai_search_index.py`.
If scikit-learn isn't available the plugin falls back to a simple substring ranker.
"""
import os
import pickle
from typing import Any, List, Tuple
from pathlib import Path

INDEX_PATH = Path(__file__).resolve().parents[2] / 'data' / 'ai_index.pkl'


def _load_index():
    if not INDEX_PATH.exists():
        return None
    try:
        with open(INDEX_PATH, 'rb') as f:
            idx = pickle.load(f)
        return idx
    except Exception:
        return None


def _simple_search(query: str, paths: List[str], docs: List[str]) -> List[Tuple[float, str, str]]:
    q = query.lower()
    results = []
    for p, d in zip(paths, docs):
        txt = d.lower()
        score = txt.count(q)
        if score > 0:
            snippet = d.strip().replace('\n', ' ')[:400]
            results.append((float(score), p, snippet))
    results.sort(key=lambda x: x[0], reverse=True)
    return results


def _tfidf_search(query: str, index, topk: int = 5):
    try:
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity
    except Exception:
        return []
    vec = index.get('vectorizer')
    mat = index.get('matrix')
    paths = index.get('paths')
    docs = index.get('docs')
    if vec is None or mat is None:
        return []
    qv = vec.transform([query])
    sims = cosine_similarity(qv, mat).ravel()
    idxs = list((-sims).argsort()[:topk])
    results = []
    for i in idxs:
        score = float(sims[i])
        snippet = docs[i].strip().replace('\n', ' ')[:500]
        results.append((score, paths[i], snippet))
    return results


async def aisearch_cmd(update: Any, context: Any):
    args = context.args or []
    if not args:
        await update.message.reply_text('Usage: /aisearch <query>')
        return
    q = ' '.join(args).strip()
    idx = _load_index()
    if idx is None:
        await update.message.reply_text('Index not found. Run `python scripts/build_ai_search_index.py`')
        return
    results = _tfidf_search(q, idx, topk=3)
    if not results:
        # try substring fallback
        results = _simple_search(q, idx.get('paths', []), idx.get('docs', []))[:3]
    if not results:
        await update.message.reply_text('No results')
        return
    lines = []
    for score, path, snippet in results:
        lines.append(f'[{path}] (score={score:.3f})\n{snippet[:400]}')
    await update.message.reply_text('\n\n'.join(lines))


async def inline_aisearch_handler(update: Any, context: Any):
    iq = getattr(update, 'inline_query', None)
    if iq is None:
        return
    q = (iq.query or '').strip()
    if not q:
        return
    idx = _load_index()
    results = []
    if idx is not None and idx.get('vectorizer') is not None:
        results = _tfidf_search(q, idx, topk=5)
    elif idx is not None:
        results = _simple_search(q, idx.get('paths', []), idx.get('docs', []))[:5]
    # build InlineQueryResultArticle objects
    try:
        from telegram import InlineQueryResultArticle, InputTextMessageContent
        import uuid
    except Exception:
        return
    out = []
    for score, path, snippet in results:
        title = f'{path} — {score:.3f}'
        content = snippet or ''
        out.append(InlineQueryResultArticle(id=str(uuid.uuid4()), title=title,
                                            input_message_content=InputTextMessageContent(content),
                                            description=(snippet[:60] if snippet else '')))
    try:
        await iq.answer(out, cache_time=5)
    except Exception:
        pass


def setup(bot):
    bot.register_command('aisearch', aisearch_cmd, 'AI-powered search (local index)', plugin='ai_search')
    bot.register_inline_handler(inline_aisearch_handler, plugin='ai_search')
