"""Simple inline-mode test plugin.

Usage: in any chat type `@YourBot <query>` and it will return test articles.
"""
import uuid
from typing import Any


async def inline_test_handler(update: Any, context: Any):
    iq = getattr(update, 'inline_query', None)
    if iq is None:
        return
    q = (iq.query or '').strip()
    from telegram import InlineQueryResultArticle, InputTextMessageContent

    results = []
    # Echo result
    title = f'Echo: {q[:50] or "(empty)"}'
    results.append(InlineQueryResultArticle(
        id=str(uuid.uuid4()),
        title=title,
        input_message_content=InputTextMessageContent(f'You searched: {q}'),
        description='Echoes your query back'
    ))

    # Example torrent/help result
    example = 'Try: sintel trailer or paste an infohash/magnet'
    results.append(InlineQueryResultArticle(
        id=str(uuid.uuid4()),
        title='Example search',
        input_message_content=InputTextMessageContent(example),
        description='Helpful example to test inline mode'
    ))

    try:
        await iq.answer(results, cache_time=5)
    except Exception:
        try:
            # best-effort: ignore failures
            pass
        except Exception:
            pass


def setup(bot):
    bot.register_inline_handler(inline_test_handler, plugin='inline_test')
