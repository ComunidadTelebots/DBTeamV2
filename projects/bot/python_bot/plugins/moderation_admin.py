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

patterns = [r'^/mod_list', r'^/mod_apply', r'^/mod_pop', r'^/mod_help', r'^/abuse_', r'^/abuse']


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

        # Abuse protection admin commands
        if cmd in ('/abuse_help', '/abuse'):
            return (
                "Comandos abuse admin:\n"
                "/abuse_block <type> <value> [reason] - block an item. type: ip|country|region|city|medium\n"
                "/abuse_unblock <type> <value> - unblock an item\n"
                "/abuse_blocked [type] - list blocked items (type optional)\n"
                "/abuse_info <ip> - show info about an IP (count, geo) if available\n"
            )

        if cmd == '/abuse_block':
            if len(parts) < 3:
                return 'Uso: /abuse_block <type> <value> [reason]'
            typ = parts[1].lower()
            val = parts[2]
            reason = ' '.join(parts[3:]) if len(parts) > 3 else 'admin'
            try:
                if typ == 'ip':
                    _r.sadd('abuse:blacklist:ip', val)
                    _r.set(f'abuse:black:ip:{val}', json.dumps({'ip': val, 'reason': reason, 'ts': int(__import__('time').time())}))
                elif typ == 'country':
                    cc = val.upper()
                    _r.sadd('abuse:blacklist:country', cc)
                    _r.hset('abuse:black:country', cc, json.dumps({'country': cc, 'reason': reason, 'ts': int(__import__('time').time())}))
                elif typ == 'region':
                    rkey = val.upper()
                    _r.sadd('abuse:blacklist:region', rkey)
                    _r.hset('abuse:black:region', rkey, json.dumps({'region': rkey, 'reason': reason, 'ts': int(__import__('time').time())}))
                elif typ == 'city':
                    _r.sadd('abuse:blacklist:city', val)
                    _r.hset('abuse:black:city', val, json.dumps({'city': val, 'reason': reason, 'ts': int(__import__('time').time())}))
                elif typ == 'medium':
                    m = val.lower()
                    _r.sadd('abuse:blacklist:medium', m)
                    _r.hset('abuse:black:medium', m, json.dumps({'medium': m, 'reason': reason, 'ts': int(__import__('time').time())}))
                else:
                    return 'Tipo inválido. Usa ip|country|region|city|medium.'
                return f'Blocked {typ} {val} (reason: {reason})'
            except Exception as e:
                print('abuse_block error', e)
                return 'Error al bloquear.'

        if cmd == '/abuse_unblock':
            if len(parts) < 3:
                return 'Uso: /abuse_unblock <type> <value>'
            typ = parts[1].lower()
            val = parts[2]
            try:
                if typ == 'ip':
                    _r.srem('abuse:blacklist:ip', val)
                    _r.delete(f'abuse:black:ip:{val}')
                elif typ == 'country':
                    cc = val.upper()
                    _r.srem('abuse:blacklist:country', cc)
                    _r.hdel('abuse:black:country', cc)
                elif typ == 'region':
                    rkey = val.upper()
                    _r.srem('abuse:blacklist:region', rkey)
                    _r.hdel('abuse:black:region', rkey)
                elif typ == 'city':
                    _r.srem('abuse:blacklist:city', val)
                    _r.hdel('abuse:black:city', val)
                elif typ == 'medium':
                    m = val.lower()
                    _r.srem('abuse:blacklist:medium', m)
                    _r.hdel('abuse:black:medium', m)
                else:
                    return 'Tipo inválido. Usa ip|country|region|city|medium.'
                return f'Unblocked {typ} {val}.'
            except Exception as e:
                print('abuse_unblock error', e)
                return 'Error al desbloquear.'

        if cmd == '/abuse_blocked':
            # optional type filter
            typ = parts[1].lower() if len(parts) >= 2 else None
            try:
                if not typ:
                    ips = _r.smembers('abuse:blacklist:ip') or set()
                    countries = _r.smembers('abuse:blacklist:country') or set()
                    regions = _r.smembers('abuse:blacklist:region') or set()
                    cities = _r.smembers('abuse:blacklist:city') or set()
                    mediums = _r.smembers('abuse:blacklist:medium') or set()
                    lines = [f'IPs: {", ".join(sorted(list(ips)))}', f'Countries: {", ".join(sorted(list(countries)))}', f'Regions: {", ".join(sorted(list(regions)))}', f'Cities: {", ".join(sorted(list(cities)))}', f'Mediums: {", ".join(sorted(list(mediums)))}']
                    return '\n'.join(lines)
                else:
                    if typ == 'ip':
                        return 'IPs: ' + ', '.join(sorted(list(_r.smembers('abuse:blacklist:ip') or set())))
                    if typ == 'country':
                        return 'Countries: ' + ', '.join(sorted(list(_r.smembers('abuse:blacklist:country') or set())))
                    if typ == 'region':
                        return 'Regions: ' + ', '.join(sorted(list(_r.smembers('abuse:blacklist:region') or set())))
                    if typ == 'city':
                        return 'Cities: ' + ', '.join(sorted(list(_r.smembers('abuse:blacklist:city') or set())))
                    if typ == 'medium':
                        return 'Mediums: ' + ', '.join(sorted(list(_r.smembers('abuse:blacklist:medium') or set())))
                    return 'Tipo inválido. Usa ip|country|region|city|medium.'
            except Exception as e:
                print('abuse_blocked error', e)
                return 'Error al listar bloqueos.'

        if cmd == '/abuse_info':
            if len(parts) < 2:
                return 'Uso: /abuse_info <ip>'
            ip = parts[1]
            try:
                cnt = _r.get(f'abuse:count:ip:{ip}') or '0'
                raw = _r.get(f'abuse:black:ip:{ip}')
                info = raw or '{}'
                return f'IP {ip} count={cnt} info={info}'
            except Exception as e:
                print('abuse_info error', e)
                return 'Error al obtener info.'

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
