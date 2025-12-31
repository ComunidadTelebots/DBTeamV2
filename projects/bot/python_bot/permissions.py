"""Permissions helpers ported from bot/permissions.lua
Provides simple permission levels and checks.
"""
from typing import List
import os

# Keep the same tag lists as the Lua version for compatibility
SUDOS = [
    "lang_install",
    "promote_admin",
    "plugins",
    "banall",
    "leave",
    "setabout",
    "creategroup",
]

ADMINS = [
    "promote_mod",
    "promote_user",
    "gban",
    "add_moderation",
    "adduser",
]

MODS = [
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
    if plugin_tag in SUDOS:
        return 3
    if plugin_tag in ADMINS:
        return 2
    if plugin_tag in MODS:
        return 1
    return 0

# The project currently keeps sudo users in _config.sudo_users in Lua; for Python
# code, prefer reading env or redis. Here we fallback to env `SUDO_USERS` as CSV.
def _load_sudo_list() -> List[int]:
    val = os.getenv('SUDO_USERS', '')
    if not val:
        return []
    return [int(x) for x in val.split(',') if x.strip()]

def user_num(user_id: int, chat_id: int, is_admin_fn, is_mod_fn, is_sudo_fn) -> int:
    """Determine numeric permission for a user via provided callbacks.
    Callbacks: is_admin_fn(user_id)->bool, is_mod_fn(chat_id,user_id)->bool,
    is_sudo_fn(user_id)->bool
    """
    if is_sudo_fn(user_id):
        return 3
    if is_admin_fn(user_id):
        return 2
    if is_mod_fn(chat_id, user_id):
        return 1
    return 0

def compare_permissions(chat_id: int, user_id: int, user_id2: int, is_admin_fn, is_mod_fn, is_sudo_fn) -> bool:
    return user_num(user_id, chat_id, is_admin_fn, is_mod_fn, is_sudo_fn) > user_num(user_id2, chat_id, is_admin_fn, is_mod_fn, is_sudo_fn)

def permissions(user_id: int, chat_id: int, plugin_tag: str, is_admin_fn, is_mod_fn, is_sudo_fn, option: str = None) -> bool:
    need = get_tag(plugin_tag)
    have = user_num(user_id, chat_id, is_admin_fn, is_mod_fn, is_sudo_fn)
    return have >= need
