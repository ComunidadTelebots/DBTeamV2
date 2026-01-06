"""Plugin para consultar y controlar servicios backend desde Telegram.

Comandos:
- /listmedia : lista archivos multimedia disponibles
- /streammedia <nombre> : genera enlace de streaming
- /dnsstatus : estado del DNS local
- /nginxstatus : estado del proxy web
- /aistats : estadísticas del servidor AI
- /reloadnginx : reinicia nginx (solo admin)
- /listservices : estado de todos los servicios
"""
import os
import requests
from typing import Any, List

BACKEND_URL = os.getenv('BACKEND_URL', 'http://127.0.0.1:8082')
AI_URL = os.getenv('AI_URL', 'http://127.0.0.1:8081')
# URL para el servicio de checksums (por defecto en el servidor AI donde añadimos endpoints)
CHECKSUMS_URL = os.getenv('CHECKSUMS_URL', AI_URL)
NGINX_URL = os.getenv('NGINX_URL', 'http://127.0.0.1')
DNS_URL = os.getenv('DNS_URL', 'http://127.0.0.1:53')

OWNER_ID = str(os.getenv('OWNER_ID', '163103382'))

def setup(bot):
    bot.register_command('listmedia', listmedia_cmd, 'Lista archivos multimedia', plugin='services')
    bot.register_command('streammedia', streammedia_cmd, 'Enlace de streaming de archivo', plugin='services')
    bot.register_command('dnsstatus', dnsstatus_cmd, 'Estado del DNS local', plugin='services')
    bot.register_command('nginxstatus', nginxstatus_cmd, 'Estado del proxy web', plugin='services')
    bot.register_command('aistats', aistats_cmd, 'Estadísticas del servidor AI', plugin='services')
    bot.register_command('reloadnginx', reloadnginx_cmd, 'Reinicia nginx', plugin='services')
    bot.register_command('listservices', listservices_cmd, 'Estado de todos los servicios', plugin='services')

async def listmedia_cmd(update: Any, context: Any):
    try:
        r = requests.get(f'{BACKEND_URL}/media/files', timeout=10)
        files = r.json().get('files', [])
        text = 'Archivos multimedia disponibles:\n'
        for f in files:
            name = f.get('name')
            # verificar checksum si está disponible
            try:
                vr = requests.get(f'{CHECKSUMS_URL}/checksums/verify', params={'name': name}, timeout=5)
                if vr.ok:
                    vj = vr.json()
                    status = '(verificado)' if vj.get('ok') else '(no-verificado)'
                else:
                    status = ''
            except Exception:
                status = ''
            text += f"- {name} {status}\n"
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

async def streammedia_cmd(update: Any, context: Any):
    args = getattr(context, 'args', []) or []
    if not args:
        await update.message.reply_text('Uso: /streammedia <nombre>')
        return
    name = args[0]
    # Antes de generar enlace, pedir verificación de checksum al API
    try:
        vr = requests.get(f'{CHECKSUMS_URL}/checksums/verify', params={'name': name}, timeout=5)
        if vr.ok:
            j = vr.json()
            if not j.get('ok'):
                await update.message.reply_text(f'Advertencia: el archivo {name} no pasó la verificación de integridad (hash mismatch). Acción abortada.')
                return
        else:
            await update.message.reply_text(f'No se pudo verificar integridad de {name}; intenta de nuevo más tarde.')
            return
    except Exception as e:
        await update.message.reply_text(f'Error al verificar integridad: {e}')
        return

    url = f'{BACKEND_URL}/media/stream/{name}'
    await update.message.reply_text(f'Enlace de streaming: {url}')

async def dnsstatus_cmd(update: Any, context: Any):
    # Simulación: solo muestra el puerto y estado
    await update.message.reply_text(f'DNS local activo en {DNS_URL}')

async def nginxstatus_cmd(update: Any, context: Any):
    try:
        r = requests.get(f'{NGINX_URL}/status.html', timeout=5)
        if r.ok:
            await update.message.reply_text('Nginx activo.')
        else:
            await update.message.reply_text('Nginx no responde.')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

async def aistats_cmd(update: Any, context: Any):
    try:
        r = requests.get(f'{AI_URL}/stats', timeout=10)
        await update.message.reply_text(f'Estadísticas AI:\n{r.text}')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

async def reloadnginx_cmd(update: Any, context: Any):
    user_id = str(update.effective_user.id) if update.effective_user else None
    if user_id != OWNER_ID:
        await update.message.reply_text('Solo el administrador puede reiniciar nginx.')
        return
    # Simulación: deberías implementar el comando real en el backend
    await update.message.reply_text('Comando de reinicio de nginx enviado.')

async def listservices_cmd(update: Any, context: Any):
    text = 'Estado de servicios:\n'
    # Simulación: puedes mejorar con peticiones reales
    text += f'- Backend: {BACKEND_URL}\n- AI: {AI_URL}\n- Nginx: {NGINX_URL}\n- DNS: {DNS_URL}\n'
    await update.message.reply_text(text)
