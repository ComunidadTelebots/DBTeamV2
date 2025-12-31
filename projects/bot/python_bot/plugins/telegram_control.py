"""Telegram control plugin: simple administrative commands exposed via Telegram.

Registers commands:
- /status  : show basic bot status
- /plugins : list loaded plugins
- /lang <code> : load language module and show a sample string
- /reload [plugin] : attempt to reload plugins (best-effort)

This plugin uses the `bot.register_command` API provided by `python_bot.bot.Bot`.
"""
import importlib
import inspect
from typing import Any


def setup(bot):
    # register commands
    bot.register_command('status', status, 'Show bot status', plugin='telegram_control')
    bot.register_command('plugins', plugins_cmd, 'List loaded plugins', plugin='telegram_control')
    bot.register_command('lang', lang_cmd, 'Load language: /lang <code>', plugin='telegram_control')
    bot.register_command('reload', reload_cmd, 'Reload plugins: /reload [plugin]', plugin='telegram_control')


async def status(update: Any, context: Any):
    """Reply with basic status info."""
    try:
        b = context.bot_data.get('pybot')
        if b is None:
            # fallback: try to access from globals
            await update.message.reply_text('Bot runtime not available (runner did not attach).')
            return
        plugins = list(b.plugins.keys())
        text = f'Bot running. Plugins loaded: {len(plugins)}\n' + ', '.join(plugins or ['(none)'])
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f'Error getting status: {e}')


async def plugins_cmd(update: Any, context: Any):
    try:
        b = context.bot_data.get('pybot')
        if b is None:
            await update.message.reply_text('Bot runtime not available.')
            return
        plugins = list(b.plugins.keys())
        await update.message.reply_text('Plugins: ' + (', '.join(plugins) or '(none)'))
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')


async def lang_cmd(update: Any, context: Any):
    """Change or show language. Usage: /lang [code]"""
    try:
        b = context.bot_data.get('pybot')
        if b is None:
            await update.message.reply_text('Bot runtime not available.')
            return
        args = context.args or []
        if not args:
            # show current english sample
            sample = b.get_text('stats', 'en')
            await update.message.reply_text(f'Sample (en): {sample}')
            return
        code = args[0].lower()
        try:
            b.load_lang(code)
            sample = b.get_text('stats', code)
            await update.message.reply_text(f'Loaded language: {code}\nSample: {sample}')
        except Exception as e:
            await update.message.reply_text(f'Failed to load language {code}: {e}')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')


async def reload_cmd(update: Any, context: Any):
    """Attempt to reload plugins. Usage: /reload [plugin]"""
    try:
        b = context.bot_data.get('pybot')
        if b is None:
            await update.message.reply_text('Bot runtime not available.')
            return
        args = context.args or []
        target = args[0] if args else None
        reloaded = []
        failed = []
        for name, mod in list(b.plugins.items()):
            if target and name != target:
                continue
            try:
                importlib.reload(mod)
                setup_fn = getattr(mod, 'setup', None)
                if callable(setup_fn):
                    # call setup again to re-register commands if needed
                    setup_fn(b)
                reloaded.append(name)
            except Exception as e:
                failed.append(f'{name}: {e}')
        msg = f'Reloaded: {reloaded}\nFailed: {failed}'
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')
