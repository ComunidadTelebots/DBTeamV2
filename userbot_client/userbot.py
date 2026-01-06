import os
import threading
from flask import Flask, render_template_string, request, redirect
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import logging
import requests
import json

# Gestión de dueño del bot
OWNER_FILE = os.path.join(os.path.dirname(__file__), 'userbot_owner.txt')

def get_owner_id():
    if os.path.exists(OWNER_FILE):
        with open(OWNER_FILE, 'r') as f:
            return int(f.read().strip())
    return None

def set_owner_id(user_id):
    with open(OWNER_FILE, 'w') as f:
        f.write(str(user_id))

logging.basicConfig(level=logging.INFO)

# Configuración básica
BOT_TOKEN = os.getenv('USER_BOT_TOKEN') or ''
API_URL = os.getenv('CENTRAL_API_URL') or 'http://localhost:8000'

# Información del userbot para registro en la API
USERBOT_NAME = os.getenv('USER_BOT_NAME') or 'UserBot Python'
USERBOT_INFO = os.getenv('USER_BOT_INFO') or 'Userbot local sincronizado con API central.'

app = Flask(__name__)

HTML_FORM = '''
<!DOCTYPE html>
<html><head><title>UserBot Config</title></head><body>
<h2>Configura tu UserBot</h2>
{% if msg %}<div style="color:green;font-weight:bold;">{{msg}}</div>{% endif %}
<form method="post">
    <label>Token de tu bot de Telegram:</label><br>
    <input type="text" name="token" value="{{token}}" size="50"><br><br>
    <label>URL de la API central:</label><br>
    <input type="text" name="api_url" value="{{api_url}}" size="50"><br><br>
    <label>ID de usuario dueño (Telegram):</label><br>
    <input type="text" name="owner_id" value="{{owner_id}}" size="30"><br><br>
    <input type="submit" value="Guardar y arrancar bot">
</form>
</body></html>
'''

@app.route('/', methods=['GET', 'POST'])
def config():
    global BOT_TOKEN, API_URL
    owner_id = get_owner_id()
    msg = ''
    if request.method == 'POST':
        BOT_TOKEN = request.form['token']
        API_URL = request.form['api_url']
        owner_id_form = request.form.get('owner_id', '').strip()
        os.environ['USER_BOT_TOKEN'] = BOT_TOKEN
        os.environ['CENTRAL_API_URL'] = API_URL
        if owner_id_form.isdigit():
            set_owner_id(int(owner_id_form))
            msg = f'Configuración guardada. Owner ID: {owner_id_form}'
        else:
            msg = 'Configuración guardada. (No se estableció Owner ID)'
        # Registrar el bot en el backend principal
        try:
            payload = {
                'token': BOT_TOKEN,
                'name': USERBOT_NAME,
                'info': USERBOT_INFO,
                'owner_id': int(owner_id_form) if owner_id_form.isdigit() else None,
                'avatar': os.getenv('USER_BOT_AVATAR') or '',
                # Puedes añadir más campos personalizados aquí si lo necesitas
            }
            resp = requests.post(f'{API_URL}/bot/import', json=payload, timeout=10)
            if resp.ok:
                msg += '<br>Bot registrado en el backend principal.'
            else:
                msg += f'<br>Error al registrar en backend: {resp.text}'
        except Exception as e:
            msg += f'<br>Error al registrar en backend: {e}'
        threading.Thread(target=start_bot, daemon=True).start()
        return render_template_string(HTML_FORM, token=BOT_TOKEN, api_url=API_URL, owner_id=owner_id_form, msg=msg)
    return render_template_string(HTML_FORM, token=BOT_TOKEN, api_url=API_URL, owner_id=owner_id or '', msg=msg)

def start_bot():
    if not BOT_TOKEN:
        print('No se ha configurado el token del bot.')
        return
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler('start', start_cmd))
    app_telegram.add_handler(CommandHandler('alerta_critica', alerta_critica_cmd))
    app_telegram.add_handler(CommandHandler('resumen_diario', resumen_diario_cmd))
    app_telegram.add_handler(CommandHandler('usuarios_activos', usuarios_activos_cmd))
    app_telegram.add_handler(CommandHandler('estado_servicios', estado_servicios_cmd))
    app_telegram.add_handler(CommandHandler('limpiar_temp', limpiar_temp_cmd))
    app_telegram.add_handler(CommandHandler('backup', backup_cmd))
    app_telegram.add_handler(CommandHandler('restore', restore_cmd))
    app_telegram.add_handler(CommandHandler('promote', promote_cmd))
    app_telegram.add_handler(CommandHandler('ban', ban_cmd))
    app_telegram.add_handler(CommandHandler('mute', mute_cmd))
    app_telegram.add_handler(CommandHandler('registrar_api', registrar_api_cmd))
    app_telegram.add_handler(CommandHandler('mis_chats', mis_chats_cmd))
    app_telegram.add_handler(CommandHandler('enviar_mensaje', enviar_mensaje_cmd))
    app_telegram.add_handler(CommandHandler('sincronizar_bloqueos', sync_bloqueos_cmd))
    app_telegram.add_handler(CommandHandler('help', help_cmd))
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    print('UserBot arrancado. Esperando mensajes...')
    app_telegram.run_polling()

