"""Core commands and admin utilities for the python_bot.

Implements: /start, /help, /lang, /ban, /unban, /mute (store-only), /plugins,
/reload, /enable, /disable, /broadcast, /stats, /export_settings, /eval, /restart
"""
import os
import sys
import time
import importlib
from typing import Any

from python_bot.bot import Bot
from python_bot.storage import storage


OWNER_ID = int(os.getenv('OWNER_ID', '163103382'))


def setup(bot: Bot):
    bot.register_command('start', start_cmd, 'Start and register chat', plugin='core')
    bot.register_command('help', help_cmd, 'Show help', plugin='core')
    bot.register_command('lang', lang_cmd, 'Set or show language', plugin='core')
    bot.register_command('ban', ban_cmd, 'Ban a chat/user (admin)', plugin='core')
    bot.register_command('unban', unban_cmd, 'Unban (admin)', plugin='core')
    bot.register_command('plugins', plugins_cmd, 'List plugins', plugin='core')
    bot.register_command('reload', reload_cmd, 'Reload plugins', plugin='core')
    bot.register_command('enable', enable_cmd, 'Enable plugin (store only)', plugin='core')
    bot.register_command('disable', disable_cmd, 'Disable plugin (store only)', plugin='core')
    bot.register_command('broadcast', broadcast_cmd, 'Broadcast message (admin)', plugin='core')
    bot.register_command('stats', stats_cmd, 'Show stats', plugin='core')
    bot.register_command('export_settings', export_cmd, 'Export settings as JSON (admin)', plugin='core')
    bot.register_command('eval', eval_cmd, 'Evaluate Python (owner only)', plugin='core')
    bot.register_command('restart', restart_cmd, 'Restart the bot (owner)', plugin='core')


async def start_cmd(update: Any, context: Any):
    chat = update.effective_chat
    user = update.effective_user
    storage.add_chat(chat.id)
    storage.set_lang(chat.id, 'en')
    text = f'Hola {user.first_name if user else ""}! Bienvenido. Escribe /help para ver comandos.'
    await update.message.reply_text(text)


async def help_cmd(update: Any, context: Any):
    b: Bot = context.bot_data.get('pybot')
    if not b:
        await update.message.reply_text('Runtime not available')
        return
    lines = []
    for cmd, md in b.get_registered_commands().items():
        lines.append(f'/{cmd} - {md.get("description","")}')
    await update.message.reply_text('\n'.join(lines) or 'No commands')


async def lang_cmd(update: Any, context: Any):
    chat = update.effective_chat
    args = context.args or []
    if not args:
        cur = storage.get_lang(chat.id) or 'en'
        await update.message.reply_text(f'Current language: {cur}')
        return
    code = args[0].lower()
    storage.set_lang(chat.id, code)
    await update.message.reply_text(f'Language set to {code}')


def _is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    role = storage.get_role(user_id)
    return role in ('owner', 'admin')


async def ban_cmd(update: Any, context: Any):
    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text('Permission denied')
        return
    args = context.args or []
    if not args:
        await update.message.reply_text('Usage: /ban <chat_id>')
        return
    try:
        cid = int(args[0])
        storage.ban_chat(cid)
        await update.message.reply_text(f'Banned {cid}')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')


async def unban_cmd(update: Any, context: Any):
    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text('Permission denied')
        return
    args = context.args or []
    if not args:
        await update.message.reply_text('Usage: /unban <chat_id>')
        return
    try:
        cid = int(args[0])
        storage.unban_chat(cid)
        await update.message.reply_text(f'Unbanned {cid}')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')


async def plugins_cmd(update: Any, context: Any):
    b: Bot = context.bot_data.get('pybot')
    await update.message.reply_text('Plugins: ' + ', '.join(list(b.plugins.keys())))


