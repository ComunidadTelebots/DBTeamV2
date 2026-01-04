"""Runner for the python_bot using python-telegram-bot (PTB v20+).

This script initializes the `Bot` scaffold, loads plugins, and exposes
registered commands via PTB CommandHandler. It expects `BOT_TOKEN` to be
present in environment variables.
"""
import os
import asyncio
import inspect
import sys
import time
import platform
from pathlib import Path
import traceback

# Ensure a suitable event loop policy on Windows so PTB can create/get the loop
if sys.platform.startswith('win'):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        # If the policy isn't available for some Python builds, ignore
        pass

# Ensure there's an event loop available (addresses some Windows/python versions)
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

try:
    from telegram import Update
    from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, InlineQueryHandler, filters as Filters
except Exception:
    print('python-telegram-bot not installed. Please install requirements.')
    raise

from python_bot.bot import Bot


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _append_botlog(line: str):
    try:
        repo = _repo_root()
        p = repo / 'bot.log'
        with open(p, 'a', encoding='utf-8') as lf:
            lf.write(line + '\n')
    except Exception:
        pass


def _check_token_and_print(token: str):
    # Print basic runtime info
    pid = os.getpid()
    pyv = sys.version.splitlines()[0]
    t = time.asctime()
    min_interval = os.getenv('TELEGRAM_MIN_INTERVAL') or os.getenv('TG_MIN_INTERVAL') or ''
    max_conc = os.getenv('TELEGRAM_MAX_CONCURRENT') or os.getenv('TG_MAX_CONCURRENT') or ''
    header = f"[startup] time={t} pid={pid} python={pyv} platform={platform.platform()} min_interval={min_interval} max_concurrent={max_conc}"
    print(header)
    _append_botlog(header)

    # Check pending outbox/messages via Redis (if available)
    try:
        try:
            import redis as _redis
        except Exception:
            _redis = None
        pending_outbox = None
        pending_web_messages = None
        if _redis is not None:
            try:
                host = os.getenv('REDIS_HOST','127.0.0.1')
                port = int(os.getenv('REDIS_PORT','6379'))
                r = _redis.StrictRedis(host=host, port=port, db=0, decode_responses=True)
                pending_outbox = int(r.llen('web:outbox') or 0)
                pending_web_messages = int(r.llen('web:messages') or 0)
            except Exception:
                pending_outbox = None
                pending_web_messages = None
        info_pending = f"pending_outbox={pending_outbox if pending_outbox is not None else 'n/a'} pending_web_messages={pending_web_messages if pending_web_messages is not None else 'n/a'}"
        print(info_pending)
        _append_botlog('[startup] ' + info_pending)
    except Exception:
        pass

    # Try calling getMe to validate token and detect authorization errors
    try:
        try:
            import requests
        except Exception:
            print('[startup] requests not available, skipping token check')
            _append_botlog('[startup] requests not available, skipping token check')
            return
        url = f'https://api.telegram.org/bot{token}/getMe'
        r = requests.get(url, timeout=5)
        j = r.json() if r.content else {'ok': False, 'description': 'no-response'}
        if not j.get('ok'):
            msg = f"[startup] token check failed: {j.get('error_code')} {j.get('description')}"
            print(msg)
            _append_botlog(msg)
            # specific check for common unauthorized codes
            if j.get('error_code') in (401, 403):
                warn = '[startup] WARNING: Bot token appears invalid or banned/unauthorized. Verify the token and Bot settings.'
                print(warn)
                _append_botlog(warn)
        else:
            res = j.get('result', {})
            info = f"[startup] bot ok: id={res.get('id')} username=@{res.get('username')} name={res.get('first_name')}"
            print(info)
            _append_botlog(info)
    except Exception as e:
        tb = traceback.format_exc()
        print('[startup] token check exception:', e)
        _append_botlog('[startup] token check exception: ' + str(e))
        _append_botlog(tb)
        _append_botlog('[startup] token check exception: ' + str(e))
        _append_botlog(tb)


def make_command_handler(fn):
    """Wrap plugin handler `fn` into an async function acceptable by PTB."""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if inspect.iscoroutinefunction(fn):
                await fn(update, context)
            else:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, fn, update, context)
        except Exception as e:
            # Print the error to console. Inline queries may not have update.message.
            print('Handler error:', e)
    return handler


