"""MiniApp plugin

Provides a tiny example app with a few commands and an inline handler.

Commands:
- /miniapp -> show menu
- /mini_set <key> <value> -> store a value per-chat
- /mini_get <key> -> retrieve stored value
- /mini_echo <text> -> echo text back

Also responds to plain text "ping" with "pong" and supports a simple
inline search that echoes the query.
"""
import uuid
from typing import Any

from python_bot.storage import storage
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
try:
    from telegram import WebAppInfo
except Exception:
    WebAppInfo = None


async def miniapp_cmd(update: Any, context: Any):
    text = (
        "MiniApp commands:\n"
        "/mini_set <key> <value> - store a value for this chat\n"
        "/mini_get <key> - get stored value\n"
        "/mini_echo <text> - echo back the text\n"
        "/miniapp - show this help"
    )
    try:
        await update.message.reply_text(text)
    except Exception:
        pass


async def mini_set_cmd(update: Any, context: Any):
    args = getattr(context, 'args', []) or []
    if len(args) < 2:
        try:
            await update.message.reply_text('Usage: /mini_set <key> <value>')
        except Exception:
            pass
        return
    key = args[0]
    value = ' '.join(args[1:])
    chat_id = update.effective_chat.id if update.effective_chat else 'global'
    sk = f'mini:{chat_id}:{key}'
    try:
        storage.set(sk, value)
        await update.message.reply_text(f'Saved {key} = {value}')
    except Exception:
        try:
            await update.message.reply_text('Failed to save value')
        except Exception:
            pass


async def mini_get_cmd(update: Any, context: Any):
    args = getattr(context, 'args', []) or []
    if len(args) < 1:
        try:
            await update.message.reply_text('Usage: /mini_get <key>')
        except Exception:
            pass
        return
    key = args[0]
    chat_id = update.effective_chat.id if update.effective_chat else 'global'
    sk = f'mini:{chat_id}:{key}'
    try:
        v = storage.get(sk)
        if v is None:
            await update.message.reply_text(f'{key} not found')
        else:
            await update.message.reply_text(f'{key} = {v}')
    except Exception:
        try:
            await update.message.reply_text('Failed to read value')
        except Exception:
            pass


async def mini_echo_cmd(update: Any, context: Any):
    text = ' '.join(getattr(context, 'args', []) or [])
    if not text:
        try:
            await update.message.reply_text('Usage: /mini_echo <text>')
        except Exception:
            pass
        return
    try:
        await update.message.reply_text(text)
    except Exception:
        pass


async def text_handler(update: Any, context: Any):
    """Simple text handler: respond to 'ping' or messages starting with 'mini:'"""
    msg = getattr(update, 'message', None)
    if msg is None or not getattr(msg, 'text', None):
        return
    t = msg.text.strip().lower()
    try:
        if t == 'ping':
            await msg.reply_text('pong')
            return
        if t.startswith('mini:'):
            # mini:echo hello -> reply with content after prefix
            payload = msg.text.split(':', 1)[1].strip()
            if payload:
                await msg.reply_text(f'Mini-prefix received: {payload}')
            return
    except Exception:
        pass


async def inline_mini_handler(update: Any, context: Any):
    iq = getattr(update, 'inline_query', None)
    if iq is None:
        return
    q = (iq.query or '').strip()
    from telegram import InlineQueryResultArticle, InputTextMessageContent

    results = []
    title = f'Mini echo: {q[:50] or "(empty)"}'
    results.append(InlineQueryResultArticle(
        id=str(uuid.uuid4()),
        title=title,
        input_message_content=InputTextMessageContent(f'You asked: {q}'),
        description='Echo your inline query'
    ))
    try:
        await iq.answer(results, cache_time=5)
    except Exception:
        pass


def setup(bot):
    bot.register_command('miniapp', miniapp_cmd, 'Show miniapp help', plugin='miniapp')
    bot.register_command('mini_set', mini_set_cmd, 'Set a key for this chat', plugin='miniapp')
    bot.register_command('mini_get', mini_get_cmd, 'Get a key for this chat', plugin='miniapp')
    bot.register_command('mini_echo', mini_echo_cmd, 'Echo text', plugin='miniapp')
    bot.register_command('webapp', webapp_cmd, 'Open the mini Web App', plugin='miniapp')
    bot.register_message_handler('text', text_handler, plugin='miniapp')
    bot.register_inline_handler(inline_mini_handler, plugin='miniapp')


async def webapp_cmd(update: Any, context: Any):
    """Send a message with a Web App button.

    Reads `WEBAPP_URL` env var or defaults to the local static server.
    """
    url = os.getenv('WEBAPP_URL') or 'http://127.0.0.1:8000/miniapp_webapp.html'
    try:
        if WebAppInfo is not None:
            web = WebAppInfo(url=url)
            button = InlineKeyboardButton('Open mini Web App', web_app=web)
        else:
            # fallback: send a URL button (opens in external browser)
            button = InlineKeyboardButton('Open mini Web App', url=url)
        kb = InlineKeyboardMarkup([[button]])
        await update.message.reply_text('Open the MiniApp using the button below:', reply_markup=kb)
    except Exception:
        try:
            await update.message.reply_text(f'Open: {url}')
        except Exception:
            pass