async def reload_cmd(update: Any, context: Any):
    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text('Permission denied')
        return
    args = context.args or []
    target = args[0] if args else None
    reloaded = []
    failed = []
    b: Bot = context.bot_data.get('pybot')
    for name, mod in list(b.plugins.items()):
        if target and name != target:
            continue
        try:
            importlib.reload(mod)
            setup_fn = getattr(mod, 'setup', None)
            if callable(setup_fn):
                setup_fn(b)
            reloaded.append(name)
        except Exception as e:
            failed.append(f'{name}: {e}')
    await update.message.reply_text(f'Reloaded: {reloaded}\nFailed: {failed}')


async def enable_cmd(update: Any, context: Any):
    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text('Permission denied')
        return
    args = context.args or []
    if not args:
        await update.message.reply_text('Usage: /enable <plugin>')
        return
    plugin = args[0]
    # store as enabled (for future load)
    storage_key = f'plugin_enabled:{plugin}'
    if storage.redis:
        storage.redis.set(storage_key, '1')
    else:
        storage.fallback.set(storage_key, '1')
    await update.message.reply_text(f'Plugin {plugin} marked enabled (reload to apply)')


async def disable_cmd(update: Any, context: Any):
    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text('Permission denied')
        return
    args = context.args or []
    if not args:
        await update.message.reply_text('Usage: /disable <plugin>')
        return
    plugin = args[0]
    storage_key = f'plugin_enabled:{plugin}'
    if storage.redis:
        storage.redis.delete(storage_key)
    else:
        storage.fallback.delete(storage_key)
    await update.message.reply_text(f'Plugin {plugin} marked disabled (reload to apply)')


async def broadcast_cmd(update: Any, context: Any):
    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text('Permission denied')
        return
    text = ' '.join(context.args or [])
    if not text and update.message.reply_to_message:
        # forward replied message text
        text = update.message.reply_to_message.text or ''
    if not text:
        await update.message.reply_text('Usage: /broadcast <text> (or reply to a message)')
        return
    chats = storage.list_chats()
    success = 0
    failed = 0
    token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
    import requests
    for cid in chats:
        try:
            resp = requests.post(f'https://api.telegram.org/bot{token}/sendMessage', data={'chat_id': cid, 'text': text}, timeout=10)
            if resp.status_code == 200:
                success += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f'Broadcast sent: success={success}, failed={failed}')


async def stats_cmd(update: Any, context: Any):
    uptime = int(time.time() - START_TIME)
    b: Bot = context.bot_data.get('pybot')
    plugin_count = len(b.plugins) if b else 0
    chat_count = len(storage.list_chats())
    await update.message.reply_text(f'Uptime: {uptime}s\nPlugins: {plugin_count}\nChats known: {chat_count}')


async def export_cmd(update: Any, context: Any):
    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text('Permission denied')
        return
    data = storage.export_json()
    # send as file via Telegram API
    token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
    import requests
    from io import BytesIO
    buf = BytesIO(data.encode('utf-8'))
    files = {'document': ('settings.json', buf)}
    resp = requests.post(f'https://api.telegram.org/bot{token}/sendDocument', data={'chat_id': user.id}, files=files)
    if resp.status_code == 200:
        await update.message.reply_text('Export sent')
    else:
        await update.message.reply_text(f'Export failed: {resp.status_code}')


async def eval_cmd(update: Any, context: Any):
    user = update.effective_user
    if user.id != OWNER_ID:
        await update.message.reply_text('Owner only')
        return
    code = ' '.join(context.args or [])
    if not code and update.message.reply_to_message:
        code = update.message.reply_to_message.text or ''
    if not code:
        await update.message.reply_text('Usage: /eval <expr>')
        return
    try:
        # dangerous: limited exposure, owner-only
        result = eval(code, {'__builtins__': {}}, {})
        await update.message.reply_text(repr(result)[:3000])
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')


async def restart_cmd(update: Any, context: Any):
    user = update.effective_user
    if user.id != OWNER_ID:
        await update.message.reply_text('Owner only')
        return
    await update.message.reply_text('Restarting...')
    # flush if possible then exit
    sys.exit(0)


# module-level start time
START_TIME = time.time()
