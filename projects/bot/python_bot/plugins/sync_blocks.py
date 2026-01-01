"""Plugin: sync_blocks

Integrates with external spam/blocklist APIs (cas.chat and others).

Commands:
- /syncblocks — download configured blocklists and store them in Redis
- /applyblocks — apply stored blocklist to the current chat (requires admin)

Configuration via environment variables:
- BLOCK_SOURCES: comma-separated URLs to fetch lists from (defaults to https://cas.chat/api)
- API_BASE: fallback API base (used if BLOCK_SOURCES not set)
"""
from typing import Any, List
import os
import re
import requests

from python_bot.storage import storage

patterns = [
    r"^[!/](syncblocks)$",
    r"^[!/](sync_blocks)$",
    r"^[!/](applyblocks)$",
    r"^[!/](apply_blocks)$",
    r"^[!/](lists)$",
    r"^[!/](showblocks)$",
    r"^[!/](show_blocks)$",
]


# expose command to list known chats when used in private
patterns += [r"^[!/](chats)$", r"^[!/](mychats)$"]

_bot = None


def setup(bot):
    global _bot
    _bot = bot
    try:
        bot.register_command('syncblocks', syncblocks_cmd, description='Sync blocklist from external APIs', plugin='sync_blocks')
        bot.register_command('sync_blocks', syncblocks_cmd, description='Sync blocklist from external APIs', plugin='sync_blocks')
        bot.register_command('applyblocks', applyblocks_cmd, description='Apply stored blocklist to this chat', plugin='sync_blocks')
        bot.register_command('apply_blocks', applyblocks_cmd, description='Apply stored blocklist to this chat', plugin='sync_blocks')
        bot.register_command('lists', lists_cmd, description='Show configured block sources', plugin='sync_blocks')
        bot.register_command('showblocks', showblocks_cmd, description='Show stored blocklist summary', plugin='sync_blocks')
        bot.register_command('show_blocks', showblocks_cmd, description='Show stored blocklist summary', plugin='sync_blocks')
        bot.register_command('chats', chats_cmd, description='List known chats (use from private)', plugin='sync_blocks')
        bot.register_command('mychats', chats_cmd, description='List known chats (use from private)', plugin='sync_blocks')
    except Exception:
        pass


def _get_sources() -> List[str]:
    env = os.getenv('BLOCK_SOURCES')
    if env:
        parts = [p.strip() for p in env.split(',') if p.strip()]
        if parts:
            return parts
    # fallback to API_BASE or cas.chat
    api_base = os.getenv('API_BASE')
    if api_base:
        return [api_base.rstrip('/')]
    return ['https://cas.chat/api']


def _fetch_from_source(url: str) -> List[int]:
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        # try JSON keys
        try:
            j = r.json()
            blocked = j.get('blocked_ids') or j.get('blocked') or j.get('ids') or j.get('data')
            if isinstance(blocked, list):
                return [int(x) for x in blocked if str(x).lstrip('-').isdigit()]
        except Exception:
            text = r.text or ''
            ids = re.findall(r"\b\d{5,}\b", text)
            return [int(x) for x in ids]
    except Exception:
        return []


def syncblocks_cmd(update: Any, context: Any):
    """Synchronous handler invoked by runner wrapper; returns a text reply."""
    try:
        # runner calls sync functions inside executor; update/context are PTB objects
        chat = update.effective_chat
        user = update.effective_user
        chat_id = chat.id
        user_id = user.id
    except Exception:
        return 'Context unavailable'

    # permission: allow if in SUDO_USERS env or chat admin
    sudo_env = os.getenv('SUDO_USERS', '')
    allowed = False
    try:
        if sudo_env:
            s = [int(x) for x in sudo_env.split(',') if x.strip()]
            if user_id in s:
                allowed = True
    except Exception:
        allowed = False

    if not allowed:
        try:
            mem = context.bot.get_chat_member(chat_id, user_id)
            if getattr(mem, 'status', '').lower() in ('administrator', 'creator'):
                allowed = True
        except Exception:
            allowed = False

    if not allowed:
        return '🚫 Solo administradores pueden ejecutar este comando.'

    sources = _get_sources()
    total = set()
    for s in sources:
        ids = _fetch_from_source(s)
        for i in ids:
            total.add(int(i))

    # persist into storage set 'blocked_ids'
    key = storage._skey('blocked_ids')
    if storage.redis:
        if total:
            storage.redis.delete(key)
            storage.redis.sadd(key, *list(total))
    else:
        # fallback: store as a set under fallback store
        storage.fallback.set(key, list(total))

    return f'✅ Sincronizado: {len(total)} IDs importados desde {len(sources)} fuente(s).'