def build_app(token: str) -> 'telegram.ext.Application':
                                    async def adminweb_cmd(update, context):
                                        user = update.effective_user
                                        chat = update.effective_chat
                                        motivo = ' '.join(context.args) if context.args else 'Sin motivo especificado.'
                                        # Registrar la solicitud en el backend
                                        import requests
                                        try:
                                            requests.post('http://localhost:8000/admin/request_intervention', json={
                                                'user_id': user.id,
                                                'username': user.username,
                                                'chat_id': chat.id,
                                                'chat_title': getattr(chat, 'title', ''),
                                                'motivo': motivo
                                            }, headers={'Authorization': f'Bearer {os.getenv('OWNER_API_TOKEN','')}'})
                                        except Exception:
                                            pass
                                        await update.message.reply_text('Solicitud enviada a los administradores de la web. Un admin intervendrá pronto. Puedes contactar también con @adminweb.')
                                    app.add_handler(CommandHandler('adminweb', adminweb_cmd))
                                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                                TG_PERMISSIONS = [
                                    'can_send_messages',
                                    'can_send_media_messages',
                                    'can_send_polls',
                                    'can_send_other_messages',
                                    'can_add_web_page_previews',
                                    'can_change_info',
                                    'can_invite_users',
                                    'can_pin_messages',
                                    'can_manage_topics',
                                    'can_manage_video_chats',
                                    'can_manage_chat',
                                    'can_delete_messages',
                                    'can_restrict_members',
                                    'can_promote_members',
                                    'can_manage_voice_chats'
                                ]
                                async def edit_perms_cmd(update, context):
                                    owner_id = os.getenv('OWNER_TELEGRAM_ID')
                                    user_id = str(update.effective_user.id)
                                    # Verificar permisos del usuario en el grupo
                                    import requests
                                    resp = requests.get('http://localhost:8000/bot/groups', headers={'Authorization': f'Bearer {os.getenv('OWNER_API_TOKEN','')}'})
                                    data = resp.json()
                                    groups = data.get('groups',[])
                                    allowed_groups = []
                                    for g in groups:
                                        # Consultar permisos del usuario en el grupo
                                        p_resp = requests.get(f'http://localhost:8000/bot/get_permissions/{g.get('id','-')}/{user_id}', headers={'Authorization': f'Bearer {os.getenv('OWNER_API_TOKEN','')}'})
                                        perms = p_resp.json().get('permissions',{})
                                        # Si tiene algún permiso relevante, puede editar
                                        if any(perms.get(p,False) for p in TG_PERMISSIONS):
                                            allowed_groups.append(g)
                                    if not allowed_groups:
                                        await update.message.reply_text('No tienes permisos suficientes para editar permisos en ningún grupo.')
                                        return
                                    keyboard = []
                                    for g in allowed_groups:
                                        keyboard.append([InlineKeyboardButton(g.get('title','-'), callback_data=f"editperms_group_{g.get('id','-')}")])
                                    reply_markup = InlineKeyboardMarkup(keyboard)
                                    await update.message.reply_text('Selecciona un grupo para editar permisos:', reply_markup=reply_markup)
                                    import requests
                                    resp = requests.get('http://localhost:8000/bot/groups', headers={'Authorization': f'Bearer {os.getenv('OWNER_API_TOKEN','')}'})
                                    data = resp.json()
                                    groups = data.get('groups',[])
                                    if not groups:
                                        await update.message.reply_text('No hay grupos registrados.')
                                        return
                                    keyboard = []
                                    for g in groups:
                                        keyboard.append([InlineKeyboardButton(g.get('title','-'), callback_data=f"editperms_group_{g.get('id','-')}")])
                                    reply_markup = InlineKeyboardMarkup(keyboard)
                                    await update.message.reply_text('Selecciona un grupo para editar permisos:', reply_markup=reply_markup)
                                app.add_handler(CommandHandler('edit_perms', edit_perms_cmd))

                                async def edit_perms_inline(update, context):
                                    query = update.callback_query
                                    data = query.data
                                    import requests
                                    if data.startswith('editperms_group_'):
                                        group_id = data.replace('editperms_group_','')
                                        resp = requests.get(f'http://localhost:8000/bot/group_bans/{group_id}', headers={'Authorization': f'Bearer {os.getenv('OWNER_API_TOKEN','')}'})
                                        d = resp.json()
                                        members = d.get('members',[])
                                        keyboard = []
                                        for m in members:
                                            keyboard.append([InlineKeyboardButton(m.get('name','-'), callback_data=f"editperms_user_{group_id}_{m['user_id']}")])
                                        reply_markup = InlineKeyboardMarkup(keyboard)
                                        await query.edit_message_text('Selecciona un usuario para editar permisos:', reply_markup=reply_markup)
                                    elif data.startswith('editperms_user_'):
                                        _, group_id, user_id = data.split('_',3)[1:]
                                        resp = requests.get(f'http://localhost:8000/bot/get_permissions/{group_id}/{user_id}', headers={'Authorization': f'Bearer {os.getenv('OWNER_API_TOKEN','')}'})
                                        perms = resp.json().get('permissions',{})
                                        msg = f'Permisos de {user_id} en grupo {group_id}:\n'
                                        keyboard = []
                                        for p in TG_PERMISSIONS:
                                            val = perms.get(p,False)
                                            txt = ('✅' if val else '❌') + ' ' + p.replace('_',' ')
                                            keyboard.append([InlineKeyboardButton(txt, callback_data=f"toggleperm_{group_id}_{user_id}_{p}_{'0' if val else '1'}")])
                                        reply_markup = InlineKeyboardMarkup(keyboard)
                                        await query.edit_message_text(msg, reply_markup=reply_markup)
                                    elif data.startswith('toggleperm_'):
                                        _, group_id, user_id, perm, value = data.split('_',4)[1:]
                                        requests.post(f'http://localhost:8000/bot/set_permission/{group_id}/{user_id}', json={'permission': perm, 'value': value=='1'}, headers={'Authorization': f'Bearer {os.getenv('OWNER_API_TOKEN','')}'})
                                        # Recargar permisos
                                        resp = requests.get(f'http://localhost:8000/bot/get_permissions/{group_id}/{user_id}', headers={'Authorization': f'Bearer {os.getenv('OWNER_API_TOKEN','')}'})
                                        perms = resp.json().get('permissions',{})
                                        msg = f'Permisos de {user_id} en grupo {group_id}:\n'
                                        keyboard = []
                                        for p in TG_PERMISSIONS:
                                            val = perms.get(p,False)
                                            txt = ('✅' if val else '❌') + ' ' + p.replace('_',' ')
                                            keyboard.append([InlineKeyboardButton(txt, callback_data=f"toggleperm_{group_id}_{user_id}_{p}_{'0' if val else '1'}")])
                                        reply_markup = InlineKeyboardMarkup(keyboard)
                                        await query.edit_message_text(msg, reply_markup=reply_markup)
                                from telegram.ext import CallbackQueryHandler
                                app.add_handler(CallbackQueryHandler(edit_perms_inline, pattern=r'^(editperms_|toggleperm_)'))
                            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                            async def group_admin_cmd(update, context):
                                # Solo owner
                                owner_id = os.getenv('OWNER_TELEGRAM_ID')
                                if str(update.effective_user.id) != str(owner_id):
                                    await update.message.reply_text('Solo el owner puede administrar grupos.')
                                    return
                                # Obtener grupos y bans
                                import requests
                                resp = requests.get('http://localhost:8000/bot/groups', headers={'Authorization': f'Bearer {os.getenv('OWNER_API_TOKEN','')}'})
                                data = resp.json()
                                groups = data.get('groups',[])
                                if not groups:
                                    await update.message.reply_text('No hay grupos registrados.')
                                    return
                                keyboard = []
                                for g in groups:
                                    keyboard.append([InlineKeyboardButton(g.get('title','-'), callback_data=f"groupadmin_{g.get('id','-')}")])
                                reply_markup = InlineKeyboardMarkup(keyboard)
                                await update.message.reply_text('Selecciona un grupo para administrar:', reply_markup=reply_markup)
                            app.add_handler(CommandHandler('group_admin', group_admin_cmd))

                            async def group_admin_inline(update, context):
                                query = update.callback_query
                                group_id = query.data.replace('groupadmin_','')
                                # Obtener bans y miembros
                                import requests
                                resp = requests.get(f'http://localhost:8000/bot/group_bans/{group_id}', headers={'Authorization': f'Bearer {os.getenv('OWNER_API_TOKEN','')}'})
                                data = resp.json()
                                bans = data.get('bans',[])
                                members = data.get('members',[])
                                msg = f'Grupo {group_id}\n\nUsuarios baneados:\n'
                                for b in bans:
                                    msg += f"- {b['user_id']} ({b.get('reason','')})\n"
                                msg += '\nMiembros:\n'
                                for m in members:
                                    msg += f"- {m['user_id']} {m.get('name','')}\n"
                                # Botones para banear/mutear
                                keyboard = []
                                for m in members:
                                    keyboard.append([
                                        InlineKeyboardButton(f"Banear {m.get('name','')}", callback_data=f"ban_{group_id}_{m['user_id']}"),
                                        InlineKeyboardButton(f"Mutear {m.get('name','')}", callback_data=f"mute_{group_id}_{m['user_id']}"),
                                        InlineKeyboardButton(f"Cambiar rol {m.get('name','')}", callback_data=f"role_{group_id}_{m['user_id']}")
                                    ])
                                reply_markup = InlineKeyboardMarkup(keyboard)
                                await query.edit_message_text(msg, reply_markup=reply_markup)

                            async def group_admin_action(update, context):
                                query = update.callback_query
                                data = query.data
                                import requests
                                if data.startswith('ban_'):
                                    _, group_id, user_id = data.split('_',2)
                                    resp = requests.post(f'http://localhost:8000/bot/ban_user/{group_id}/{user_id}', headers={'Authorization': f'Bearer {os.getenv('OWNER_API_TOKEN','')}'})
                                    await query.edit_message_text(f'Usuario {user_id} baneado en grupo {group_id}.')
                                elif data.startswith('mute_'):
                                    _, group_id, user_id = data.split('_',2)
                                    resp = requests.post(f'http://localhost:8000/bot/mute_user/{group_id}/{user_id}', headers={'Authorization': f'Bearer {os.getenv('OWNER_API_TOKEN','')}'})
                                    await query.edit_message_text(f'Usuario {user_id} muteado en grupo {group_id}.')
                                elif data.startswith('role_'):
                                    _, group_id, user_id = data.split('_',2)
                                    # Mostrar opciones de rol
                                    keyboard = [
                                        [InlineKeyboardButton('Admin', callback_data=f"setrole_{group_id}_{user_id}_admin"),
                                         InlineKeyboardButton('Usuario', callback_data=f"setrole_{group_id}_{user_id}_user")]
                                    ]
                                    reply_markup = InlineKeyboardMarkup(keyboard)
                                    await query.edit_message_text(f'Selecciona el nuevo rol para {user_id}:', reply_markup=reply_markup)
                                elif data.startswith('setrole_'):
                                    _, group_id, user_id, role = data.split('_',3)
                                    resp = requests.post(f'http://localhost:8000/bot/set_role/{group_id}/{user_id}', json={'role': role}, headers={'Authorization': f'Bearer {os.getenv('OWNER_API_TOKEN','')}'})
                                    await query.edit_message_text(f'Rol de {user_id} cambiado a {role} en grupo {group_id}.')

                            from telegram.ext import CallbackQueryHandler
                            app.add_handler(CallbackQueryHandler(group_admin_inline, pattern=r'^groupadmin_'))
                            app.add_handler(CallbackQueryHandler(group_admin_action, pattern=r'^(ban_|mute_)'))
                        # Comando para mostrar ajustes actuales
                        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                        import json
                        SETTINGS_PATH = os.path.join(os.path.dirname(__file__), 'data', 'settings.json')
                        def load_settings():
                            try:
                                with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                                    return json.load(f)
                            except Exception:
                                return {}
                        def save_settings(settings):
                            try:
                                with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                                    json.dump(settings, f, indent=2, ensure_ascii=False)
                            except Exception:
                                pass
                        async def settings_cmd(update, context):
                            s = load_settings()
                            ajustes = {
                                'Min intervalo envío': s.get('TELEGRAM_MIN_INTERVAL','0.35'),
                                'Max concurrencia': s.get('TELEGRAM_MAX_CONCURRENT','2'),
                                'Owner Telegram ID': s.get('OWNER_TELEGRAM_ID','-'),
                                'Web URL': s.get('WEBAPP_URL','http://127.0.0.1:8000'),
                                'API URL': s.get('STATS_API_URL','http://127.0.0.1:8081'),
                                'Tor activado': 'Sí' if s.get('USE_TOR','0') == '1' else 'No',
                                'Proxy Tor': s.get('TOR_PROXY','socks5h://127.0.0.1:9050'),
                                'Token protegido': 'Sí',
                            }
                            msg = 'Ajustes actuales:\n'
                            for k,v in ajustes.items():
                                msg += f'- {k}: {v}\n'
                            keyboard = [
                                [InlineKeyboardButton('Editar intervalo', callback_data='edit_interval'), InlineKeyboardButton('Editar concurrencia', callback_data='edit_concurrent')],
                                [InlineKeyboardButton('Editar Owner ID', callback_data='edit_owner')],
                                [InlineKeyboardButton('Editar Web URL', callback_data='edit_web')],
                                [InlineKeyboardButton('Editar API URL', callback_data='edit_api')],
                                [InlineKeyboardButton('Editar Tor', callback_data='edit_tor')],
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            await update.message.reply_text(msg, reply_markup=reply_markup)
                        app.add_handler(CommandHandler('settings', settings_cmd))

                        async def settings_inline(update, context):
                            query = update.callback_query
                            data = query.data
                            if data == 'edit_interval':
                                await query.edit_message_text('Envía el nuevo valor para el intervalo mínimo de envío (segundos):')
                                context.user_data['edit_setting'] = 'TELEGRAM_MIN_INTERVAL'
                            elif data == 'edit_concurrent':
                                await query.edit_message_text('Envía el nuevo valor para la concurrencia máxima:')
                                context.user_data['edit_setting'] = 'TELEGRAM_MAX_CONCURRENT'
                            elif data == 'edit_owner':
                                await query.edit_message_text('Envía el nuevo Owner Telegram ID:')
                                context.user_data['edit_setting'] = 'OWNER_TELEGRAM_ID'
                            elif data == 'edit_web':
                                await query.edit_message_text('Envía la nueva Web URL:')
                                context.user_data['edit_setting'] = 'WEBAPP_URL'
                            elif data == 'edit_api':
                                await query.edit_message_text('Envía la nueva API URL:')
                                context.user_data['edit_setting'] = 'STATS_API_URL'
                            elif data == 'edit_tor':
                                await query.edit_message_text('Envía 1 para activar Tor, 0 para desactivar:')
                                context.user_data['edit_setting'] = 'USE_TOR'
                            else:
                                await query.edit_message_text('Opción no reconocida.')
                        from telegram.ext import CallbackQueryHandler, MessageHandler, filters as Filters
                        app.add_handler(CallbackQueryHandler(settings_inline, pattern=r'^edit_'))

                        async def settings_message(update, context):
                            setting = context.user_data.get('edit_setting')
                            value = update.message.text.strip()
                            if not setting:
                                return
                            s = load_settings()
                            s[setting] = value
                            save_settings(s)
                            await update.message.reply_text(f'Ajuste {setting} actualizado a: {value} (persistente)')
                            context.user_data['edit_setting'] = None
                        app.add_handler(MessageHandler(Filters.TEXT & Filters.ChatType.PRIVATE, settings_message))
                    # Mensaje de bienvenida al /start
                    async def start_cmd(update, context):
                        web_ui = os.getenv('WEBAPP_URL') or 'http://127.0.0.1:8000'
                        host_api = os.getenv('STATS_API_URL') or 'http://127.0.0.1:8081'
                        bienvenida = (
                            '¡Bienvenido a DBTeamV2!\n\n'
                            'Este bot te ayuda a administrar grupos, gestionar bots, ver estadísticas, expulsar usuarios y mucho más.\n\n'
                            'Nuevos comandos disponibles:\n'
                            '/botinfo - Ver información y gráficos de tus bots\n'
                            '/banned_users - Usuarios expulsados y regiones bloqueadas\n'
                            '/resources - Uso de recursos de bots\n'
                            '/bots - Lista de bots\n'
                            '/groups - Grupos y canales\n'
                            '/users - Usuarios registrados\n'
                            '/translations - Estado de traducciones\n'
                            '/services - Estado de servicios\n'
                            '/geo - Información geográfica de bots y usuarios\n\n'
                            'Para registrarte en la web:\n'
                            '1. Usa /weblogin para obtener tu código de acceso.\n'
                            f'2. Abre la web: {web_ui}\n'
                            '3. Ingresa el código para vincular tu cuenta y acceder a todas las funciones.\n\n'
                            '¿Dudas? Usa /help para ver todos los comandos.'
                        )
                        await update.message.reply_text(bienvenida)
                    app.add_handler(CommandHandler('start', start_cmd))
                # Comando: información detallada de bots
                async def botinfo_cmd(update, context):
                    try:
                        import requests
                        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                        resp = requests.get('http://localhost:8000/bot/mybots', headers={'Authorization': f'Bearer {os.getenv("OWNER_API_TOKEN","")}'})
                        data = resp.json()
                        bots = data.get('bots', [])
                        if not bots:
                            if update.message:
                                await update.message.reply_text('No hay bots registrados.')
                            elif update.callback_query:
                                await update.callback_query.edit_message_text('No hay bots registrados.')
                            return
                        def ascii_bar(val, maxval, width=20):
                            n = int((val/maxval)*width) if maxval else 0
                            return '█'*n + '░'*(width-n)
                        max_chats = max((b.get('total_chats',0) or 0) for b in bots) or 1
                        max_members = max((b.get('total_members',0) or 0) for b in bots) or 1
                        max_msgs = max((b.get('total_messages',0) or 0) for b in bots) or 1
                        chart = '\nGráfico de chats:\n'
                        for b in bots:
                            chart += f"{b.get('name','-')[:12]:12} {ascii_bar(b.get('total_chats',0), max_chats)} {b.get('total_chats',0)}\n"
                        chart += '\nGráfico de miembros:\n'
                        for b in bots:
                            chart += f"{b.get('name','-')[:12]:12} {ascii_bar(b.get('total_members',0), max_members)} {b.get('total_members',0)}\n"
                        chart += '\nGráfico de mensajes:\n'
                        for b in bots:
                            chart += f"{b.get('name','-')[:12]:12} {ascii_bar(b.get('total_messages',0), max_msgs)} {b.get('total_messages',0)}\n"
                        # Inline keyboard para ver detalles de cada bot
                        keyboard = [[InlineKeyboardButton(bot.get('name','-'), callback_data=f"botinfo_{bot.get('token','-')}") for bot in bots]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        text = chart + '\nSelecciona un bot para ver detalles.'
                        if update.message:
                            sent = await update.message.reply_text(text, reply_markup=reply_markup)
                            context.user_data['last_botinfo_msg_id'] = sent.message_id
                        elif update.callback_query:
                            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
                    except Exception as e:
                        err = f'Error consultando bots: {e}'
                        if update.message:
                            await update.message.reply_text(err)
                        elif update.callback_query:
                            await update.callback_query.edit_message_text(err)

                async def botinfo_inline(update, context):
                    try:
                        import requests
                        token = update.callback_query.data.replace('botinfo_','')
                        resp = requests.get('http://localhost:8000/bot/mybots', headers={'Authorization': f'Bearer {os.getenv("OWNER_API_TOKEN","")}'})
                        data = resp.json()
                        bots = data.get('bots', [])
                        bot = next((b for b in bots if b.get('token','-') == token), None)
                        if not bot:
                            await update.callback_query.edit_message_text('Bot no encontrado.')
                            return
                        sec = bot.get('security', {})
                        msg = f"Nombre: {bot.get('name','-')}\nEstado: {bot.get('status','-')}\nToken: {bot.get('token','-')[:8]}...*\nInfo: {bot.get('info','-')}\nAvatar: {bot.get('avatar','-')}\nPropietario: {bot.get('owner','-')}\nFecha importación: {sec.get('imported_at','-')}\nIP importación: {sec.get('import_ip','-')}\nRegión: {sec.get('region','-')}\nTor: {'Sí' if bot.get('tor_enabled') else 'No'}\nHash esperado: {bot.get('expected_hash','-')}\nChats: {bot.get('total_chats','-')}\nMiembros: {bot.get('total_members','-')}\nMensajes: {bot.get('total_messages','-')}\nCódigo verificado: {'Sí' if sec.get('code_verified') else 'No'}\nInstrucciones prohibidas: {'Sí' if sec.get('forbidden_found') else 'No'}"
                        await update.callback_query.edit_message_text(msg)
                    except Exception as e:
                        await update.callback_query.edit_message_text(f'Error consultando bot: {e}')

                app.add_handler(CommandHandler('botinfo', botinfo_cmd))
                from telegram.ext import CallbackQueryHandler
                app.add_handler(CallbackQueryHandler(botinfo_inline, pattern=r'^botinfo_'))
                app.add_handler(CommandHandler('botinfo', botinfo_cmd))
            # Comando: usuarios expulsados y regiones bloqueadas
            async def banned_users_cmd(update, context):
                owner_id = os.getenv('OWNER_TELEGRAM_ID')
                if str(update.effective_user.id) != str(owner_id):
                    await update.message.reply_text('Solo el owner puede ver usuarios expulsados.')
                    return
                try:
                    import requests
                    resp = requests.get('http://localhost:8000/admin/banned_users', headers={'Authorization': f'Bearer {os.getenv("OWNER_API_TOKEN","")}'})
                    data = resp.json()
                    msg = 'Usuarios expulsados:\n'
                    for u in data.get('users', []):
                        msg += f"- {u['user']} ({u['region']}): {u['reason']}\n"
                    msg += '\nRegiones más bloqueadas:\n'
                    for region, count in data.get('top_regions', []):
                        msg += f"- {region}: {count}\n"
                    await update.message.reply_text(msg)
                except Exception as e:
                    await update.message.reply_text(f'Error consultando expulsados: {e}')
            app.add_handler(CommandHandler('banned_users', banned_users_cmd))

            # Comando: uso de recursos de bots
            async def resources_cmd(update, context):
                try:
                    import requests
                    resp = requests.get('http://localhost:8000/bot/resources_usage', headers={'Authorization': f'Bearer {os.getenv("OWNER_API_TOKEN","")}'})
                    data = resp.json()
                    msg = 'Uso de recursos de bots:\n'
                    for b in data.get('bots_usage', []):
                        msg += f"- {b['name'] or b['token'][:8]}: {b['total_chats']} chats, {b['total_members']} miembros, {b['total_messages']} mensajes\n"
                    await update.message.reply_text(msg)
                except Exception as e:
                    await update.message.reply_text(f'Error consultando recursos: {e}')
            app.add_handler(CommandHandler('resources', resources_cmd))

            # Comando: lista de bots
            async def bots_cmd(update, context):
                try:
                    import requests
                    resp = requests.get('http://localhost:8000/bot/mybots', headers={'Authorization': f'Bearer {os.getenv("OWNER_API_TOKEN","")}'})
                    data = resp.json()
                    msg = 'Bots registrados:\n'
                    for b in data.get('bots', []):
                        msg += f"- {b['name'] or b['token'][:8]}: {b['status']}\n"
                    await update.message.reply_text(msg)
                except Exception as e:
                    await update.message.reply_text(f'Error consultando bots: {e}')
            app.add_handler(CommandHandler('bots', bots_cmd))

            # Comando: grupos y canales
            async def groups_cmd(update, context):
                try:
                    import requests
                    resp = requests.get('http://localhost:8000/bot/groups', headers={'Authorization': f'Bearer {os.getenv("OWNER_API_TOKEN","")}'})
                    data = resp.json()
                    msg = 'Grupos y canales:\n'
                    for g in data.get('groups', []):
                        msg += f"- {g['title'] or g['id']}: {g['type']}\n"
                    await update.message.reply_text(msg)
                except Exception as e:
                    await update.message.reply_text(f'Error consultando grupos: {e}')
            app.add_handler(CommandHandler('groups', groups_cmd))

            # Comando: usuarios
            async def users_cmd(update, context):
                try:
                    import requests
                    resp = requests.get('http://localhost:8000/admin/users', headers={'Authorization': f'Bearer {os.getenv("OWNER_API_TOKEN","")}'})
                    data = resp.json()
                    msg = 'Usuarios:\n'
                    for u in data.get('users', []):
                        msg += f"- {u['user']}: {u['role']}\n"
                    await update.message.reply_text(msg)
                except Exception as e:
                    await update.message.reply_text(f'Error consultando usuarios: {e}')
            app.add_handler(CommandHandler('users', users_cmd))

            # Comando: estado de traducciones
            async def translations_cmd(update, context):
                try:
                    import requests
                    resp = requests.get('http://localhost:8000/i18n/status.json', headers={'Authorization': f'Bearer {os.getenv("OWNER_API_TOKEN","")}'})
                    data = resp.json()
                    msg = 'Estado de traducciones:\n'
                    for lang in data.get('languages', []):
                        percent = round((lang['translated'] / lang['total']) * 100) if lang['total'] else 0
                        msg += f"- {lang['code']}: {percent}%\n"
                    await update.message.reply_text(msg)
                except Exception as e:
                    await update.message.reply_text(f'Error consultando traducciones: {e}')
            app.add_handler(CommandHandler('translations', translations_cmd))

            # Comando: estado de servicios
            async def services_cmd(update, context):
                try:
                    import requests
                    resp = requests.get('http://localhost:8000/services/status', headers={'Authorization': f'Bearer {os.getenv("OWNER_API_TOKEN","")}'})
                    data = resp.json()
                    msg = 'Estado de servicios:\n'
                    for s in data.get('services', []):
                        msg += f"- {s['name']}: {s['status']}\n"
                    await update.message.reply_text(msg)
                except Exception as e:
                    await update.message.reply_text(f'Error consultando servicios: {e}')
            app.add_handler(CommandHandler('services', services_cmd))

            # Comando: geo bots y usuarios
            async def geo_cmd(update, context):
                try:
                    import requests
                    resp = requests.get('http://localhost:8000/geo/summary', headers={'Authorization': f'Bearer {os.getenv("OWNER_API_TOKEN","")}'})
                    data = resp.json()
                    msg = 'Geo bots:\n'
                    for b in data.get('bots', []):
                        msg += f"- {b['name']}: {b['region']}\n"
                    msg += '\nGeo usuarios:\n'
                    for u in data.get('users', []):
                        msg += f"- {u['user']}: {u['region']}\n"
                    await update.message.reply_text(msg)
                except Exception as e:
                    await update.message.reply_text(f'Error consultando geo: {e}')
            app.add_handler(CommandHandler('geo', geo_cmd))
        # Comando para mostrar usuarios expulsados y regiones más bloqueadas
        async def banned_users_cmd(update, context):
            # Solo owner
            owner_id = os.getenv('OWNER_TELEGRAM_ID')
            if str(update.effective_user.id) != str(owner_id):
                await update.message.reply_text('Solo el owner puede ver usuarios expulsados.')
                return
            try:
                import requests
                resp = requests.get('http://localhost:8000/admin/banned_users', headers={'Authorization': f'Bearer {os.getenv("OWNER_API_TOKEN","")}'})
                data = resp.json()
                msg = 'Usuarios expulsados:\n'
                for u in data.get('users', []):
                    msg += f"- {u['user']} ({u['region']}): {u['reason']}\n"
                msg += '\nRegiones más bloqueadas:\n'
                for region, count in data.get('top_regions', []):
                    msg += f"- {region}: {count}\n"
                await update.message.reply_text(msg)
            except Exception as e:
                await update.message.reply_text(f'Error consultando expulsados: {e}')
        app.add_handler(CommandHandler('banned_users', banned_users_cmd))
    b = Bot()
    b.start()

    app = ApplicationBuilder().token(token).build()
    # --- Simple rate limiter to reduce Telegram flood risk ---
    # Configurable via env vars:
    # TELEGRAM_MIN_INTERVAL: minimum seconds between requests (default 0.35)
    # TELEGRAM_MAX_CONCURRENT: maximum concurrent send operations (default 2)
    import asyncio
    min_interval = float(os.getenv('TELEGRAM_MIN_INTERVAL') or os.getenv('TG_MIN_INTERVAL') or 0.35)
    max_concurrent = int(os.getenv('TELEGRAM_MAX_CONCURRENT') or os.getenv('TG_MAX_CONCURRENT') or 2)

    class _RateLimiter:
        def __init__(self, interval: float, concurrency: int):
            self.interval = interval
            self.sem = asyncio.Semaphore(concurrency)
            self._lock = asyncio.Lock()
            self._last = 0.0

        async def __aenter__(self):
            await self.sem.acquire()
            await self._wait_interval()
            return self

        async def __aexit__(self, exc_type, exc, tb):
            self._last = asyncio.get_event_loop().time()
            self.sem.release()

        async def _wait_interval(self):
            async with self._lock:
                now = asyncio.get_event_loop().time()
                wait = max(0.0, self.interval - (now - self._last))
                if wait > 0:
                    await asyncio.sleep(wait)

    _rl = _RateLimiter(min_interval, max_concurrent)
    # expose bot scaffold to handlers via bot_data
    app.bot_data['pybot'] = b

    # Monkeypatch common send methods on app.bot to apply rate limiting
    try:
        send_methods = ['send_message', 'send_document', 'send_photo', 'send_video', 'edit_message_text', 'send_media_group', 'forward_message', 'send_audio']
        for name in send_methods:
            orig = getattr(app.bot, name, None)
            if orig is None:
                continue
            async def make_wrapper(orig_fn):
                async def wrapper(*a, **kw):
                    async with _rl:
                        return await orig_fn(*a, **kw)
                return wrapper
            # bind wrapper to instance
            setattr(app.bot, name, asyncio.coroutine(lambda *a, **kw: None))
            # Using closure to set proper orig_fn
            async def _bind_and_replace(orig_fn, attr_name):
                async def wrapper(*a, **kw):
                    async with _rl:
                        return await orig_fn(*a, **kw)
                setattr(app.bot, attr_name, wrapper)
            # schedule immediate binding
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_bind_and_replace(orig, name))
    except Exception:
        # best-effort, don't fail app build if monkeypatching fails
        pass

    # register commands discovered by plugins
    for name, meta in b.get_registered_commands().items():
        handler_fn = meta.get('handler')
        if handler_fn is None:
            continue
        app.add_handler(CommandHandler(name, make_command_handler(handler_fn)))

    # register message handlers (plugins can register by filter string)
    for mh in b.get_registered_message_handlers():
        f_str = mh.get('filter', 'document')
        handler_fn = mh.get('handler')
        # map filter strings to PTB filters
        filt = None
        parts = [p.strip() for p in f_str.split('|') if p.strip()]
        for p in parts:
            p_low = p.lower()
            if p_low == 'document':
                f = Filters.Document.ALL
            elif p_low == 'video':
                f = Filters.VIDEO
            elif p_low == 'audio':
                f = Filters.AUDIO
            elif p_low == 'photo':
                f = Filters.PHOTO
            elif p_low == 'text':
                f = Filters.TEXT
            else:
                f = None
            if f is not None:
                filt = f if filt is None else (filt | f)
        if filt is not None and handler_fn is not None:
            app.add_handler(MessageHandler(filt, make_command_handler(handler_fn)))

    # register inline query handlers
    for ih in b.get_registered_inline_handlers():
        handler_fn = ih.get('handler')
        if handler_fn is not None:
            app.add_handler(InlineQueryHandler(make_command_handler(handler_fn)))

    # help command
    async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        b_local = context.bot_data.get('pybot')
        if not b_local:
            await update.message.reply_text('Bot runtime not available')
            return
        # Add helpful web links, brief description and login steps to help output
        web_ui = os.getenv('WEBAPP_URL') or 'http://127.0.0.1:8000'
        host_api = os.getenv('STATS_API_URL') or 'http://127.0.0.1:8081'
        desc_lines = [
            'DBTeamV2 is an administration Telegram bot providing moderation, plugin-based features, and a web UI for multimedia and control.',
            f'Web UI: {web_ui}',
            f'Web API: {host_api}',
            'Web login steps: 1) In Telegram use /weblogin to request a code; 2) Open the Web UI and enter the code to verify; 3) Your session will be created.'
        ]
        lines = desc_lines
        lines.append('Available commands:')
        for cmd, md in b_local.get_registered_commands().items():
            lines.append(f'/{cmd} - {md.get("description","")}')
        # send as multiple messages if too long
        payload = '\n'.join(lines) or 'No commands registered'
        if len(payload) > 3000:
            # split into chunks
            parts = [payload[i:i+2500] for i in range(0, len(payload), 2500)]
            for p in parts:
                await update.message.reply_text(p)
        else:
            await update.message.reply_text(payload)

    app.add_handler(CommandHandler('help', help_cmd))

    return app


def main():
    token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print('BOT_TOKEN not set. Set BOT_TOKEN environment variable to run the Telegram bot.')
        sys.exit(1)

    # Configurar requests y telegram para usar Tor si TOR_PROXY está definido
    tor_proxy = os.getenv('TOR_PROXY') or 'socks5h://127.0.0.1:9050'
    use_tor = os.getenv('USE_TOR', '0') == '1'
    if use_tor:
        import telegram
        import telegram.ext
        import requests
        from telegram.utils.request import Request as TGRequest
        # Configurar requests para usar Tor
        session = requests.Session()
        session.proxies = {
            'http': tor_proxy,
            'https': tor_proxy
        }
        # Configurar telegram para usar Tor
        tg_request = TGRequest(con_pool_size=8, connect_timeout=10, read_timeout=10, session=session)
        app = ApplicationBuilder().token(token).request(tg_request).build()
    else:
        app = build_app(token)

    # Evitar que el token se imprima en logs o errores
    def safe_token(token):
        if not token or len(token) < 10:
            return '***'
        return token[:4] + '...' + token[-4:]

    print(f'Starting Telegram bot (polling) with token: {safe_token(token)}')
    _append_botlog('[startup] Starting Telegram bot (polling)')
    app.run_polling()


if __name__ == '__main__':
    main()
"""Entry point for python_bot skeleton.
"""
from python_bot.bot import Bot


def main():
    bot = Bot()
    bot.start()


if __name__ == '__main__':
    main()
