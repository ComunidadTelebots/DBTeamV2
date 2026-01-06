"""Web control plugin (renamed from telegram_control.py).

Exposes administrative commands via Telegram (status, plugins, lang, reload, ping, reloadbg).
This module is a rename of projects/bot/python_bot/plugins/telegram_control.py —
plugin registration names updated to `web_controler`.
"""
import importlib
import inspect
import os
import subprocess
import threading
import time
from typing import Any
from python_bot.storage import storage


def setup(bot):
    # register commands
    bot.register_command('status', status, 'Show bot status', plugin='web_controler')
    bot.register_command('plugins', plugins_cmd, 'List loaded plugins', plugin='web_controler')
    bot.register_command('lang', lang_cmd, 'Load language: /lang <code>', plugin='web_controler')
    bot.register_command('reload', reload_cmd, 'Reload plugins: /reload [plugin]', plugin='web_controler')
    bot.register_command('ping', ping_cmd, 'Ping the bot to check liveness', plugin='web_controler')
    bot.register_command('reloadbg', reloadbg_cmd, 'Restart the bot in background (owner only)', plugin='web_controler')


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


async def ping_cmd(update: Any, context: Any):
    """Simple ping/pong to check bot is responsive."""
    try:
        await update.message.reply_text('pong')
    except Exception:
        pass


async def reloadbg_cmd(update: Any, context: Any):
    """Restart the bot in background using the wrapper script. Owner/admin only."""
    try:
        user = update.effective_user
        if not user:
            return
        role = storage.get_role(user.id)
        if role not in ('owner', 'admin'):
            await update.message.reply_text('Permission denied')
            return
        await update.message.reply_text('Restarting bot in background...')
        # spawn the wrapper via PowerShell to start a fresh bot process
        try:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
            wrapper = os.path.join(repo_root, '.run_bot_wrapper.ps1')
            # verify wrapper integrity via checksums API if available
            try:
                from python_bot.utils import compute_file_sha256, verify_local_with_checksums_api
                if os.path.exists(wrapper):
                    local_hash = compute_file_sha256(wrapper)
                    v = verify_local_with_checksums_api(os.path.basename(wrapper), local_hash)
                    if v is False:
                        await update.message.reply_text('La verificación de integridad del wrapper ha fallado. No se reiniciará el bot.')
                        return
            except Exception:
                # if verification toolchain not available, continue but warn
                try:
                    await update.message.reply_text('Aviso: no se pudo verificar firma/hash del wrapper; procediendo bajo su responsabilidad.')
                except Exception:
                    pass
            # fire-and-forget
            subprocess.Popen(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', wrapper], cwd=repo_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            await update.message.reply_text(f'Failed to spawn wrapper: {e}')
            return
        # schedule exit of current process after short delay so reply is delivered
        def _exit_after_delay():
            time.sleep(1)
            try:
                os._exit(0)
            except Exception:
                pass
        threading.Thread(target=_exit_after_delay, daemon=True).start()
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')