def notify_api(text):
    try:
        requests.post(f'{API_URL}/userbot/event', json={'text': text, 'bot_token': BOT_TOKEN})
    except Exception as e:
        print(f'Error notificando a la API: {e}')

async def start_cmd(update, context):
    owner_id = get_owner_id()
    user_id = update.effective_user.id
    if owner_id is None:
        set_owner_id(user_id)
        await update.message.reply_text('¡Te has registrado como dueño de este UserBot!')
    elif owner_id == user_id:
        await update.message.reply_text('¡UserBot Python activo! (Eres el dueño)')
    else:
        await update.message.reply_text('UserBot activo, pero solo el dueño puede ejecutar comandos administrativos.')
    notify_api('UserBot iniciado')

# Decorador para restringir comandos al dueño
def owner_only(func):
    async def wrapper(update, context):
        owner_id = get_owner_id()
        user_id = update.effective_user.id
        if owner_id is not None and user_id != owner_id:
            await update.message.reply_text('Solo el dueño registrado puede usar este comando.')
            return
        return await func(update, context)
    return wrapper


@owner_only
async def alerta_critica_cmd(update, context):
    await update.message.reply_text('¡Alerta crítica enviada!')
    notify_api('Alerta crítica enviada')

@owner_only
async def resumen_diario_cmd(update, context):
    await update.message.reply_text('Resumen diario solicitado.')
    notify_api('Resumen diario solicitado')

@owner_only
async def usuarios_activos_cmd(update, context):
    await update.message.reply_text('Usuarios activos listados.')
    notify_api('Usuarios activos listados')

@owner_only
async def estado_servicios_cmd(update, context):
    await update.message.reply_text('Estado de servicios consultado.')
    notify_api('Estado de servicios consultado')

@owner_only
async def limpiar_temp_cmd(update, context):
    await update.message.reply_text('Archivos temporales limpiados.')
    notify_api('Archivos temporales limpiados')

@owner_only
async def backup_cmd(update, context):
    await update.message.reply_text('Backup realizado.')
    notify_api('Backup realizado')

@owner_only
async def restore_cmd(update, context):
    await update.message.reply_text('Restauración realizada.')
    notify_api('Restauración realizada')

@owner_only
async def promote_cmd(update, context):
    await update.message.reply_text('Usuario promovido.')
    notify_api('Usuario promovido')

@owner_only
async def ban_cmd(update, context):
    await update.message.reply_text('Usuario baneado.')
    notify_api('Usuario baneado')

@owner_only
async def mute_cmd(update, context):
    await update.message.reply_text('Usuario silenciado.')
    notify_api('Usuario silenciado')

async def help_cmd(update, context):
    help_text = (
        "/alerta_critica - Enviar alerta crítica a canal/grupo.\n"
        "/resumen_diario - Enviar resumen diario/semanal de actividad o logs.\n"
        "/usuarios_activos - Listar usuarios activos y sus permisos.\n"
        "/estado_servicios - Consultar y reportar estado de servicios externos.\n"
        "/limpiar_temp - Limpieza automática de archivos temporales/logs antiguos.\n"
        "/backup - Realizar backup de la base de datos/configuración.\n"
        "/restore - Restaurar base de datos/configuración desde backup.\n"
        "/promote - Promover usuario a admin/mod.\n"
        "/ban - Banear usuario.\n"
        "/mute - Silenciar usuario.\n"
        "/registrar_api - Registrar este bot en la API central.\n"
        "/mis_chats - Listar los grupos/chats gestionados por este bot.\n"
        "/enviar_mensaje - Enviar mensaje a un grupo/chat desde la API.\n"
        "/sincronizar_bloqueos - Sincronizar bloqueos desde la API.\n"
        "/help - Mostrar esta ayuda."
    )
    await update.message.reply_text(help_text)