def applyblocks_cmd(update: Any, context: Any):
    try:
        chat = update.effective_chat
        user = update.effective_user
        chat_id = chat.id
        user_id = user.id
    except Exception:
        return 'Context unavailable'

    # Parse optional target from message text (allow /applyblocks <chat_id|@username>)
    target_chat_id = None
    try:
        text = getattr(update.message, 'text', '') or ''
        parts = text.split()
        if len(parts) > 1:
            targ = parts[1].strip()
            # numeric id
            if targ.lstrip('-').isdigit():
                target_chat_id = int(targ)
            else:
                # try as @username
                try:
                    c = context.bot.get_chat(targ)
                    target_chat_id = c.id
                except Exception:
                    target_chat_id = None
    except Exception:
        target_chat_id = None

    # permission check
    sudo_env = os.getenv('SUDO_USERS', '')
    allowed = False
    try:
        if sudo_env:
            s = [int(x) for x in sudo_env.split(',') if x.strip()]
            if user_id in s:
                allowed = True
    except Exception:
        allowed = False

    if not allowed:
        try:
            mem = context.bot.get_chat_member(chat_id, user_id)
            if getattr(mem, 'status', '').lower() in ('administrator', 'creator'):
                allowed = True
        except Exception:
            allowed = False

    if not allowed:
        return '🚫 Solo administradores pueden ejecutar este comando.'

    # load blocked ids from storage
    key = storage._skey('blocked_ids')
    blocked = []
    if storage.redis:
        try:
            blocked = [int(x) for x in storage.redis.smembers(key) or []]
        except Exception:
            blocked = []
    else:
        blocked = storage.fallback.get(key) or []

    if not blocked:
        return 'No hay IDs bloqueadas en el almacenamiento. Ejecuta /syncblocks primero.'

    # If called from private and no target specified, show user's chats and usage
    if getattr(chat, 'type', '') == 'private' and not target_chat_id:
        chats = storage.list_chats()
        if not chats:
            return 'No tengo chats registrados. Añádeme a un grupo o usa /syncblocks en un grupo primero.'
        lines = []
        for cid in chats[:50]:
            try:
                c = context.bot.get_chat(cid)
                title = getattr(c, 'title', None) or getattr(c, 'username', None) or str(cid)
            except Exception:
                title = str(cid)
            lines.append(f'{title} ({cid})')
        lines.append('\nUsa: /applyblocks <chat_id> para aplicar la lista en ese chat.')
        return 'Chats conocidos:\n' + '\n'.join(lines)

    success = 0
    failed = 0
    errors = []
    # decide where to apply
    dest_chat = target_chat_id or chat_id

    # permission: if applying to a different chat, ensure caller is admin there or sudo
    if dest_chat != chat_id:
        # re-check allowed for target chat
        allowed_target = False
        try:
            if sudo_env:
                s = [int(x) for x in sudo_env.split(',') if x.strip()]
                if user_id in s:
                    allowed_target = True
        except Exception:
            allowed_target = False
        if not allowed_target:
            try:
                mem = context.bot.get_chat_member(dest_chat, user_id)
                if getattr(mem, 'status', '').lower() in ('administrator', 'creator'):
                    allowed_target = True
            except Exception:
                allowed_target = False
        if not allowed_target:
            return '🚫 No tienes permisos en el chat objetivo para aplicar los baneos.'

    for uid in blocked:
        try:
            context.bot.ban_chat_member(chat_id=dest_chat, user_id=int(uid))
            success += 1
        except Exception as e:
            failed += 1
            errors.append(f'{uid}: {e}')

    summary = f'✅ Baneos aplicados: {success} · fallidos: {failed}'
    if failed:
        summary += '\nErrores: ' + '; '.join(errors[:5])
    return summary


def lists_cmd(update: Any, context: Any):
    """Return configured block sources."""
    sources = _get_sources()
    if not sources:
        return 'No hay fuentes configuradas.'
    lines = [f'- {s}' for s in sources]
    return f'Fuentes configuradas ({len(sources)}):\n' + '\n'.join(lines)


def chats_cmd(update: Any, context: Any):
    """Return stored chats where the bot was active. Use from private to manage."""
    try:
        chat = update.effective_chat
        user = update.effective_user
    except Exception:
        return 'Context unavailable'

    chats = storage.list_chats()
    if not chats:
        return 'No tengo chats registrados.'
    lines = []
    for cid in chats[:100]:
        try:
            c = context.bot.get_chat(cid)
            title = getattr(c, 'title', None) or getattr(c, 'username', None) or str(cid)
        except Exception:
            title = str(cid)
        lines.append(f'{title} ({cid})')
    lines.append('\nPara aplicar bloqueos desde privado: /applyblocks <chat_id>')
    return 'Chats conocidos:\n' + '\n'.join(lines)


def showblocks_cmd(update: Any, context: Any):
    """Show stored blocklist summary and a small sample."""
    key = storage._skey('blocked_ids')
    blocked = []
    if storage.redis:
        try:
            blocked = [int(x) for x in storage.redis.smembers(key) or []]
        except Exception:
            blocked = []
    else:
        blocked = storage.fallback.get(key) or []

    if not blocked:
        return 'No hay IDs bloqueadas en el almacenamiento.'

    sample = list(blocked)[:20]
    return f'IDs almacenadas: {len(blocked)}. Ejemplo: ' + ', '.join(str(x) for x in sample)
