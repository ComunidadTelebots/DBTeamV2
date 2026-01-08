"""Admin commands to review and apply moderation suggestions from Redis.

Commands (text message commands expected):
- /mod_list [n]       List pending suggestions (default 10)
- /mod_apply <idx> <action>  Apply action for suggestion index (ban/mute/warn/ignore)
- /mod_pop            Pop and return first suggestion
- /mod_help           Show help

Note: This plugin records applied actions to Redis list `moderation:applied`.
Actual enforcement (calling Telegram API) should be handled by another
component/process that reads from `moderation:applied` and performs the
ban/mute operations with appropriate credentials.
"""
from typing import Any
import os
import json
import redis

REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
_r = redis.from_url(REDIS_URL, decode_responses=True)

patterns = [r'^/mod_list', r'^/mod_apply', r'^/mod_pop', r'^/mod_help']


def setup(bot: Any):
    print("Plugin 'moderation_admin' loaded.")


def _format_entry(idx: int, raw: str) -> str:
    try:
        j = json.loads(raw)
        return f"[{idx}] group:{j.get('group_id')} user:{j.get('user_id')} sug:{j.get('suggestion')} ts:{j.get('ts')} info:{j.get('info')}"
    except Exception:
        return f"[{idx}] {raw}"


def run(msg, matches):
    try:
        text = None
        if isinstance(msg, dict):
            text = msg.get('text') or ''
            sender = msg.get('from') or {}
        else:
            text = getattr(msg, 'text', '') or ''
            sender = getattr(msg, 'from', {}) or {}

        parts = (text or '').strip().split()
        cmd = parts[0] if parts else ''

        if cmd == '/mod_help':
            return (
                "Comandos moderation admin:\n"
                "/mod_list [n] - listar sugerencias pendientes\n"
                "/mod_apply <idx> <action> - aplicar acción (ban/mute/warn/ignore)\n"
                "/mod_pop - obtener y eliminar la primera sugerencia\n"
            )

        if cmd == '/mod_list':
            n = 10
            if len(parts) >= 2 and parts[1].isdigit():
                n = int(parts[1])
            entries = _r.lrange('moderation:actions', 0, n - 1)
            if not entries:
                return 'No hay sugerencias pendientes.'
            lines = [_format_entry(i, e) for i, e in enumerate(entries, start=1)]
            return '\n'.join(lines)

        if cmd == '/mod_pop':
            item = _r.lpop('moderation:actions')
            if not item:
                return 'No hay sugerencias para pop.'
            return 'Pop: ' + _format_entry(1, item)

        if cmd == '/mod_apply':
            if len(parts) < 3:
                return 'Uso: /mod_apply <idx> <action>'
            idx = parts[1]
            action = parts[2].lower()
            if action not in ('ban', 'mute', 'warn', 'ignore'):
                return 'Acción inválida. Usa ban/mute/warn/ignore.'
            # Fetch the item by index (1-based). Redis LRANGE uses 0-based.
            if not idx.isdigit():
                return 'Índice inválido.'
            i = int(idx) - 1
            entries = _r.lrange('moderation:actions', i, i)
            if not entries:
                return f'No se encontró sugerencia en índice {idx}.'
            raw = entries[0]
            try:
                j = json.loads(raw)
            except Exception:
                j = {'raw': raw}

            applied = {
                'applied_by': int(sender.get('id') or 0),
                'action': action,
                'original': j,
                'ts': int(__import__('time').time()),
            }
            # Record applied action and remove original entry
            _r.rpush('moderation:applied', json.dumps(applied))
            # Remove only one occurrence of the raw entry
            _r.lrem('moderation:actions', 1, raw)
            return f'Sugerencia {idx} marcada como {action} y registrada para ejecución.'

    except Exception as e:
        print('moderation_admin.run error:', e)
        return 'Error interno en moderation_admin.'

    return None
