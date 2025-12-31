"""Streaming plugin: send progressive updates to the user by editing a message.

Commands:
- /stream <seconds> <text> : simulate streaming the provided text over <seconds> seconds
- /stream_chunks <interval_ms> <text> : send text in chunks every interval milliseconds

The plugin edits the same message to show progress; suitable for long-running tasks.
"""
import asyncio
from typing import Any


def setup(bot):
    bot.register_command('stream', stream_cmd, 'Stream text over time', plugin='stream')
    bot.register_command('stream_chunks', stream_chunks_cmd, 'Send text in chunks', plugin='stream')


async def stream_cmd(update: Any, context: Any):
    """Stream the provided text by progressively revealing more characters.

Usage: /stream <seconds> <text>
Example: /stream 5 Hola mundo
"""
    args = context.args or []
    if not args:
        await update.message.reply_text('Usage: /stream <seconds> <text>')
        return
    try:
        seconds = float(args[0])
        text = ' '.join(args[1:]) or '...'
    except Exception:
        await update.message.reply_text('Invalid usage. Example: /stream 5 Hola mundo')
        return

    # initial message
    msg = await update.message.reply_text('Streaming...')
    total = len(text)
    steps = max(3, int(seconds * 2))
    for i in range(1, steps + 1):
        # reveal proportionally
        portion = int(total * i / steps)
        new_text = text[:portion]
        try:
            await msg.edit_text(new_text or '...')
        except Exception:
            # in case edit fails (e.g., deleted), send a new message instead
            await update.message.reply_text(new_text or '...')
        await asyncio.sleep(seconds / steps)
    # mark done
    try:
        await msg.edit_text(text)
    except Exception:
        await update.message.reply_text(text)


async def stream_chunks_cmd(update: Any, context: Any):
    """Send the text in chunks at a fixed interval (milliseconds).

Usage: /stream_chunks <interval_ms> <text>
Example: /stream_chunks 500 Esto es una prueba
"""
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text('Usage: /stream_chunks <interval_ms> <text>')
        return
    try:
        interval_ms = int(args[0])
        text = ' '.join(args[1:])
    except Exception:
        await update.message.reply_text('Invalid usage. Example: /stream_chunks 500 Hola')
        return

    chunk_size = 50
    sent_msg = None
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i+chunk_size]
        if sent_msg is None:
            sent_msg = await update.message.reply_text(chunk)
        else:
            try:
                await sent_msg.edit_text(sent_msg.text + chunk)
            except Exception:
                # fallback: send new message
                sent_msg = await update.message.reply_text(chunk)
        await asyncio.sleep(interval_ms / 1000.0)
