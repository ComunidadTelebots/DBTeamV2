import aiohttp
"""Plugin para modo owner-only: el bot solo responde al OWNER_ID hasta que se desactive desde la web.

Comandos:
- /ownerlock : activa el modo owner-only
- /unlock : desactiva el modo owner-only
"""
import os
from typing import Any


LOCK_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'ownerlock.flag')
GROUP_LOCK_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'group_lock.flag')
OWNER_ID = str(os.getenv('OWNER_ID', '163103382'))

def _get_locked_groups():
    if not os.path.exists(GROUP_LOCK_FILE):
        return set()
    try:
        with open(GROUP_LOCK_FILE, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except Exception:
        return set()

def _set_locked_groups(groups):
    try:
        with open(GROUP_LOCK_FILE, 'w') as f:
            for gid in groups:
                f.write(str(gid)+'\n')
    except Exception:
        pass

def _is_locked():
    return os.path.exists(LOCK_FILE)

def _set_lock(state: bool):
    if state:
        with open(LOCK_FILE, 'w') as f:
            f.write('locked')
    else:
        try:
            os.remove(LOCK_FILE)
        except Exception:
            pass

def setup(bot):
            async def send_tg_notification(msg):
                tg_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'tg_notify_channel.txt')
                token = os.getenv('BOT_TOKEN')
                if not token:
                    return
                if not os.path.exists(tg_path):
                    return
                try:
                    with open(tg_path, 'r', encoding='utf-8') as f:
                        channel = f.read().strip()
                    if not channel:
                        return
                    url = f'https://api.telegram.org/bot{token}/sendMessage'
                    async with aiohttp.ClientSession() as session:
                        await session.post(url, json={ 'chat_id': channel, 'text': msg })
                except Exception:
                    pass

            async def notification_watcher():
                notif_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'notifications.log')
                last_size = 0
                while True:
                    try:
                        if os.path.exists(notif_path):
                            with open(notif_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                            if len(lines) > last_size:
                                for line in lines[last_size:]:
                                    parts = line.strip().split('|', 2)
                                    if len(parts) == 3:
                                        ts, typ, msg = parts
                                        await send_tg_notification(f'[{ts}] {msg}')
                                last_size = len(lines)
                    except Exception:
                        pass
                    await asyncio.sleep(10)
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(notification_watcher())
            except Exception:
                pass
        # Start background task to process leave group queue
        import asyncio
        async def leave_group_watcher():
            queue_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leave_group_queue.txt')
            while True:
                try:
                    if os.path.exists(queue_path):
                        with open(queue_path, 'r') as f:
                            groups = [line.strip() for line in f if line.strip()]
                        if groups:
                            for gid in groups:
                                try:
                                    await bot.leave_group_by_id(gid)
                                except Exception:
                                    pass
                            # Clear file after processing
                            with open(queue_path, 'w') as f:
                                f.write('')
                except Exception:
                    pass
                await asyncio.sleep(5)
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(leave_group_watcher())
        except Exception:
            pass
    bot.register_command('ownerlock', ownerlock_cmd, 'Activa modo owner-only', plugin='ownerlock')
    bot.register_command('unlock', unlock_cmd, 'Desactiva modo owner-only', plugin='ownerlock')
    bot.register_command('grouplock', grouplock_cmd, 'Restringe comandos solo al owner en este grupo', plugin='ownerlock')
    bot.register_command('groupunlock', groupunlock_cmd, 'Permite comandos a todos en este grupo', plugin='ownerlock')
    bot.register_command('leavegroup', leavegroup_cmd, 'Salir de este grupo (solo owner)', plugin='ownerlock')
    bot.register_message_handler('*', owner_filter, plugin='ownerlock', priority=100)
    bot.register_message_handler('*', group_command_filter, plugin='ownerlock', priority=99)

async def ownerlock_cmd(update: Any, context: Any):
    user_id = str(update.effective_user.id) if update.effective_user else None
    if user_id != OWNER_ID:
        await update.message.reply_text('Solo el owner puede activar el modo owner-only.')
        return
    _set_lock(True)
    await update.message.reply_text('Modo owner-only activado. El bot solo responderá al owner.')

async def unlock_cmd(update: Any, context: Any):
    user_id = str(update.effective_user.id) if update.effective_user else None
    if user_id != OWNER_ID:
        await update.message.reply_text('Solo el owner puede desactivar el modo owner-only.')
        return
    _set_lock(False)
    await update.message.reply_text('Modo owner-only desactivado. El bot responderá a todos.')

async def owner_filter(update: Any, context: Any):
    if not _is_locked():
        return None  # no bloqueo
    user_id = str(update.effective_user.id) if update.effective_user else None
    if user_id != OWNER_ID:
        # Ignora mensajes de otros usuarios
        return True  # bloquea
    return None  # permite al owner

async def group_command_filter(update: Any, context: Any):
    # Solo afecta a comandos en grupos bloqueados
    if not update.message or not update.message.chat or not update.message.text:
        return None
    chat = update.message.chat
    if chat.type not in ('group', 'supergroup'):
        return None
    locked_groups = _get_locked_groups()
    if str(chat.id) not in locked_groups:
        return None
    user_id = str(update.effective_user.id) if update.effective_user else None
    if user_id != OWNER_ID:
        # Bloquea comandos de otros usuarios en grupos bloqueados
        if update.message.text.startswith('/'):
            return True
    return None

async def grouplock_cmd(update: Any, context: Any):
    chat = update.message.chat if update.message and update.message.chat else None
    user_id = str(update.effective_user.id) if update.effective_user else None
    if not chat or chat.type not in ('group', 'supergroup'):
        await update.message.reply_text('Este comando solo se puede usar en grupos.')
        return
    if user_id != OWNER_ID:
        await update.message.reply_text('Solo el owner puede bloquear comandos en el grupo.')
        return
    locked_groups = _get_locked_groups()
    locked_groups.add(str(chat.id))
    _set_locked_groups(locked_groups)
    await update.message.reply_text('Comandos bloqueados para todos excepto el owner en este grupo.')

async def groupunlock_cmd(update: Any, context: Any):
    chat = update.message.chat if update.message and update.message.chat else None
    user_id = str(update.effective_user.id) if update.effective_user else None
    if not chat or chat.type not in ('group', 'supergroup'):
        await update.message.reply_text('Este comando solo se puede usar en grupos.')
        return
    if user_id != OWNER_ID:
        await update.message.reply_text('Solo el owner puede desbloquear comandos en el grupo.')
        return
    locked_groups = _get_locked_groups()
    locked_groups.discard(str(chat.id))
    _set_locked_groups(locked_groups)
    await update.message.reply_text('Comandos permitidos para todos en este grupo.')

async def leavegroup_cmd(update: Any, context: Any):
    chat = update.message.chat if update.message and update.message.chat else None
    user_id = str(update.effective_user.id) if update.effective_user else None
    if not chat or chat.type not in ('group', 'supergroup'):
        await update.message.reply_text('Este comando solo se puede usar en grupos.')
        return
    if user_id != OWNER_ID:
        await update.message.reply_text('Solo el owner puede hacer que el bot salga del grupo.')
        return
    try:
        await context.bot.leave_chat(chat.id)
        await update.message.reply_text('Bot saliendo del grupo...')
    except Exception as e:
        await update.message.reply_text(f'Error al salir del grupo: {e}')
