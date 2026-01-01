"""Runner for the python_bot using python-telegram-bot (PTB v20+).

This script initializes the `Bot` scaffold, loads plugins, and exposes
registered commands via PTB CommandHandler. It expects `BOT_TOKEN` to be
present in environment variables.
"""
import os
import asyncio
import inspect
import sys
import time
import platform
from pathlib import Path
import traceback

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
    from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, InlineQueryHandler, filters as Filters
except Exception:
    print('python-telegram-bot not installed. Please install requirements.')
    raise

from python_bot.bot import Bot


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _append_botlog(line: str):
    try:
        repo = _repo_root()
        p = repo / 'bot.log'
        with open(p, 'a', encoding='utf-8') as lf:
            lf.write(line + '\n')
    except Exception:
        pass


def _check_token_and_print(token: str):
    # Print basic runtime info
    pid = os.getpid()
    pyv = sys.version.splitlines()[0]
    t = time.asctime()
    min_interval = os.getenv('TELEGRAM_MIN_INTERVAL') or os.getenv('TG_MIN_INTERVAL') or ''
    max_conc = os.getenv('TELEGRAM_MAX_CONCURRENT') or os.getenv('TG_MAX_CONCURRENT') or ''
    header = f"[startup] time={t} pid={pid} python={pyv} platform={platform.platform()} min_interval={min_interval} max_concurrent={max_conc}"
    print(header)
    _append_botlog(header)

    # Check pending outbox/messages via Redis (if available)
    try:
        try:
            import redis as _redis
        except Exception:
            _redis = None
        pending_outbox = None
        pending_web_messages = None
        if _redis is not None:
            try:
                host = os.getenv('REDIS_HOST','127.0.0.1')
                port = int(os.getenv('REDIS_PORT','6379'))
                r = _redis.StrictRedis(host=host, port=port, db=0, decode_responses=True)
                pending_outbox = int(r.llen('web:outbox') or 0)
                pending_web_messages = int(r.llen('web:messages') or 0)
            except Exception:
                pending_outbox = None
                pending_web_messages = None
        info_pending = f"pending_outbox={pending_outbox if pending_outbox is not None else 'n/a'} pending_web_messages={pending_web_messages if pending_web_messages is not None else 'n/a'}"
        print(info_pending)
        _append_botlog('[startup] ' + info_pending)
    except Exception:
        pass

    # Try calling getMe to validate token and detect authorization errors
    try:
        try:
            import requests
        except Exception:
            print('[startup] requests not available, skipping token check')
            _append_botlog('[startup] requests not available, skipping token check')
            return
        url = f'https://api.telegram.org/bot{token}/getMe'
        r = requests.get(url, timeout=5)
        j = r.json() if r.content else {'ok': False, 'description': 'no-response'}
        if not j.get('ok'):
            msg = f"[startup] token check failed: {j.get('error_code')} {j.get('description')}"
            print(msg)
            _append_botlog(msg)
            # specific check for common unauthorized codes
            if j.get('error_code') in (401, 403):
                warn = '[startup] WARNING: Bot token appears invalid or banned/unauthorized. Verify the token and Bot settings.'
                print(warn)
                _append_botlog(warn)
        else:
            res = j.get('result', {})
            info = f"[startup] bot ok: id={res.get('id')} username=@{res.get('username')} name={res.get('first_name')}"
            print(info)
            _append_botlog(info)
    except Exception as e:
        tb = traceback.format_exc()
        print('[startup] token check exception:', e)
        _append_botlog('[startup] token check exception: ' + str(e))
        _append_botlog(tb)
        _append_botlog('[startup] token check exception: ' + str(e))
        _append_botlog(tb)


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
            # Print the error to console. Inline queries may not have update.message.
            print('Handler error:', e)
    return handler