# ========== FUNCIONES DE SINCRONIZACIÓN API ==========

@owner_only
async def registrar_api_cmd(update, context):
    """Registrar el userbot en la API central."""
    try:
        resp = requests.post(f'{API_URL}/bot/import', json={
            'token': BOT_TOKEN,
            'name': USERBOT_NAME,
            'info': USERBOT_INFO
        })
        if resp.ok:
            await update.message.reply_text('Userbot registrado en la API central.')
        else:
            await update.message.reply_text(f'Error al registrar: {resp.text}')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

@owner_only
async def mis_chats_cmd(update, context):
    """Listar los grupos/chats gestionados por este bot."""
    try:
        resp = requests.get(f'{API_URL}/bot/stats', params={'token': BOT_TOKEN})
        if resp.ok:
            data = resp.json()
            chats = data.get('chats', [])
            if not chats:
                await update.message.reply_text('No se encontraron chats gestionados.')
            else:
                txt = '\n'.join([f"{c.get('title','') or c.get('id','')} ({c.get('id','')})" for c in chats])
                await update.message.reply_text('Chats gestionados:\n' + txt)
        else:
            await update.message.reply_text(f'Error al consultar chats: {resp.text}')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

@owner_only
async def enviar_mensaje_cmd(update, context):
    """Enviar mensaje a un grupo/chat desde la API central."""
    if len(context.args) < 2:
        await update.message.reply_text('Uso: /enviar_mensaje <group_id> <texto>')
        return
    group_id = context.args[0]
    text = ' '.join(context.args[1:])
    try:
        resp = requests.post(f'{API_URL}/bot/send_message', json={
            'token': BOT_TOKEN,
            'group_id': group_id,
            'text': text
        })
        if resp.ok:
            await update.message.reply_text('Mensaje enviado a través de la API.')
        else:
            await update.message.reply_text(f'Error al enviar mensaje: {resp.text}')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

@owner_only
async def sync_bloqueos_cmd(update, context):
    """Sincronizar bloqueos desde la API central."""
    try:
        resp = requests.get(f'{API_URL}/bot/data', params={'token': BOT_TOKEN})
        if resp.ok:
            data = resp.json()
            blocked = data.get('blocked_ids') or data.get('blocked') or []
            if not blocked:
                await update.message.reply_text('No hay bloqueos para sincronizar.')
            else:
                await update.message.reply_text(f'IDs bloqueados sincronizados: {len(blocked)}')
                # Aquí podrías llamar a ban_user para cada ID si lo deseas
        else:
            await update.message.reply_text(f'Error al sincronizar bloqueos: {resp.text}')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

async def echo(update, context):
    msg = update.message.text
    await update.message.reply_text(f'Eco: {msg}')
    notify_api(f'Mensaje recibido: {msg}')

if __name__ == '__main__':
    app.run(port=5000, debug=True)

# ========== API PARA CONTROL REMOTO DESDE BACKEND ==========
from flask import jsonify
import asyncio

@app.route('/api/cmd', methods=['POST'])
def api_cmd():
    """
    Endpoint para que el backend envíe comandos al userbot.
    Espera JSON: {"command": "alerta_critica", "args": [opcional]}
    """
    data = request.get_json(force=True)
    command = data.get('command', '').lower()
    args = data.get('args', [])
    # Mapeo de comandos a funciones
    cmd_map = {
        'alerta_critica': alerta_critica_cmd,
        'resumen_diario': resumen_diario_cmd,
        'usuarios_activos': usuarios_activos_cmd,
        'estado_servicios': estado_servicios_cmd,
        'limpiar_temp': limpiar_temp_cmd,
        'backup': backup_cmd,
        'restore': restore_cmd,
        'promote': promote_cmd,
        'ban': ban_cmd,
        'mute': mute_cmd,
        'help': help_cmd,
    }
    func = cmd_map.get(command)
    if not func:
        return jsonify({'ok': False, 'error': 'Comando no soportado'}), 400
    # Simular un update/context mínimos para ejecución manual
    class Dummy:
        pass
    dummy_update = Dummy()
    dummy_update.effective_chat = Dummy()
    dummy_update.effective_chat.id = 0
    dummy_update.message = Dummy()
    dummy_update.message.reply_text = lambda text: None
    dummy_update.message.text = ''
    dummy_context = Dummy()
    # Ejecutar la función async
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(func(dummy_update, dummy_context))
        else:
            loop.run_until_complete(func(dummy_update, dummy_context))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
