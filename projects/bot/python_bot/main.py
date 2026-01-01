"""Runner for the python_bot using python-telegram-bot (PTB v20+).

This script initializes the `Bot` scaffold, loads plugins, and exposes
registered commands via PTB CommandHandler. It expects `BOT_TOKEN` to be
present in environment variables.
"""
import os
import asyncio
import inspect
import sys

# Ensure a suitable event loop policy on Windows so PTB can create/get the loop
if sys.platform.startswith('win'):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        # If the policy isn't available for some Python builds, ignore
        pass

# Ensure there's an event loop available (addresses some Windows/python versions)
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

try:
    from telegram import Update
    from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters as Filters
except Exception:
    print('python-telegram-bot not installed. Please install requirements.')
    raise

from python_bot.bot import Bot


def make_command_handler(fn):
    """Wrap plugin handler `fn` into an async function acceptable by PTB."""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if inspect.iscoroutinefunction(fn):
                await fn(update, context)
            else:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, fn, update, context)
        except Exception as e:
            try:
                await update.message.reply_text(f'Handler error: {e}')
            except Exception:
                print('Failed to send error reply:', e)
    return handler


def build_app(token: str) -> 'telegram.ext.Application':
    b = Bot()
    b.start()

    app = ApplicationBuilder().token(token).build()
    # expose bot scaffold to handlers via bot_data
    app.bot_data['pybot'] = b

    # register commands discovered by plugins
    for name, meta in b.get_registered_commands().items():
        handler_fn = meta.get('handler')
        if handler_fn is None:
            continue
        app.add_handler(CommandHandler(name, make_command_handler(handler_fn)))

    # register message handlers (plugins can register by filter string)
    for mh in b.get_registered_message_handlers():
        f_str = mh.get('filter', 'document')
        handler_fn = mh.get('handler')
        # map filter strings to PTB filters
        filt = None
        parts = [p.strip() for p in f_str.split('|') if p.strip()]
        for p in parts:
            p_low = p.lower()
            if p_low == 'document':
                f = Filters.Document.ALL
            elif p_low == 'video':
                f = Filters.VIDEO
            elif p_low == 'audio':
                f = Filters.AUDIO
            elif p_low == 'photo':
                f = Filters.PHOTO
            elif p_low == 'text':
                f = Filters.TEXT
            else:
                f = None
            if f is not None:
                filt = f if filt is None else (filt | f)
        if filt is not None and handler_fn is not None:
            app.add_handler(MessageHandler(filt, make_command_handler(handler_fn)))

    # help command
    async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        b_local = context.bot_data.get('pybot')
        if not b_local:
            await update.message.reply_text('Bot runtime not available')
            return
        lines = []
        for cmd, md in b_local.get_registered_commands().items():
            lines.append(f'/{cmd} - {md.get("description","")}')
        await update.message.reply_text('\n'.join(lines) or 'No commands registered')

    app.add_handler(CommandHandler('help', help_cmd))

    return app


def main():
    token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print('BOT_TOKEN not set. Set BOT_TOKEN environment variable to run the Telegram bot.')
        sys.exit(1)

    app = build_app(token)
    print('Starting Telegram bot (polling)...')
    app.run_polling()


if __name__ == '__main__':
    main()
"""Entry point for python_bot skeleton.
"""
from python_bot.bot import Bot


def main():
    bot = Bot()
    bot.start()


if __name__ == '__main__':
    main()