def build_app(token: str) -> 'telegram.ext.Application':
    b = Bot()
    b.start()

    app = ApplicationBuilder().token(token).build()
    # --- Simple rate limiter to reduce Telegram flood risk ---
    # Configurable via env vars:
    # TELEGRAM_MIN_INTERVAL: minimum seconds between requests (default 0.35)
    # TELEGRAM_MAX_CONCURRENT: maximum concurrent send operations (default 2)
    import asyncio
    min_interval = float(os.getenv('TELEGRAM_MIN_INTERVAL') or os.getenv('TG_MIN_INTERVAL') or 0.35)
    max_concurrent = int(os.getenv('TELEGRAM_MAX_CONCURRENT') or os.getenv('TG_MAX_CONCURRENT') or 2)

    class _RateLimiter:
        def __init__(self, interval: float, concurrency: int):
            self.interval = interval
            self.sem = asyncio.Semaphore(concurrency)
            self._lock = asyncio.Lock()
            self._last = 0.0

        async def __aenter__(self):
            await self.sem.acquire()
            await self._wait_interval()
            return self

        async def __aexit__(self, exc_type, exc, tb):
            self._last = asyncio.get_event_loop().time()
            self.sem.release()

        async def _wait_interval(self):
            async with self._lock:
                now = asyncio.get_event_loop().time()
                wait = max(0.0, self.interval - (now - self._last))
                if wait > 0:
                    await asyncio.sleep(wait)

    _rl = _RateLimiter(min_interval, max_concurrent)
    # expose bot scaffold to handlers via bot_data
    app.bot_data['pybot'] = b

    # Monkeypatch common send methods on app.bot to apply rate limiting
    try:
        send_methods = ['send_message', 'send_document', 'send_photo', 'send_video', 'edit_message_text', 'send_media_group', 'forward_message', 'send_audio']
        for name in send_methods:
            orig = getattr(app.bot, name, None)
            if orig is None:
                continue
            async def make_wrapper(orig_fn):
                async def wrapper(*a, **kw):
                    async with _rl:
                        return await orig_fn(*a, **kw)
                return wrapper
            # bind wrapper to instance
            setattr(app.bot, name, asyncio.coroutine(lambda *a, **kw: None))
            # Using closure to set proper orig_fn
            async def _bind_and_replace(orig_fn, attr_name):
                async def wrapper(*a, **kw):
                    async with _rl:
                        return await orig_fn(*a, **kw)
                setattr(app.bot, attr_name, wrapper)
            # schedule immediate binding
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_bind_and_replace(orig, name))
    except Exception:
        # best-effort, don't fail app build if monkeypatching fails
        pass

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

    # register inline query handlers
    for ih in b.get_registered_inline_handlers():
        handler_fn = ih.get('handler')
        if handler_fn is not None:
            app.add_handler(InlineQueryHandler(make_command_handler(handler_fn)))

    # help command
    async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        b_local = context.bot_data.get('pybot')
        if not b_local:
            await update.message.reply_text('Bot runtime not available')
            return
        # Add helpful web links, brief description and login steps to help output
        web_ui = os.getenv('WEBAPP_URL') or 'http://127.0.0.1:8000'
        host_api = os.getenv('STATS_API_URL') or 'http://127.0.0.1:8081'
        desc_lines = [
            'DBTeamV2 is an administration Telegram bot providing moderation, plugin-based features, and a web UI for multimedia and control.',
            f'Web UI: {web_ui}',
            f'Web API: {host_api}',
            'Web login steps: 1) In Telegram use /weblogin to request a code; 2) Open the Web UI and enter the code to verify; 3) Your session will be created.'
        ]
        lines = desc_lines
        lines.append('Available commands:')
        for cmd, md in b_local.get_registered_commands().items():
            lines.append(f'/{cmd} - {md.get("description","")}')
        # send as multiple messages if too long
        payload = '\n'.join(lines) or 'No commands registered'
        if len(payload) > 3000:
            # split into chunks
            parts = [payload[i:i+2500] for i in range(0, len(payload), 2500)]
            for p in parts:
                await update.message.reply_text(p)
        else:
            await update.message.reply_text(payload)

    app.add_handler(CommandHandler('help', help_cmd))

    return app


def main():
    token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print('BOT_TOKEN not set. Set BOT_TOKEN environment variable to run the Telegram bot.')
        sys.exit(1)

    # perform startup checks and print info (including token validation)
    try:
        _check_token_and_print(token)
    except Exception:
        pass

    app = build_app(token)
    print('Starting Telegram bot (polling)...')
    _append_botlog('[startup] Starting Telegram bot (polling)')
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
