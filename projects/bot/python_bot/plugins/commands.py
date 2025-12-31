"""Port of `plugins/commands.lua` to Python.

Implements the `commands` command which lists available commands
from enabled plugins using the project's Redis-backed i18n keys.
"""

from typing import Any, Dict, List

patterns = [
    r"^[!/#](commands)$",
    r"^[!/#](commands) (.+)"
]

_bot = None

def setup(bot):
    global _bot
    _bot = bot
    print("Plugin 'commands' loaded.")

def run(msg: Dict[str, Any], matches: List[str]):
    # Lazy imports of compatibility helpers
    from python_bot.legacy import bot_lua as bot_legacy
    from python_bot.legacy import permissions_lua as perm
    from python_bot.legacy import utils_lua as utils
    from python_bot.utils import lang_text

    chat_id = msg.get('to', {}).get('id')
    user_id = msg.get('from', {}).get('id')

    r = utils._get_redis()

    text = '#⃣ ' + lang_text(chat_id, 'commandsT') + ':\n'
    space = '\n'

    # No specific plugin requested: list commands for all enabled plugins
    if matches[0] == 'commands' and (len(matches) < 2 or not matches[1]):
        if perm.permissions(user_id, chat_id, 'mod_commands'):
            cfg = bot_legacy.load_config()
            enabled = cfg.get('enabled_plugins', [])
            lang = r.get(f'langset:{chat_id}') or 'en'
            for plugin in enabled:
                text_key = f'lang:{lang}:{plugin}:0'
                count = r.get(text_key)
                if count:
                    try:
                        n = int(count)
                    except Exception:
                        n = 0
                    for i in range(1, n + 1):
                        text = text + lang_text(chat_id, f'{plugin}:{i}') + '\n'
                    text = text + space
        else:
            text = text + lang_text(chat_id, 'moderation:5') + '\n'
            text = text + lang_text(chat_id, 'version:1') + '\n'
            text = text + lang_text(chat_id, 'rules:1') + '\n'

    # Specific plugin requested: show commands for that plugin only
    elif matches[0] == 'commands' and len(matches) > 1 and matches[1]:
        if perm.permissions(user_id, chat_id, 'mod_commands'):
            cfg = bot_legacy.load_config()
            enabled = cfg.get('enabled_plugins', [])
            lang = r.get(f'langset:{chat_id}') or 'en'
            target = matches[1]
            for plugin in enabled:
                if plugin == target:
                    text_key = f'lang:{lang}:{plugin}:0'
                    count = r.get(text_key)
                    if count:
                        try:
                            n = int(count)
                        except Exception:
                            n = 0
                        for i in range(1, n + 1):
                            text = text + lang_text(chat_id, f'{plugin}:{i}') + '\n'
                    return text
            return 'ℹ️ ' + lang_text(chat_id, 'errorNoPlug')
        else:
            return '🚫 ' + lang_text(chat_id, 'require_mod')

    return '`' + text + '`'
