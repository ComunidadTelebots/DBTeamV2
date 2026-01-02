"""Plugin para gestionar trackers WebRTC desde Telegram.

Comandos:
- /listtrackers : muestra la lista de trackers activos
- /addtracker <url> : añade un tracker (solo admin)
"""
import os
from typing import Any, List

TRACKERS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'webtorrent_trackers.txt')

DEFAULT_TRACKERS = [
    'wss://tracker.openwebtorrent.com',
    'wss://tracker.btorrent.xyz',
    'wss://tracker.fastcast.nz',
    'wss://tracker.webtorrent.dev',
    'wss://tracker.sloppyta.co:443/announce',
    'wss://tracker.files.fm:7073/announce',
    'ws://tracker.files.fm:7072/announce',
    'wss://tracker.thepiratebay.org/announce',
    'wss://dontorrent.prof/announce'
]

def _load_trackers():
    if not os.path.exists(TRACKERS_FILE):
        return DEFAULT_TRACKERS.copy()
    try:
        with open(TRACKERS_FILE, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception:
        return DEFAULT_TRACKERS.copy()

def _save_trackers(trackers: List[str]):
    try:
        with open(TRACKERS_FILE, 'w', encoding='utf-8') as f:
            for t in trackers:
                f.write(t + '\n')
        return True
    except Exception:
        return False

def setup(bot):
    bot.register_command('listtrackers', listtrackers_cmd, 'Lista los trackers WebRTC activos', plugin='trackers')
    bot.register_command('addtracker', addtracker_cmd, 'Añade un tracker WebRTC', plugin='trackers')

async def listtrackers_cmd(update: Any, context: Any):
    trackers = _load_trackers()
    text = 'Trackers WebRTC activos:\n' + '\n'.join(trackers)
    await update.message.reply_text(text)

async def addtracker_cmd(update: Any, context: Any):
    user_id = update.effective_user.id if update.effective_user else None
    # Solo admin (puedes mejorar con tu sistema de permisos)
    if str(user_id) != str(os.getenv('OWNER_ID', '163103382')):
        await update.message.reply_text('Solo el administrador puede añadir trackers.')
        return
    args = getattr(context, 'args', []) or []
    if not args:
        await update.message.reply_text('Uso: /addtracker <url>')
        return
    url = args[0].strip()
    trackers = _load_trackers()
    if url in trackers:
        await update.message.reply_text('El tracker ya está en la lista.')
        return
    trackers.append(url)
    if _save_trackers(trackers):
        await update.message.reply_text(f'Tracker añadido: {url}')
    else:
        await update.message.reply_text('Error al guardar el tracker.')
