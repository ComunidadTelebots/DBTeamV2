"""Port of bot/permissions.lua to Python (compat wrappers).
Provides `permissions`, `compare_permissions` and helpers used by legacy code.
"""
from python_bot.legacy import utils_lua as utils
import os
try:
    import redis
except Exception:
    redis = None

REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')

def _get_redis():
    if not redis:
        raise RuntimeError('redis library not available')
    return redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)

sudos = [
    "lang_install",
    "promote_admin",
    "plugins",
    "banall",
    "leave",
    "setabout",
    "creategroup",
]
admins = [
    "promote_mod",
    "promote_user",
    "gban",
    "add_moderation",
    "adduser",
]
mods = [
    "set_lang",
    "settings",
    "muteBan",
    "moderation",
    "mod_commands",
    "tagall",
    "rem_history",
    "spam",
]

def get_tag(plugin_tag: str) -> int:
    if plugin_tag in sudos:
        return 3
    if plugin_tag in admins:
        return 2
    if plugin_tag in mods:
        return 1
    return 0

def user_num(user_id: int, chat_id: int) -> int:
    # basic checks against redis sets
    r = _get_redis()
    try:
        # sudo users: read env SUDO_USERS as csv
        sudos_env = os.getenv('SUDO_USERS', '')
        if str(user_id) in [s.strip() for s in sudos_env.split(',') if s.strip()]:
            return 3
    except Exception:
        pass
    if r.sismember('admins', str(user_id)):
        return 2
    if r.sismember(f'mods:{chat_id}', str(user_id)):
        return 1
    return 0

def send_warning(user_id: int, chat_id: int, user_need: int):
    if user_need == 3:
        utils.set_text('en', 'require_sudo', '')
    # In original bot this sends a message; leave minimal behaviour

def compare_permissions(chat_id: int, user_id: int, user_id2: int) -> bool:
    return user_num(user_id, chat_id) > user_num(user_id2, chat_id)

def permissions(user_id: int, chat_id: int, plugin_tag: str, option: str = None) -> bool:
    need = get_tag(plugin_tag)
    have = user_num(user_id, chat_id)
    if have >= need:
        return True
    if option != 'silent':
        send_warning(user_id, chat_id, need)
    return False
