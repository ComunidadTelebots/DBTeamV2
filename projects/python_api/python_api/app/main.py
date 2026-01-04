@app.post('/admin/unban_user')
def unban_user(payload: dict, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede desbloquear usuarios')
    user = payload.get('user')
    if not user:
        raise HTTPException(status_code=400, detail='Usuario requerido')
    r.srem('banned_users', user)
    r.delete(f'user:{user}:banned_reason')
    return { 'ok': True, 'msg': f'Usuario {user} desbloqueado' }
@app.get('/admin/banned_users')
def get_banned_users(request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede ver usuarios expulsados')
    users = list(r.smembers('banned_users'))
    result = []
    region_stats = {}
    for u in users:
        reason = r.get(f'user:{u}:banned_reason') or 'Sin motivo registrado'
        region = r.get(f'user:{u}:region') or 'unknown'
        result.append({'user': u, 'reason': reason, 'region': region})
        region_stats[region] = region_stats.get(region, 0) + 1
    # Obtener top regiones bloqueadas
    top_regions = sorted(region_stats.items(), key=lambda x: x[1], reverse=True)
    return {'users': result, 'top_regions': top_regions}
# Endpoint para validar el hash del bot localmente desplegado
@app.post('/bot/validate_local_hash')
def validate_local_hash(payload: dict, request: Request):
    token = payload.get('token')
    local_hash = payload.get('local_hash')
    if not token or not local_hash:
        raise HTTPException(status_code=400, detail='Token y hash requeridos')
    # Buscar bot por token
    items = r.lrange('user_bots', 0, -1) or []
    bot = None
    for it in items:
        try:
            b = json.loads(it.decode() if isinstance(it, bytes) else it)
            if b.get('token') == token:
                bot = b
                break
        except Exception:
            continue
    if not bot:
        raise HTTPException(status_code=404, detail='Bot no encontrado')
    # Validar hash contra el último importado (si existe)
    # Se puede guardar el hash en el registro del bot al importar
    expected_hash = bot.get('expected_hash')
    if expected_hash and local_hash.lower() == expected_hash.lower():
        return { 'ok': True, 'msg': 'Hash válido' }
    # Aviso al dueño por Telegram si el hash no coincide
    owner_id = bot.get('owner_id') or bot.get('owner')
    alert_msg = f"ALERTA: El bot '{bot.get('name')}' tiene un hash inválido: {local_hash} (esperado: {expected_hash})"
    send_owner_alert(alert_msg, owner_id)
    return { 'ok': False, 'msg': 'Hash no coincide', 'expected': expected_hash }

# Función para enviar aviso al dueño por Telegram
def send_owner_alert(msg, owner_id):
    # owner_id debe ser el chat_id de Telegram del dueño
    # Configura el token del bot de avisos
    TELEGRAM_ALERT_BOT_TOKEN = os.environ.get('TELEGRAM_ALERT_BOT_TOKEN')
    if not TELEGRAM_ALERT_BOT_TOKEN or not owner_id:
        print('No se puede enviar alerta por Telegram: falta token o owner_id')
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_ALERT_BOT_TOKEN}/sendMessage"
        payload = { 'chat_id': owner_id, 'text': msg }
        requests.post(url, json=payload, timeout=5)
        print('Alerta enviada al dueño por Telegram.')
    except Exception as e:
        print(f'Error enviando alerta por Telegram: {e}')
import hashlib
# Endpoint para verificar la integridad del bot importado
import requests
@app.get('/bot/verify_integrity')
def verify_bot_integrity(token: str = '', request: Request = None):
    if not token:
        raise HTTPException(status_code=400, detail='Token requerido')
    # Verificar token con Telegram API
    try:
        url = f'https://api.telegram.org/bot{token}/getMe'
        resp = requests.get(url, timeout=6)
        data = resp.json() if resp.content else {'ok': False, 'description': 'Sin respuesta'}
        if not data.get('ok'):
            return { 'ok': False, 'msg': 'Token inválido o sin permisos', 'details': data }
        return { 'ok': True, 'msg': 'Bot válido', 'details': data.get('result', {}) }
    except Exception as e:
        return { 'ok': False, 'msg': f'Error de conexión: {e}' }
# Endpoint para importar/registrar bots externos
@app.post('/bot/import')
def import_bot(payload: dict, request: Request):
    sess = get_session_from_request(request)
    if not sess or not sess.get('user'):
        raise HTTPException(status_code=403, detail='No autorizado')
    user = sess['user']
    token = payload.get('token')
    name = payload.get('name')
    info = payload.get('info', '')
    avatar = payload.get('avatar', '/logo.svg')
    bot_file = payload.get('bot_file')  # Debe ser base64 o ruta
    expected_hash = payload.get('expected_hash')  # SHA256 o MD5
    if not token or not name:
        raise HTTPException(status_code=400, detail='Token y nombre requeridos')
    # Verificar hash si se proporciona archivo y hash
    if bot_file and expected_hash:
        try:
            import base64
            file_bytes = base64.b64decode(bot_file)
            sha256 = hashlib.sha256(file_bytes).hexdigest()
            md5 = hashlib.md5(file_bytes).hexdigest()
            if expected_hash not in [sha256, md5]:
                raise HTTPException(status_code=400, detail=f'Hash inválido. SHA256: {sha256}, MD5: {md5}')
            # Verificar el código antes de ejecutar (ejemplo: no debe contener import os, sys, subprocess, open, etc)
            code_str = file_bytes.decode(errors='ignore')
            forbidden = ['import os', 'import sys', 'subprocess', 'open(', 'eval(', 'exec(', 'socket', 'requests', 'popen', 'system(', 'fork(', 'thread', 'multiprocessing']
            for word in forbidden:
                if word in code_str:
                    # Expulsar automáticamente al usuario
                    r.sadd('banned_users', user)
                    r.set(f'user:{user}:banned_reason', f'Intento de vulnerar la web/bot: {word}')
                    raise HTTPException(status_code=403, detail=f'Usuario expulsado por intento de vulnerar la web/bot ({word})')
        except Exception as e:
            raise HTTPException(status_code=400, detail=f'Error verificando hash: {e}')
    # Registrar bot en Redis
    import datetime
    ip = request.client.host if hasattr(request, 'client') and request.client else 'unknown'
    bot_data = {
        'token': token,
        'name': name,
        'info': info,
        'avatar': avatar,
        'owner': user,
        'status': 'Activo',
        'statusColor': 'green',
        'security': {
            'imported_at': datetime.datetime.utcnow().isoformat(),
            'import_ip': ip,
            'code_verified': True,
            'forbidden_found': False
        }
    }
    # Eliminar cualquier campo local antes de guardar
    for k in ['local_path','local_config','local_env','local_ip','local_user','local_secret']:
        bot_data.pop(k, None)
    r.rpush('user_bots', json.dumps(bot_data))
    return { 'ok': True, 'msg': 'Bot importado', 'bot': bot_data }
# Endpoint para banear grupo/canal
@app.post('/group/ban')
def ban_group(payload: dict, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede banear grupos')
    group_id = payload.get('group_id')
    if not group_id:
        raise HTTPException(status_code=400, detail='group_id requerido')
    r.set(f'group:{group_id}:banned', '1')
    return { 'ok': True, 'msg': 'Grupo baneado', 'group_id': group_id }
# Endpoint para consultar avisos de límite excedido en tiempo real
@app.get('/group/rate_limit_alerts')
def get_group_rate_limit_alerts(request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo admins/owner pueden ver avisos')
    items = r.lrange('group:rate_limit_exceeded', -100, -1) or []
    alerts = []
    for it in items:
        try:
            group_id, ts = it.split('|')
            alerts.append({ 'group_id': group_id, 'timestamp': float(ts) })
        except Exception:
            continue
    return { 'alerts': alerts }
# Endpoint para limitar la lectura de mensajes por segundo en un grupo/canal
@app.post('/group/set_read_limit')
def set_group_read_limit(payload: dict, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede limitar lectura')
    group_id = payload.get('group_id')
    read_limit = payload.get('read_limit')
    if not group_id or not isinstance(read_limit, int):
        raise HTTPException(status_code=400, detail='group_id y read_limit requeridos')
    r.set(f'group:{group_id}:read_limit', read_limit)
    return { 'ok': True, 'msg': 'Límite de lectura actualizado', 'group_id': group_id, 'read_limit': read_limit }

# Endpoint para consultar el límite de lectura de mensajes de un grupo/canal
@app.get('/group/get_read_limit')
def get_group_read_limit(group_id: str = '', request: Request = None):
    if not group_id:
        raise HTTPException(status_code=400, detail='group_id requerido')
    raw = r.get(f'group:{group_id}:read_limit')
    read_limit = int(raw) if raw else None
    return { 'group_id': group_id, 'read_limit': read_limit }
# Endpoint para ver uso de recursos de todos los bots y detectar el grupo/canal/proceso que más consume
@app.get('/bot/resources_usage')
def bots_resources_usage(request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner o admin puede ver recursos')
    items = r.lrange('user_bots', 0, -1) or []
    bots_usage = []
    max_usage = {'bot': None, 'group': None, 'type': None, 'value': 0}
    groups_raw = r.get('bot_groups')
    if groups_raw:
        try:
            groups = json.loads(groups_raw.decode() if isinstance(groups_raw, bytes) else groups_raw)
        except Exception:
            groups = []
    else:
        groups = []
    for it in items:
        try:
            bot = json.loads(it.decode() if isinstance(it, bytes) else it)
            token = bot.get('token')
            bot_groups = [g for g in groups if g.get('bot_token') == token]
            total_chats = len(bot_groups)
            total_members = sum(len(r.lrange(f'bot_group:{g.get("id")}:members', 0, 99) or []) for g in bot_groups)
            total_messages = sum(len(r.lrange(f'bot_group:{g.get("id")}:messages', 0, 99) or []) for g in bot_groups)
            # Detectar grupo/canal con más miembros/mensajes
            top_group = None
            top_value = 0
            top_type = ''
            for g in bot_groups:
                members = len(r.lrange(f'bot_group:{g.get("id")}:members', 0, 99) or [])
                messages = len(r.lrange(f'bot_group:{g.get("id")}:messages', 0, 99) or [])
                if members > top_value:
                    top_group = g.get('id')
                    top_value = members
                    top_type = 'miembros'
                if messages > top_value:
                    top_group = g.get('id')
                    top_value = messages
                    top_type = 'mensajes'
            if top_value > max_usage['value']:
                max_usage = {'bot': token, 'group': top_group, 'type': top_type, 'value': top_value}
            bots_usage.append({
                'token': token,
                'name': bot.get('name'),
                'total_chats': total_chats,
                'total_members': total_members,
                'total_messages': total_messages,
                'top_group': top_group,
                'top_type': top_type,
                'top_value': top_value
            })
        except Exception:
            continue
    return { 'bots_usage': bots_usage, 'max_usage': max_usage }
# Endpoint para banear bots de usuarios
@app.post('/bot/ban')
def ban_bot(payload: dict, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede banear bots')
    token = payload.get('token')
    if not token:
        raise HTTPException(status_code=400, detail='Token requerido')
    # Marcar bot como baneado en Redis
    r.set(f'bot:{token}:banned', '1')
    return { 'ok': True, 'msg': 'Bot baneado' }
# Endpoint para que el owner limite recursos de bots de usuarios
@app.post('/bot/set_limits')
def set_bot_limits(payload: dict, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede limitar recursos')
    token = payload.get('token')
    limits = payload.get('limits', {})
    if not token or not isinstance(limits, dict):
        raise HTTPException(status_code=400, detail='Token y límites requeridos')
    # Guardar límites en Redis (incluyendo rate limit)
    # Ejemplo de limits: { 'max_chats': 10, 'max_members': 1000, 'max_messages': 10000, 'rate_limit': 5 }
    r.set(f'bot:{token}:limits', json.dumps(limits))
    return { 'ok': True, 'msg': 'Límites actualizados', 'limits': limits }

# Endpoint para consultar límites de recursos de un bot
@app.get('/bot/get_limits')
def get_bot_limits(token: str = '', request: Request = None):
    if not token:
        raise HTTPException(status_code=400, detail='Token requerido')
    raw = r.get(f'bot:{token}:limits')
    if raw:
        try:
            limits = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        except Exception:
            limits = {}
    else:
        limits = {}
    return { 'limits': limits }
# Endpoint para ver grupos/chats gestionados por un bot específico (token)
@app.get('/bot/stats')
def bot_stats(token: str = '', request: Request = None):
    sess = get_session_from_request(request)
    if not sess or not sess.get('user'):
        raise HTTPException(status_code=403, detail='No autorizado')
    user = sess['user']
    # Buscar el bot del usuario por token
    items = r.lrange('user_bots', 0, -1) or []
    bot = None
    for it in items:
        try:
            b = json.loads(it.decode() if isinstance(it, bytes) else it)
            if b.get('token') == token and b.get('owner') == user:
                bot = b
                break
        except Exception:
            continue
    if not bot:
        raise HTTPException(status_code=404, detail='Bot no encontrado')
    # Buscar grupos/chats gestionados por ese bot
    groups_raw = r.get('bot_groups')
    if groups_raw:
        try:
            groups = json.loads(groups_raw.decode() if isinstance(groups_raw, bytes) else groups_raw)
        except Exception:
            groups = []
    else:
        groups = []
    bot_groups = []
    for gr in groups:
        if gr.get('bot_token') == token:
            gid = gr.get('id')
            members = r.lrange(f'bot_group:{gid}:members', 0, 49)
            gr['members'] = []
            for m in members or []:
                try:
                    gr['members'].append(json.loads(m.decode() if isinstance(m, bytes) else m))
                except Exception:
                    continue
            msgs = r.lrange(f'bot_group:{gid}:messages', 0, 19)
            gr['messages'] = []
            for msg in msgs or []:
                try:
                    gr['messages'].append(json.loads(msg.decode() if isinstance(msg, bytes) else msg))
                except Exception:
                    continue
            bot_groups.append(gr)
    return { 'chats': bot_groups }
# Endpoint para ver estadísticas de los chats/grupos del usuario
@app.get('/user/chats_stats')
def user_chats_stats(request: Request):
    sess = get_session_from_request(request)
    if not sess or not sess.get('user'):
        raise HTTPException(status_code=403, detail='No autorizado')
    user = sess['user']
    # Obtener grupos/chats donde el usuario es miembro
    user_groups = []
    groups_raw = r.get('bot_groups')
    if groups_raw:
        try:
            groups = json.loads(groups_raw.decode() if isinstance(groups_raw, bytes) else groups_raw)
        except Exception:
            groups = []
    else:
        groups = []
    for gr in groups:
        gid = gr.get('id')
        members = r.lrange(f'bot_group:{gid}:members', 0, 99)
        member_ids = [json.loads(m.decode() if isinstance(m, bytes) else m).get('id') for m in members or []]
        if user in member_ids:
            # Estadísticas básicas
            msgs = r.lrange(f'bot_group:{gid}:messages', 0, 99)
            last_msg = None
            if msgs:
                try:
                    last_msg = json.loads(msgs[0].decode() if isinstance(msgs[0], bytes) else msgs[0])
                except Exception:
                    last_msg = None
            user_groups.append({
                'id': gid,
                'title': gr.get('title'),
                'type': gr.get('type'),
                'miembros': len(members or []),
                'mensajes': len(msgs or []),
                'ultima_actividad': last_msg.get('date') if last_msg and last_msg.get('date') else None
            })
    return { 'chats': user_groups }
# Endpoint para confirmar verificación de Telegram
@app.post('/user/confirm_telegram')
def confirm_telegram(token: str = '', request: Request = None):
    if not token:
        raise HTTPException(status_code=400, detail='Token requerido')
    user = r.get(f'user:*:telegram_verify_token', token)
    # Buscar usuario por token
    found_user = None
    for k in r.scan_iter(match='user:*:telegram_verify_token'):
        v = r.get(k)
        if v and v.decode() == token:
            found_user = k.decode().split(':')[1]
            break
    if not found_user:
        raise HTTPException(status_code=404, detail='Token inválido o expirado')
    r.set(f'user:{found_user}:telegram_verified', '1')
    r.delete(f'user:{found_user}:telegram_verify_token')
    return { 'ok': True, 'user': found_user }
# Endpoint para consultar estado de verificación de Telegram
@app.get('/user/telegram_status')
def telegram_status(request: Request):
    sess = get_session_from_request(request)
    if not sess or not sess.get('user'):
        raise HTTPException(status_code=403, detail='No autorizado')
    user = sess['user']
    verified = bool(r.get(f'user:{user}:telegram_verified'))
    return { 'verified': verified }

# Endpoint para solicitar verificación de Telegram
@app.post('/user/verify_telegram')
def verify_telegram(request: Request):
    sess = get_session_from_request(request)
    if not sess or not sess.get('user'):
        raise HTTPException(status_code=403, detail='No autorizado')
    user = sess['user']
    # Simular envío de enlace de verificación por Telegram
    import secrets
    token = secrets.token_urlsafe(32)
    r.set(f'user:{user}:telegram_verify_token', token, ex=1800)
    # Aquí deberías enviar el enlace real por Telegram
    print(f'Verify link for {user}: https://tuweb/verify_telegram?token={token}')
    return { 'ok': True, 'msg': 'Solicitud enviada' }
# Endpoint para solicitar recuperación de contraseña
@app.post('/auth/request_reset')
def request_password_reset(payload: dict):
    user = (payload.get('user') or '').strip()
    if not user:
        raise HTTPException(status_code=400, detail='Usuario requerido')
    # Buscar usuario en Redis
    rec = r.get(f'web:user:{user}')
    if not rec:
        raise HTTPException(status_code=404, detail='Usuario no encontrado')
    import secrets, time
    token = secrets.token_urlsafe(32)
    r.set(f'web:pwreset:{token}', user, ex=3600)
    # Enviar enlace por email o Telegram (simulado)
    # Aquí deberías implementar el envío real
    print(f'Reset link for {user}: https://tuweb/reset_password?token={token}')
    # Opcional: guardar log de solicitud
    r.rpush('web:pwreset_requests', f'{user}|{int(time.time())}')
    return { 'ok': True, 'msg': 'Solicitud procesada' }
# Endpoint para listar bots y ajustes del usuario actual
@app.get('/bot/mybots')
def get_my_bots(request: Request):
    sess = get_session_from_request(request)
    if not sess or not sess.get('user'):
        raise HTTPException(status_code=403, detail='No autorizado')
    user = sess['user']
    items = r.lrange('user_bots', 0, -1) or []
    bots = []
    for it in items:
        try:
            b = json.loads(it.decode() if isinstance(it, bytes) else it)
            if b.get('owner') == user:
                # Detectar si el bot tiene Tor activo (puedes guardar este flag al iniciar el bot)
                tor_flag = r.get(f"bot:{b.get('token')}:tor_enabled")
                b['tor_enabled'] = bool(tor_flag == '1')
                # Eliminar información local sensible
                b.pop('local_path', None)
                b.pop('local_config', None)
                b.pop('local_env', None)
                b.pop('local_ip', None)
                b.pop('local_user', None)
                b.pop('local_secret', None)
                bots.append(b)
        except Exception:
            continue
    return { 'bots': bots }
# Endpoint para listar bots de usuarios y sus ajustes
@app.get('/bot/userbots')
def get_user_bots(request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede ver bots de usuarios')
    items = r.lrange('user_bots', 0, -1) or []
    out = []
    for it in items:
        try:
            out.append(json.loads(it.decode() if isinstance(it, bytes) else it))
        except Exception:
            continue
    return { 'bots': out }
# Endpoint para consultar historial de acciones de ban
@app.get('/bot/group/ban_history')
def get_ban_history(request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede ver historial')
    items = r.lrange('bot:ban_history', 0, -1) or []
    out = []
    for it in items:
        try:
            out.append(json.loads(it.decode() if isinstance(it, bytes) else it))
        except Exception:
            continue
    return { 'history': out }

# Endpoint para consultar notificaciones de ban para admin
@app.get('/bot/group/ban_notifications')
def get_ban_notifications(request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=403, detail='Solo admins pueden ver notificaciones')
    # Filtrar notificaciones por el admin actual
    auth = request.headers.get('authorization', '')
    items = r.lrange('bot:ban_notifications', 0, -1) or []
    out = []
    for it in items:
        try:
            notif = json.loads(it.decode() if isinstance(it, bytes) else it)
            if notif.get('to') == auth:
                out.append(notif)
        except Exception:
            continue
    return { 'notifications': out }
# Endpoint para listar sugerencias de ban
@app.get('/bot/group/ban_suggestions')
def list_ban_suggestions(request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede ver sugerencias')
    items = r.lrange('bot:ban_suggestions', 0, -1) or []
    out = []
    for it in items:
        try:
            out.append(json.loads(it.decode() if isinstance(it, bytes) else it))
        except Exception:
            continue
    return { 'suggestions': out }

# Endpoint para eliminar sugerencia de ban (por índice)
@app.post('/bot/group/ban_suggestions/{idx}/delete')
def delete_ban_suggestion(idx: int, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede eliminar sugerencias')
    items = r.lrange('bot:ban_suggestions', 0, -1) or []
    if idx < 0 or idx >= len(items):
        raise HTTPException(status_code=404, detail='Índice fuera de rango')
    sug = None
    try:
        sug = json.loads(items[idx].decode() if isinstance(items[idx], bytes) else items[idx])
    except Exception:
        pass
    r.lset('bot:ban_suggestions', idx, '__deleted__')
    r.lrem('bot:ban_suggestions', 1, '__deleted__')
    # Registrar historial de acción
    action = request.query_params.get('action') or 'rechazado'
    r.rpush('bot:ban_history', json.dumps({ 'ids': sug.get('ids') if sug else [], 'from': sug.get('from') if sug else '', 'action': action, 'ts': int(time.time()) }))
    # Notificar al admin (simulado: guardar notificación en Redis)
    if sug and sug.get('from'):
        r.rpush('bot:ban_notifications', json.dumps({ 'to': sug['from'], 'action': action, 'ids': sug.get('ids', []), 'ts': int(time.time()) }))
    return { 'ok': True }
# Endpoint para sugerir lista de ban al owner
@app.post('/bot/group/suggestban')
def suggest_ban_list(payload: dict, request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=403, detail='Solo admins pueden sugerir bans')
    ids = payload.get('ids')
    if not ids or not isinstance(ids, list):
        raise HTTPException(status_code=400, detail='Lista de IDs requerida')
    # Guardar sugerencia en Redis para revisión del owner
    r.rpush('bot:ban_suggestions', json.dumps({ 'ids': ids, 'from': request.headers.get('authorization', '') }))
    return { 'ok': True, 'suggested': len(ids) }
# Endpoint para importar lista de ban en los bots
@app.post('/bot/group/importban')
def import_ban_list(payload: dict, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede importar bans')
    ids = payload.get('ids')
    if not ids or not isinstance(ids, list):
        raise HTTPException(status_code=400, detail='Lista de IDs requerida')
    # Aplica el ban en Redis y opcionalmente en Telegram
    api_type = payload.get('api') or ''
    global_ban = payload.get('global') or False
    banned = 0
    for uid in ids:
        if global_ban:
            r.sadd('bot:banlist_global', uid)
        else:
            r.sadd('bot:banlist', uid)
        if api_type == 'cas.ban':
            # Llamar a la API de CAS para banear
            try:
                import requests
                resp = requests.post('https://api.cas.chat/ban', json={ 'user_id': uid }, timeout=6)
                if resp.ok:
                    banned += 1
            except Exception as e:
                print(f'Error CAS ban {uid}:', e)
        else:
            banned += 1
    return { 'ok': True, 'banned': banned }
# --- BLOG ENDPOINTS ---
@app.get('/blog/posts')
def get_blog_posts():
    items = r.lrange('web:blog:posts', 0, 49) or []
    out = []
    for it in items:
        try:
            out.append(json.loads(it.decode() if isinstance(it, bytes) else it))
        except Exception:
            continue
    return { 'posts': out }

@app.post('/blog/publish')
def publish_blog_post(payload: dict, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede publicar')
    title = (payload.get('title') or '').strip()
    content = (payload.get('content') or '').strip()
    if not title or not content:
        raise HTTPException(status_code=400, detail='Título y contenido requeridos')
    post = {
        'title': title,
        'content': content,
        'date': payload.get('date') or time.strftime('%Y-%m-%d'),
        'author': 'owner',
        'id': secrets.token_hex(8)
    }
    r.lpush('web:blog:posts', json.dumps(post))
    # Reenviar al chat de Telegram si es publicación nueva o si se solicita (resend)
    resend = payload.get('resend') or False
    if resend or not payload.get('id'):
        try:
            tg_chat_id = r.get('blog:telegram_chat_id')
            tg_token = r.get('blog:telegram_token')
            if tg_chat_id and tg_token:
                import requests
                msg = f"📝 Nueva publicación en el blog:\n<b>{post['title']}</b>\n{post['content']}\n\nVer más en la web."
                url = f"https://api.telegram.org/bot{tg_token.decode() if isinstance(tg_token, bytes) else tg_token}/sendMessage"
                requests.post(url, data={
                    'chat_id': tg_chat_id.decode() if isinstance(tg_chat_id, bytes) else tg_chat_id,
                    'text': msg,
                    'parse_mode': 'HTML'
                }, timeout=6)
        except Exception as e:
            print('Error enviando publicación al chat Telegram:', e)
    return { 'ok': True, 'post': post }

@app.post('/blog/edit')
def edit_blog_post(payload: dict, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede editar')
    post_id = payload.get('id')
    title = (payload.get('title') or '').strip()
    content = (payload.get('content') or '').strip()
    if not post_id or not title or not content:
        raise HTTPException(status_code=400, detail='ID, título y contenido requeridos')
    items = r.lrange('web:blog:posts', 0, 49) or []
    new_posts = []
    edited = None
    for it in items:
        try:
            post = json.loads(it.decode() if isinstance(it, bytes) else it)
            if post.get('id') == post_id:
                post['title'] = title
                post['content'] = content
                edited = post
            new_posts.append(post)
        except Exception:
            continue
    if not edited:
        raise HTTPException(status_code=404, detail='Post no encontrado')
    # Sobrescribe la lista
    r.delete('web:blog:posts')
    for post in reversed(new_posts):
        r.lpush('web:blog:posts', json.dumps(post))
    return { 'ok': True, 'post': edited }
def is_owner_request(request: Request) -> bool:
    if not check_auth(request):
        return False
    sess = get_session_from_request(request)
    return bool(sess and sess.get('role') == 'owner')

# Endpoint para listar grupos/chats del bot
@app.get('/bot/groups')
def get_bot_groups(request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede acceder')
    groups = r.get('bot_groups')
    if groups:
        try:
            groups = json.loads(groups.decode() if isinstance(groups, bytes) else groups)
        except Exception:
            groups = []
    else:
        groups = []
    # Para cada grupo/chat, añadir miembros y mensajes recientes si existen en Redis
    for gr in groups:
        gid = gr.get('id')
        # Miembros
        members = r.lrange(f'bot_group:{gid}:members', 0, 49)
        gr['members'] = []
        for m in members or []:
            try:
                gr['members'].append(json.loads(m.decode() if isinstance(m, bytes) else m))
            except Exception:
                continue
        # Mensajes recientes
        msgs = r.lrange(f'bot_group:{gid}:messages', 0, 19)
        gr['messages'] = []
        for msg in msgs or []:
            try:
                gr['messages'].append(json.loads(msg.decode() if isinstance(msg, bytes) else msg))
            except Exception:
                continue
    return { 'groups': groups }

# Endpoint para salir de grupo/chat
@app.post('/bot/groups/leave')
def leave_bot_group(payload: dict, request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede acceder')
    group_id = payload.get('id') if payload else None
    if not group_id:
        raise HTTPException(status_code=400, detail='id requerido')
    # Simulación: marcar grupo como abandonado
    r.sadd('bot_left_groups', group_id)
    return { 'ok': True }

# Endpoint para ver mensajes recibidos por el bot
@app.get('/bot/messages')
def get_bot_messages(request: Request):
    if not is_owner_request(request):
        raise HTTPException(status_code=403, detail='Solo el owner puede acceder')
    msgs = r.lrange('bot_received_messages', 0, 49)
    messages = []
    for m in msgs or []:
        try:
            messages.append(json.loads(m.decode() if isinstance(m, bytes) else m))
        except Exception:
            continue
    return { 'messages': messages }
## ...existing code...

# (Mover esto después de app = FastAPI())

app = FastAPI()
## ...existing code...

# Endpoint para estado de traducciones
@app.get('/i18n/status.json')
def i18n_status():
    # Ajusta los paths según tu estructura
    base_path = 'web/i18n/en.json'
    import glob
    langs = []
    try:
        with open(base_path, 'r', encoding='utf-8') as f:
            base = json.load(f)
    except Exception:
        return {"languages": []}
    total = len(base)
    for fpath in glob.glob('web/i18n/*.json'):
        code = fpath.split('/')[-1].replace('.json','')
        if code == 'en':
            continue
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            translated = sum(1 for k in base if k in data and data[k] and data[k].strip())
            langs.append({"code": code, "translated": translated, "total": total})
        except Exception:
            continue
    return {"languages": langs}
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import shlex
import platform
from typing import Optional, Any
from fastapi.responses import JSONResponse
import os
import sys
import subprocess
# --- Dependencias requeridas ---
REQUIRED_PACKAGES = [
    'uvicorn',
    'fastapi',
    'redis',
    'cryptography',
    'requests',
    'python-dotenv',
    'python-telegram-bot',
    'transformers',
    'torch',
    'PySocks',
    'stem',
]
def ensure_dependencies():
    import importlib
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg.split('[')[0])
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Instalando dependencias faltantes: {missing}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
        print("Dependencias instaladas. Reinicia el servidor.")
        sys.exit(0)
ensure_dependencies()
from pathlib import Path
import redis
import json
import hashlib
import hmac
import secrets
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import requests
import socks
import socket
from stem import Signal
from stem.control import Controller
import threading
def libretranslate_translate(text, target_lang, source_lang='en', api_url='https://libretranslate.com/translate'):
    def request_with_tor():
        # Start Tor if not running
        try:
            with Controller.from_port(port=9051) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)
        except Exception:
            pass  # Tor may already be running or not installed
        session = requests.Session()
        session.proxies = {
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        }
        try:
            resp = session.post(api_url, json={
                'q': text,
                'source': source_lang,
                'target': target_lang,
                'format': 'text'
            }, timeout=20, verify=True)
            if resp.ok:
                return resp.json().get('translatedText', text)
            return text
        except Exception:
            return text

    def request_normal():
        try:
            resp = requests.post(api_url, json={
                'q': text,
                'source': source_lang,
                'target': target_lang,
                'format': 'text'
            }, timeout=10, verify=True)
            if resp.ok:
                return resp.json().get('translatedText', text)
            return text
        except Exception:
            return text

    # Detect if banned (simulate with _is_banned on IP)
    # For demo, use local IP
    ip = None
    try:
        ip = requests.get('https://api.ipify.org').text
    except Exception:
        ip = None
    if ip and _is_banned(ip):
        return request_with_tor()
    else:
        return request_normal()

def auto_translate_all(scope='bot'):
    # Detect new strings and translate them using LibreTranslate
    # Only for demonstration: assumes en.json as base, others as targets
    base_path = f'projects/bot/python_bot/lang/en.py' if scope == 'bot' else f'web/i18n/en.json'
    output_dir = f'projects/bot/python_bot/lang/generated_libretranslate' if scope == 'bot' else f'web/i18n'
    # For bot: parse LANG dict from en.py
    lang_dict = {}
    if scope == 'bot':
        try:
            with open(base_path, 'r', encoding='utf-8') as f:
                code = f.read()
                ns = {}
                exec(code, ns)
                lang_dict = ns.get('LANG', {})
        except Exception:
            return {'error': 'No se pudo leer el archivo base.'}
    else:
        try:
            with open(base_path, 'r', encoding='utf-8') as f:
                lang_dict = json.load(f)
        except Exception:
            return {'error': 'No se pudo leer el archivo base.'}
    # Idiomas destino
    LANGUAGES = ['es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja']
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    for lang in LANGUAGES:
        translated = {}
        for k, v in lang_dict.items():
            translated[k] = libretranslate_translate(v, lang)
        # Guardar resultado
        if scope == 'bot':
            out_path = os.path.join(output_dir, f'{lang}.py')
            with open(out_path, 'w', encoding='utf-8') as out:
                out.write(f"""# Auto-generated translation\nLANG = {json.dumps(translated, ensure_ascii=False, indent=2)}\n""")
        else:
            out_path = os.path.join(output_dir, f'{lang}.json')
            with open(out_path, 'w', encoding='utf-8') as out:
                json.dump(translated, out, ensure_ascii=False, indent=2)
        results[lang] = out_path
    return {'status': 'ok', 'results': results}
# Endpoint para traducción automática forzada
@app.post('/translations/auto')
def force_auto_translate(request: Request, scope: str = 'bot', background_tasks: BackgroundTasks = None):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    def run_task():
        auto_translate_all(scope)
    if background_tasks:
        background_tasks.add_task(run_task)
        return {'status': 'started'}
    else:
        result = auto_translate_all(scope)
        return result
import signal
import time
import uuid
import hmac as _hmaclib
import re
import socket
import threading
import ipaddress
import math
# Load configuration from a local `config.py` if present; otherwise fall back to env vars
try:
    from .config import BOT_TOKEN, WEB_API_KEY, WEB_API_SECRET, WEB_API_ORIGIN, REDIS_URL
except Exception:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    WEB_API_KEY = os.getenv('WEB_API_KEY')
    WEB_API_SECRET = os.getenv('WEB_API_SECRET')
    WEB_API_ORIGIN = os.getenv('WEB_API_ORIGIN')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')

app = FastAPI()
r = redis.from_url(REDIS_URL)

# Configure CORS middleware early. If WEB_API_ORIGIN is set, allow only that origin;
# otherwise allow common localhost origins used during development.
if WEB_API_ORIGIN:
    _origins = [WEB_API_ORIGIN]
else:
    _origins = [
        'http://127.0.0.1:8080',
        'http://localhost:8080',
        'http://127.0.0.1:8000',
        'http://localhost:8000',
        'https://cas.chat',
    ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# server start time for uptime reporting
START_TIME = int(time.time())

# Optional: auto-register a bot token on server startup if provided via env var
AUTO_REGISTER_BOT_TOKEN = os.getenv('AUTO_REGISTER_BOT_TOKEN')

def _register_bot_token_on_startup(token: str):
    if not token:
        return None
    try:
        resp = requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=10)
    except Exception as e:
        print('auto-register: telegram error', e)
        return None
    if not resp.ok:
        print('auto-register: telegram returned not ok', resp.text)
        return None
    try:
        data = resp.json()
    except Exception:
        data = { 'ok': False }
    result = data.get('result') if isinstance(data, dict) else None
    bot_id = None
    bot_name = None
    if result:
        bot_id = result.get('id')
        bot_name = result.get('username') or result.get('first_name')
    device_id = f'bot:{bot_id}' if bot_id else f'bot:{secrets.token_hex(6)}'
    device_name = bot_name or device_id
    enc = encrypt_value(token)
    obj = { 'id': device_id, 'name': device_name, 'token': enc }
    try:
        items = r.lrange('web:devices', 0, -1) or []
        exists = False
        for it in items:
            try:
                cur = json.loads(it)
                if cur.get('id') == obj['id']:
                    exists = True
                    break
            except Exception:
                continue
        if not exists:
            r.rpush('web:devices', json.dumps(obj))
            print('auto-register: device registered', device_id)
        else:
            print('auto-register: device already present', device_id)
    except Exception as e:
        print('auto-register: failed to persist device', e)
    return obj


@app.on_event('startup')
def _auto_register_startup_event():
    if AUTO_REGISTER_BOT_TOKEN:
        try:
            _register_bot_token_on_startup(AUTO_REGISTER_BOT_TOKEN)
        except Exception as e:
            print('auto-register startup exception:', e)

# Note: static files will be mounted at the end of this module so API routes
# (including /tdlib) are registered first and not shadowed by StaticFiles.

# Include tdlib router (scaffold). If import fails, register a JSON fallback
TDLIB_AVAILABLE = True
try:
    # Try package-relative import first (works when running as a package)
    try:
        from .tdlib_router import router as tdlib_router
    except Exception:
        # Fallback to top-level import (works when running from the module dir)
        from tdlib_router import router as tdlib_router
    app.include_router(tdlib_router, prefix='/tdlib')
    print('tdlib router included')
except Exception as _e:
    TDLIB_AVAILABLE = False
    print('tdlib router import failed:', repr(_e))
    # Provide minimal JSON endpoints to surface an explicit error instead of HTML
    from fastapi import APIRouter
    fallback = APIRouter()
    @fallback.post('/connect')
    def tdlib_connect_fallback():
        raise HTTPException(status_code=501, detail='tdlib router not available on server')

    @fallback.post('/disconnect')
    def tdlib_disconnect_fallback():
        raise HTTPException(status_code=501, detail='tdlib router not available on server')

    @fallback.post('/send')
    def tdlib_send_fallback():
        raise HTTPException(status_code=501, detail='tdlib router not available on server')

    @fallback.get('/chats')
    def tdlib_chats_fallback():
        raise HTTPException(status_code=501, detail='tdlib router not available on server')

    @fallback.get('/messages')
    def tdlib_messages_fallback():
        raise HTTPException(status_code=501, detail='tdlib router not available on server')

    app.include_router(fallback, prefix='/tdlib')

# Process control: define named processes and commands to start them
REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = REPO_ROOT / 'run'
RUN_DIR.mkdir(parents=True, exist_ok=True)

PROCESS_DEFS = {
    'python_bot': {
        'cmd': ['python', str(REPO_ROOT / 'python_bot' / 'bot.py')],
        'cwd': str(REPO_ROOT)
    },
    'lua_bot': {
        'cmd': ['lua', str(REPO_ROOT / 'bot' / 'bot.lua')],
        'cwd': str(REPO_ROOT)
    }
}

def pidfile_for(name: str) -> Path:
    return RUN_DIR / f"{name}.pid"

def logfile_for(name: str) -> Path:
    return RUN_DIR / f"{name}.log"

def is_pid_running(pid: int) -> bool:
    try:
        if platform.system() == 'Windows':
            # os.kill with 0 works on Windows in Python 3.8+
            os.kill(pid, 0)
        else:
            os.kill(pid, 0)
        return True
    except Exception:
        return False

def read_pid(name: str):
    p = pidfile_for(name)
    if not p.exists():
        return None
    try:
        return int(p.read_text(encoding='utf-8').strip())
    except Exception:
        return None

def start_process(name: str):
    if name not in PROCESS_DEFS:
        raise ValueError('unknown process')
    prog = PROCESS_DEFS[name]
    logp = logfile_for(name)
    pidp = pidfile_for(name)
    # open log file
    lf = open(str(logp), 'ab')
    # spawn detached process
    if platform.system() == 'Windows':
        # CREATE_NEW_PROCESS_GROUP to detach
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        p = subprocess.Popen(prog['cmd'], cwd=prog.get('cwd'), stdout=lf, stderr=subprocess.STDOUT, creationflags=creationflags)
    else:
        p = subprocess.Popen(prog['cmd'], cwd=prog.get('cwd'), stdout=lf, stderr=subprocess.STDOUT, close_fds=True)
    # write pid
    try:
        pidp.write_text(str(p.pid), encoding='utf-8')
    except Exception:
        pass
    return p.pid

def process_status(name: str):
    pid = read_pid(name)
    running = False
    if pid:
        running = is_pid_running(pid)
    return { 'name': name, 'pid': pid, 'running': running, 'log': str(logfile_for(name)) }



def derive_key(secret: str) -> bytes:
    if not secret:
        return None
    salt = b'dbteam-salt'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return key

FERNET_KEY = derive_key(WEB_API_SECRET) if WEB_API_SECRET else None
FERNET = Fernet(FERNET_KEY) if FERNET_KEY else None

def encrypt_value(plain: str) -> str:
    if not FERNET:
        return plain
    return FERNET.encrypt(plain.encode()).decode()

def decrypt_value(cipher: str) -> str:
    if not FERNET:
        return cipher
    try:
        return FERNET.decrypt(cipher.encode()).decode()
    except Exception:
        return None

# --- API key helpers for bot/client control ---
API_KEYS_HASH = 'bot:api_keys'
BANS_SET = 'security:bans'

def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt.hex() + ':' + dk.hex()

def _is_api_key(token: str) -> bool:
    if not token:
        return False
    # direct WEB_API_KEY match first
    if WEB_API_KEY and token == WEB_API_KEY:
        return True
    try:
        val = r.hget(API_KEYS_HASH, token)
        return val is not None
    except Exception:
        return False

def _ban_list() -> list:
    try:
        raw = r.smembers(BANS_SET) or []
        out = []
        for x in raw:
            try:
                out.append(x.decode() if isinstance(x, bytes) else str(x))
            except Exception:
                continue
        return sorted(out)
    except Exception:
        return []

def _is_banned(value: str) -> bool:
    if not value:
        return False
    try:
        return r.sismember(BANS_SET, value)
    except Exception:
        return False

def _add_ban(value: str):
    if not value:
        return
    r.sadd(BANS_SET, value)

def _remove_ban(value: str):
    if not value:
        return
    r.srem(BANS_SET, value)


def geolocate_ip(ip: str) -> Optional[dict]:
    if not ip:
        return None
    try:
        resp = requests.get(f'https://ipapi.co/{ip}/json/', timeout=1.2)
        if not resp.ok:
            return None
        data = resp.json()
        return {
            'ip': ip,
            'city': data.get('city'),
            'country': data.get('country_name') or data.get('country'),
            'lat': data.get('latitude'),
            'lon': data.get('longitude'),
            'org': data.get('org')
        }
    except Exception:
        return None

def check_auth(request: Request) -> bool:
    try:
        have_custom_keys = r.hlen(API_KEYS_HASH) > 0
    except Exception:
        have_custom_keys = False
    if not WEB_API_KEY and not have_custom_keys:
        return True
    auth = request.headers.get('authorization')
    xapi = request.headers.get('x-api-key')
    if xapi and _is_api_key(xapi):
        return True
    if auth and auth.lower().startswith('bearer '):
        token = auth.split(None, 1)[1]
        if _is_api_key(token):
            return True
        # check session
        v = r.get(f'web:session:{token}')
        if v:
            dec = decrypt_value(v.decode()) if isinstance(v, bytes) else decrypt_value(v)
            if dec:
                try:
                    json.loads(dec)
                    return True
                except Exception:
                    return False
    return False


def get_session_from_request(request: Request) -> Optional[dict]:
    # Return session dict if Authorization Bearer token corresponds to a stored session
    auth = request.headers.get('authorization')
    if auth and auth.lower().startswith('bearer '):
        token = auth.split(None, 1)[1]
        v = r.get(f'web:session:{token}')
        if v:
            dec = decrypt_value(v.decode()) if isinstance(v, bytes) else decrypt_value(v)
            if dec:
                try:
                    return json.loads(dec)
                except Exception:
                    return None
    return None

def _sanitize_user_records() -> list:
    out = []
    try:
        for k in r.scan_iter(match='web:user:*'):
            name = k.decode() if isinstance(k, bytes) else k
            username = name.split(':', 2)[-1]
            rec = r.get(k)
            if not rec:
                continue
            try:
                obj = json.loads(rec.decode() if isinstance(rec, bytes) else rec)
            except Exception:
                obj = {}
            out.append({
                'user': username,
                'is_admin': bool(obj.get('is_admin')),
                'created_at': obj.get('created_at')
            })
    except Exception:
        return []
    return sorted(out, key=lambda x: x.get('user') or '')

def _delete_user_sessions(username: str):
    try:
        for key in r.scan_iter(match='web:session:*'):
            try:
                v = r.get(key)
                if not v:
                    continue
                dec = decrypt_value(v.decode() if isinstance(v, bytes) else v)
                if not dec:
                    continue
                obj = json.loads(dec)
                if obj.get('user') == username:
                    r.delete(key)
            except Exception:
                continue
    except Exception:
        pass


# Static files mount moved to the end of this file to avoid shadowing API routes.

@app.middleware('http')
async def cors_and_auth(request: Request, call_next):
    # Authentication passthrough middleware. Leave CORS handling to CORSMiddleware.
    response = await call_next(request)
    return response

@app.get('/messages')
def get_messages(request: Request, limit: int = 20):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    items = r.lrange('web:messages', 0, limit-1) or []
    out = []
    for it in items:
        try:
            out.append(json.loads(it))
        except Exception:
            continue
    return out


@app.post('/translations/suggest')
def suggest_translation(payload: dict, request: Request):
    """Accept a translation suggestion. Payload: {lang, key, value, author (opt), comment (opt)}"""
    if not payload or not payload.get('lang') or not payload.get('key'):
        raise HTTPException(status_code=400, detail='invalid payload, require lang and key')
    sid = uuid.uuid4().hex
    obj = {
        'id': sid,
        'lang': payload.get('lang'),
        'scope': payload.get('scope') or 'bot',
        'key': payload.get('key'),
        'value': payload.get('value', ''),
        'author': payload.get('author') or None,
        'comment': payload.get('comment') or None,
        'status': 'pending',
        'created_at': int(time.time())
    }
    r.set(f'web:translation:suggestion:{sid}', json.dumps(obj))
    r.rpush('web:translation:suggestions', sid)
    return { 'status': 'ok', 'id': sid }


def is_admin_request(request: Request) -> bool:
    if not check_auth(request):
        return False
    sess = get_session_from_request(request)
    if sess and sess.get('is_admin'):
        return True
    xapi = request.headers.get('x-api-key')
    if xapi and WEB_API_KEY and xapi == WEB_API_KEY:
        return True
    return False


@app.get('/translations/suggestions')
def list_suggestions(request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    ids = r.lrange('web:translation:suggestions', 0, -1) or []
    out = []
    for sid in ids:
        try:
            sid_str = sid.decode() if isinstance(sid, bytes) else sid
            data = r.get(f'web:translation:suggestion:{sid_str}')
            if data:
                out.append(json.loads(data))
        except Exception:
            continue
    return out


@app.post('/translations/apply')
def apply_suggestion(payload: dict, request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    sid = payload.get('id') if payload else None
    if not sid:
        raise HTTPException(status_code=400, detail='id required')
    data = r.get(f'web:translation:suggestion:{sid}')
    if not data:
        raise HTTPException(status_code=404, detail='suggestion not found')
    sug = json.loads(data)
    try:
        repo_root = Path(__file__).resolve().parents[2]
    except Exception:
        repo_root = Path('.')
    scope = sug.get('scope') or payload.get('scope') or 'bot'
    i18n_dir = repo_root / 'web' / 'i18n' / scope
    i18n_dir.mkdir(parents=True, exist_ok=True)
    lang_file = i18n_dir / f"{sug['lang']}.json"
    cur = {}
    if lang_file.exists():
        try:
            cur = json.loads(lang_file.read_text(encoding='utf-8'))
        except Exception:
            cur = {}
    cur[sug['key']] = sug['value']
    lang_file.write_text(json.dumps(cur, indent=2, ensure_ascii=False), encoding='utf-8')
    sug['status'] = 'applied'
    applied_by = get_session_from_request(request)
    sug['applied_by'] = applied_by if applied_by else {'api_key': True}
    sug['applied_at'] = int(time.time())
    r.set(f'web:translation:suggestion:{sid}', json.dumps(sug))
    return { 'status': 'applied', 'id': sid }


@app.post('/processes/restart')
def processes_restart(payload: dict, request: Request):
    """Restart a named process. Payload: { name: 'python_bot' }
    Requires admin privileges (WEB_API_KEY or admin session).
    """
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('name'):
        raise HTTPException(status_code=400, detail='name required')
    name = payload.get('name')
    if name not in PROCESS_DEFS:
        raise HTTPException(status_code=400, detail='unknown process')
    try:
        pid = start_process(name)
        return { 'status': 'started', 'name': name, 'pid': pid }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- API keys management for bot/client control ---
@app.post('/bot/api-keys')
def create_api_key(payload: Optional[dict] = None, request: Request = None):
    """Generate and store a new API key for bot/control clients.
    Payload optional: { name: 'client-1' }
    Requires admin privileges.
    """
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    name = (payload or {}).get('name') or 'client'
    key = secrets.token_hex(32)
    meta = { 'name': name, 'created_at': int(time.time()) }
    try:
        r.hset(API_KEYS_HASH, key, json.dumps(meta))
    except Exception:
        raise HTTPException(status_code=500, detail='failed to store api key')
    return { 'status': 'created', 'key': key, 'meta': meta }


@app.get('/security/bans')
def list_bans(request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    return { 'bans': _ban_list() }


@app.post('/security/bans')
def add_ban(payload: dict, request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    val = payload.get('value') if payload else None
    if not val:
        raise HTTPException(status_code=400, detail='value required')
    _add_ban(str(val))
    return { 'status': 'added', 'value': str(val) }


@app.delete('/security/bans/{value}')
def delete_ban(value: str, request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    _remove_ban(value)
    return { 'status': 'removed', 'value': value }


@app.get('/geo/summary')
def geo_summary(request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    bots = []
    users = []
    try:
        for k in r.scan_iter(match='geo:bot:*'):
            name = k.decode() if isinstance(k, bytes) else k
            data = r.hgetall(name) or {}
            obj = { 'id': name.split(':',2)[-1] }
            for dk, dv in data.items():
                key = dk.decode() if isinstance(dk, bytes) else dk
                val = dv.decode() if isinstance(dv, bytes) else dv
                obj[key] = val
            bots.append(obj)
    except Exception:
        bots = []
    try:
        for k in r.scan_iter(match='geo:user:*'):
            name = k.decode() if isinstance(k, bytes) else k
            data = r.hgetall(name) or {}
            obj = { 'user': name.split(':',2)[-1] }
            for dk, dv in data.items():
                key = dk.decode() if isinstance(dk, bytes) else dk
                val = dv.decode() if isinstance(dv, bytes) else dv
                obj[key] = val
            users.append(obj)
    except Exception:
        users = []
    return { 'bots': bots, 'users': users }


@app.get('/bot/api-keys')
def list_api_keys(request: Request):
    """List stored API keys (hash bot:api_keys). Requires admin."""
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    out = []
    try:
        data = r.hgetall(API_KEYS_HASH) or {}
        for k, v in data.items():
            key = k.decode() if isinstance(k, bytes) else k
            try:
                meta = json.loads(v.decode() if isinstance(v, bytes) else v)
            except Exception:
                meta = None
            out.append({ 'key': key, 'meta': meta })
    except Exception:
        out = []
    return { 'keys': out }


@app.delete('/bot/api-keys/{token}')
def delete_api_key(token: str, request: Request):
    """Revoke a specific API key. Requires admin."""
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    try:
        removed = r.hdel(API_KEYS_HASH, token)
        if not removed:
            raise HTTPException(status_code=404, detail='not found')
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail='delete failed')
    return { 'status': 'deleted', 'key': token }


@app.post('/processes/start')
def processes_start(payload: dict, request: Request):
    """Start a named process. Payload: { name: 'python_bot' }
    Requires admin privileges similar to /processes/restart.
    """
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('name'):
        raise HTTPException(status_code=400, detail='name required')
    name = payload.get('name')
    if name not in PROCESS_DEFS:
        raise HTTPException(status_code=400, detail='unknown process')
    try:
        pid = start_process(name)
        return { 'status': 'started', 'name': name, 'pid': pid }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/processes/stop')
def processes_stop(payload: dict, request: Request):
    """Attempt to stop a named process. Payload: { name: 'python_bot' }
    This will try to read the pidfile and send SIGTERM to the process.
    """
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('name'):
        raise HTTPException(status_code=400, detail='name required')
    name = payload.get('name')
    if name not in PROCESS_DEFS:
        raise HTTPException(status_code=400, detail='unknown process')
    pid = read_pid(name)
    if not pid:
        return { 'status': 'not-running', 'name': name }
    try:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            # fallback: try terminate via subprocess on Windows if available
            try:
                import psutil
                p = psutil.Process(pid)
                p.terminate()
            except Exception:
                pass
        return { 'status': 'stopped', 'name': name, 'pid': pid }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/devices')
def get_devices(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    items = r.lrange('web:devices', 0, -1) or []
    out = []
    for it in items:
        try:
            obj = json.loads(it)
            out.append({ 'id': obj.get('id'), 'name': obj.get('name') })
        except Exception:
            continue
    return out


@app.get('/discover/lan')
def discover_lan(request: Request, subnet: str = '192.168.1.0/24', ports: str = '8000', limit: int = 64):
    """Scan a small LAN range for DBTeam web/status endpoints.

    Query params:
    - subnet: CIDR, default 192.168.1.0/24
    - ports: comma-separated ports, default 8000
    - limit: max hosts to scan from the subnet hosts list (to keep it fast)
    """
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')

    try:
        net = ipaddress.ip_network(subnet, strict=False)
    except Exception:
        raise HTTPException(status_code=400, detail='invalid subnet')

    try:
        port_list = [int(p) for p in ports.split(',') if p.strip()]
        port_list = [p for p in port_list if p > 0 and p < 65536]
    except Exception:
        raise HTTPException(status_code=400, detail='invalid ports')
    if not port_list:
        raise HTTPException(status_code=400, detail='no ports provided')

    hosts = list(net.hosts())
    if limit and limit > 0:
        hosts = hosts[:limit]

    found = []
    for h in hosts:
        for p in port_list:
            url = f'http://{h}:{p}/status'
            try:
                resp = requests.get(url, timeout=0.6)
                if not resp.ok:
                    continue
                data = None
                try:
                    data = resp.json()
                except Exception:
                    data = None
                entry = {
                    'host': str(h),
                    'port': p,
                    'url': url,
                    'status': data.get('status') if isinstance(data, dict) else None,
                    'pages': data.get('pages') if isinstance(data, dict) else None,
                }
                found.append(entry)
            except Exception:
                continue

    return { 'found': found, 'count': len(found) }


@app.get('/bot/stats')
def bot_stats(request: Request):
    """Return various bot-related statistics (messages, devices, tdlib events, processes)."""
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    out = {}
    try:
        out['messages_count'] = r.llen('web:messages')
    except Exception:
        out['messages_count'] = None
    try:
        out['tdlib_events_count'] = r.llen('tdlib:events')
        last = r.lindex('tdlib:events', 0)
        if last:
            try:
                out['tdlib_last_event'] = json.loads(last.decode() if isinstance(last, bytes) else last)
            except Exception:
                out['tdlib_last_event'] = str(last)
        else:
            out['tdlib_last_event'] = None
    except Exception:
        out['tdlib_events_count'] = None
        out['tdlib_last_event'] = None
    try:
        items = r.lrange('web:devices', 0, -1) or []
        devs = []
        for it in items:
            try:
                obj = json.loads(it.decode() if isinstance(it, bytes) else it)
                devs.append({'id': obj.get('id'), 'name': obj.get('name')})
            except Exception:
                continue
        out['devices'] = devs
    except Exception:
        out['devices'] = None
    # processes
    try:
        out['processes'] = [ process_status(n) for n in PROCESS_DEFS.keys() ]
    except Exception:
        out['processes'] = None
    # uptime basic
    try:
        out['server_uptime'] = int(time.time()) - START_TIME
    except Exception:
        out['server_uptime'] = None
    return out


@app.post('/bot/start')
def bot_start(payload: Optional[dict] = None, request: Request = None):
    """Start the `python_bot` process (admin only). Payload optional: { name: 'python_bot' }"""
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    name = 'python_bot'
    if payload and payload.get('name'):
        name = payload.get('name')
    if name not in PROCESS_DEFS:
        raise HTTPException(status_code=400, detail='unknown process')
    try:
        pid = start_process(name)
        return { 'status': 'started', 'name': name, 'pid': pid }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/bot/accounts')
def bot_accounts(request: Request):
    """Return list of registered bot accounts (from `web:devices`) and their Telegram getMe status."""
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    admin = is_admin_request(request)
    items = r.lrange('web:devices', 0, -1) or []
    out = []
    for it in items:
        try:
            obj = json.loads(it.decode() if isinstance(it, bytes) else it)
        except Exception:
            continue
        device_id = obj.get('id')
        name = obj.get('name')
        token_enc = obj.get('token')
        has_token = bool(token_enc)
        token = None
        if token_enc:
            dec = decrypt_value(token_enc) if FERNET else None
            token = dec if dec else token_enc

        entry = { 'id': device_id, 'name': name, 'has_token': has_token }

        # include masked token only for admins (never reveal full token)
        if admin and has_token:
            try:
                t = token if token else token_enc
                ts = str(t)
                if len(ts) <= 10:
                    masked = ts[:2] + '***' + ts[-2:]
                else:
                    masked = ts[:6] + '***' + ts[-4:]
                entry['token_masked'] = masked
            except Exception:
                entry['token_masked'] = None

        # attempt to call Telegram getMe if we have a token
        if token:
            try:
                resp = requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=8)
                if resp.ok:
                    try:
                        jd = resp.json()
                    except Exception:
                        jd = { 'raw': resp.text }
                    entry['getMe'] = jd.get('result') if isinstance(jd, dict) and jd.get('ok') else jd
                    entry['getMe_status'] = 'ok' if resp.ok else 'error'
                else:
                    entry['getMe_error'] = f'status={resp.status_code}'
            except Exception as e:
                entry['getMe_error'] = str(e)
        else:
            entry['getMe'] = None

        out.append(entry)

    return { 'accounts': out }

@app.post('/devices/add')
def add_device(payload: dict, request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('id') or not payload.get('token'):
        raise HTTPException(status_code=400, detail='invalid payload, require id and token')
    if _is_banned(str(payload.get('id'))):
        raise HTTPException(status_code=403, detail='device id banned')
    enc = encrypt_value(payload.get('token'))
    obj = { 'id': payload.get('id'), 'name': payload.get('name') or payload.get('id'), 'token': enc }
    r.rpush('web:devices', json.dumps(obj))
    return { 'status': 'added' }


@app.post('/bot/announce')
def bot_announce(payload: dict, request: Request):
    """Endpoint para que un bot se auto-registre/sincronice.
    Requiere API key o sesión válida (check_auth). Payload mínimo: { id, token }.
    Campos opcionales: name, host, port, status_url.
    """
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('id') or not payload.get('token'):
        raise HTTPException(status_code=400, detail='id y token requeridos')

    dev_id = str(payload.get('id'))
    if _is_banned(dev_id) or _is_banned(str(payload.get('host') or '')):
        raise HTTPException(status_code=403, detail='banned bot or host')
    name = payload.get('name') or dev_id
    enc = encrypt_value(payload.get('token'))
    meta = {
        'id': dev_id,
        'name': name,
        'token': enc,
        'host': payload.get('host'),
        'port': payload.get('port'),
        'status_url': payload.get('status_url'),
        'updated_at': int(time.time())
    }

    # geolocate client IP and store
    try:
        ip = request.client.host if request and request.client else None
        if ip and not ip.startswith('127.'):
            geo = geolocate_ip(ip)
            if geo:
                r.hset(f'geo:bot:{dev_id}', mapping={
                    'ip': geo.get('ip') or ip,
                    'city': geo.get('city') or '',
                    'country': geo.get('country') or '',
                    'lat': geo.get('lat') or '',
                    'lon': geo.get('lon') or '',
                    'org': geo.get('org') or '',
                    'ts': int(time.time())
                })
    except Exception:
        pass

    try:
        items = r.lrange('web:devices', 0, -1) or []
        kept = []
        for it in items:
            try:
                obj = json.loads(it.decode() if isinstance(it, bytes) else it)
                if obj.get('id') == dev_id:
                    continue  # replace existing
                kept.append(obj)
            except Exception:
                continue
        kept.append(meta)
        pipe = r.pipeline()
        pipe.delete('web:devices')
        for k in kept:
            pipe.rpush('web:devices', json.dumps(k))
        pipe.execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail='store error: '+str(e))

    return { 'status': 'ok', 'id': dev_id, 'name': name }


@app.delete('/devices/{device_id}')
def delete_device(device_id: str, request: Request):
    """Remove a registered device by id from `web:devices` list."""
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    try:
        items = r.lrange('web:devices', 0, -1) or []
        kept = []
        found = False
        for it in items:
            try:
                obj = json.loads(it)
                if obj.get('id') == device_id:
                    found = True
                    continue
                kept.append(json.dumps(obj))
            except Exception:
                # if parse fails, keep original raw
                kept.append(it if isinstance(it, str) else (it.decode() if isinstance(it, bytes) else str(it)))
        # replace list atomically
        try:
            r.delete('web:devices')
        except Exception:
            pass
        for v in kept:
            try:
                r.rpush('web:devices', v)
            except Exception:
                continue
        if not found:
            raise HTTPException(status_code=404, detail='device not found')
        return { 'status': 'deleted', 'id': device_id }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/bot/verify')
def bot_verify(payload: dict, request: Request):
    """Verify a Telegram Bot token, register it as a device and import local bot data.
    Payload: { token: '<bot token>', id: '<optional device id>', name: '<optional name>' }
    Returns registered device info and imported data (infohashes, allowed_senders).
    """
    if not payload or not payload.get('token'):
        raise HTTPException(status_code=400, detail='token required')
    token = payload.get('token')
    # verify token with Telegram getMe
    try:
        resp = requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=10)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not resp.ok:
        raise HTTPException(status_code=400, detail=f'telegram error: {resp.text}')
    try:
        data = resp.json()
    except Exception:
        data = { 'ok': False }
    result = data.get('result') if isinstance(data, dict) else None
    bot_id = None
    bot_name = None
    if result:
        bot_id = result.get('id')
        bot_name = result.get('username') or result.get('first_name')

    # attempt to fetch a profile photo URL for the bot (best-effort)
    photo_url = None
    try:
        if bot_id:
            p = requests.get(f'https://api.telegram.org/bot{token}/getUserProfilePhotos', params={'user_id': bot_id, 'limit': 1}, timeout=10)
            if p.ok:
                pj = p.json()
                pres = pj.get('result') if isinstance(pj, dict) else None
                photos = pres.get('photos') if pres else None
                if photos and len(photos) > 0 and isinstance(photos[0], list):
                    sizes = photos[0]
                    if sizes:
                        file_id = sizes[-1].get('file_id')
                        if file_id:
                            gf = requests.get(f'https://api.telegram.org/bot{token}/getFile', params={'file_id': file_id}, timeout=10)
                            if gf.ok:
                                gfj = gf.json()
                                gfres = gfj.get('result') if isinstance(gfj, dict) else None
                                file_path = gfres.get('file_path') if gfres else None
                                if file_path:
                                    photo_url = f'https://api.telegram.org/file/bot{token}/{file_path}'
    except Exception:
        photo_url = None

    # choose device id
    device_id = payload.get('id') or (f'bot:{bot_id}' if bot_id else f'bot:{secrets.token_hex(6)}')
    device_name = payload.get('name') or bot_name or device_id

    # store encrypted token as a web device (reuse existing structure)
    enc = encrypt_value(token)
    obj = { 'id': device_id, 'name': device_name, 'token': enc }
    # avoid duplicates
    try:
        items = r.lrange('web:devices', 0, -1) or []
        exists = False
        for it in items:
            try:
                cur = json.loads(it)
                if cur.get('id') == obj['id']:
                    exists = True
                    break
            except Exception:
                continue
        if not exists:
            r.rpush('web:devices', json.dumps(obj))
    except Exception:
        # best-effort: ignore storage errors
        pass

    # Import bot-local data stored under storage prefix `dbteam:` (infohashes, allowed_senders)
    infohashes = []
    try:
        for ih in (r.smembers('dbteam:infohashes') or set()):
            try:
                infohashes.append(ih.decode() if isinstance(ih, bytes) else ih)
            except Exception:
                continue
    except Exception:
        infohashes = []

    allowed_senders = {}
    try:
        for k in r.scan_iter(match='dbteam:allowed_senders:*'):
            try:
                keyname = k.decode() if isinstance(k, bytes) else k
                parts = keyname.split(':')
                chatid = parts[-1]
                members = r.smembers(keyname) or set()
                allowed_senders[str(chatid)] = [int(x) for x in [(m.decode() if isinstance(m, bytes) else m) for m in members]]
            except Exception:
                continue
    except Exception:
        allowed_senders = {}

    return { 'status': 'ok', 'device': { 'id': device_id, 'name': device_name }, 'infohashes': infohashes, 'allowed_senders': allowed_senders, 'getMe': result, 'photo_url': photo_url }


@app.get('/bot/data')
def bot_data(request: Request):
    """Return imported bot-local data (infohashes and allowed_senders) for the web UI."""
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    infohashes = []
    try:
        for ih in (r.smembers('dbteam:infohashes') or set()):
            try:
                infohashes.append(ih.decode() if isinstance(ih, bytes) else ih)
            except Exception:
                continue
    except Exception:
        infohashes = []
    allowed_senders = {}
    try:
        for k in r.scan_iter(match='dbteam:allowed_senders:*'):
            try:
                keyname = k.decode() if isinstance(k, bytes) else k
                parts = keyname.split(':')
                chatid = parts[-1]
                members = r.smembers(keyname) or set()
                allowed_senders[str(chatid)] = [int(x) for x in [(m.decode() if isinstance(m, bytes) else m) for m in members]]
            except Exception:
                continue
    except Exception:
        allowed_senders = {}
    return { 'infohashes': infohashes, 'allowed_senders': allowed_senders }


@app.post('/bot/files')
def bot_files(payload: dict, request: Request):
    """Best-effort: list files uploaded by the bot by scanning recent getUpdates.
    Payload: { token: '<bot token>', limit: 50 }
    Returns: list of { chat_id, date, type, file_id, file_name (opt), file_url }
    Note: this only sees updates available via getUpdates (webhook bots may not have history here).
    """
    if not payload or not payload.get('token'):
        raise HTTPException(status_code=400, detail='token required')
    token = payload.get('token')
    limit = int(payload.get('limit', 50))
    try:
        resp = requests.get(f'https://api.telegram.org/bot{token}/getUpdates', params={'limit': limit}, timeout=10)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not resp.ok:
        raise HTTPException(status_code=400, detail=f'telegram error: {resp.text}')
    try:
        data = resp.json()
    except Exception:
        data = { 'result': [] }
    updates = data.get('result') if isinstance(data, dict) else []
    out_files = []
    for u in updates:
        for msgkey in ('message', 'edited_message'):
            msg = u.get(msgkey)
            if not msg:
                continue
            frm = msg.get('from') or {}
            if not frm.get('is_bot'):
                continue
            chat = msg.get('chat') or {}
            chat_id = chat.get('id')
            date = msg.get('date')
            # check common attachment types
            file_id = None
            ftype = None
            fname = None
            if 'photo' in msg and msg.get('photo'):
                sizes = msg.get('photo')
                if isinstance(sizes, list) and sizes:
                    file_id = sizes[-1].get('file_id')
                    ftype = 'photo'
            if not file_id and msg.get('document'):
                file_id = msg['document'].get('file_id')
                fname = msg['document'].get('file_name')
                ftype = 'document'
            if not file_id and msg.get('video'):
                file_id = msg['video'].get('file_id')
                ftype = 'video'
            if not file_id and msg.get('audio'):
                file_id = msg['audio'].get('file_id')
                ftype = 'audio'
            if not file_id and msg.get('voice'):
                file_id = msg['voice'].get('file_id')
                ftype = 'voice'
            if file_id:
                # resolve file path
                try:
                    gf = requests.get(f'https://api.telegram.org/bot{token}/getFile', params={'file_id': file_id}, timeout=10)
                    if gf.ok:
                        gfj = gf.json()
                        gfres = gfj.get('result') if isinstance(gfj, dict) else None
                        file_path = gfres.get('file_path') if gfres else None
                        if file_path:
                            file_url = f'https://api.telegram.org/file/bot{token}/{file_path}'
                        else:
                            file_url = None
                    else:
                        file_url = None
                except Exception:
                    file_url = None
                out_files.append({ 'chat_id': chat_id, 'date': date, 'type': ftype, 'file_id': file_id, 'file_name': fname, 'file_url': file_url })
    return { 'files': out_files }

@app.post('/send')
def send_message(payload: dict, request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('chat_id') or not payload.get('text'):
        raise HTTPException(status_code=400, detail='invalid payload, require chat_id and text')
    token_to_use = BOT_TOKEN
    if payload.get('device_id'):
        items = r.lrange('web:devices', 0, -1) or []
        for it in items:
            try:
                obj = json.loads(it)
                if obj.get('id') == payload.get('device_id') and obj.get('token'):
                    dec = decrypt_value(obj.get('token'))
                    if dec:
                        token_to_use = dec
                    else:
                        token_to_use = obj.get('token')
                    break
            except Exception:
                continue
    if not token_to_use:
        raise HTTPException(status_code=500, detail='no BOT_TOKEN available')
    url = f'https://api.telegram.org/bot{token_to_use}/sendMessage'
    body = { 'chat_id': payload.get('chat_id'), 'text': payload.get('text') }
    resp = requests.post(url, json=body)
    if not resp.ok:
        raise HTTPException(status_code=500, detail=resp.text)
    return resp.json()


@app.post('/bot/send')
def bot_send(payload: dict, request: Request):
    """Alias endpoint to send via server-side Bot API. Accepts {chat_id, text, attachment_url (opt), device_id (opt)}"""
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('chat_id'):
        raise HTTPException(status_code=400, detail='chat_id required')
    token_to_use = BOT_TOKEN
    if payload.get('device_id'):
        items = r.lrange('web:devices', 0, -1) or []
        for it in items:
            try:
                obj = json.loads(it)
                if obj.get('id') == payload.get('device_id') and obj.get('token'):
                    dec = decrypt_value(obj.get('token'))
                    if dec:
                        token_to_use = dec
                    else:
                        token_to_use = obj.get('token')
                    break
            except Exception:
                continue
    if not token_to_use:
        raise HTTPException(status_code=500, detail='no BOT_TOKEN available')

    # choose send method depending on presence of attachment and file type
    attach = payload.get('attachment_url')
    try:
        if attach and re.search(r'\.(jpg|jpeg|png|gif|webp)(\?|$)', str(attach).lower()):
            url = f'https://api.telegram.org/bot{token_to_use}/sendPhoto'
            body = { 'chat_id': payload.get('chat_id'), 'photo': attach, 'caption': payload.get('text', '') }
        else:
            url = f'https://api.telegram.org/bot{token_to_use}/sendMessage'
            body = { 'chat_id': payload.get('chat_id'), 'text': payload.get('text', '') }
        resp = requests.post(url, json=body)
        if not resp.ok:
            raise HTTPException(status_code=500, detail=resp.text)
        return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/send_user')
def send_user(payload: dict, request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('chat_id') or not payload.get('text'):
        raise HTTPException(status_code=400, detail='invalid payload, require chat_id and text')
    outobj = { 'chat_id': payload.get('chat_id'), 'text': payload.get('text') }
    if payload.get('device_id'):
        outobj['device_id'] = payload.get('device_id')
    r.rpush('web:outbox', json.dumps(outobj))
    return { 'status': 'queued' }


@app.post('/ai')
def ai_generate(payload: dict, request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('prompt'):
        raise HTTPException(status_code=400, detail='invalid payload, require prompt')
    provider = payload.get('provider', 'local')
    model = payload.get('model', 'gpt2')

    if provider == 'local':
        try:
            from transformers import pipeline
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'transformers not installed: {e}')
        try:
            gen = pipeline('text-generation', model=model)
            params = {
                'max_length': int(payload.get('max_length', 128)),
                'do_sample': bool(payload.get('do_sample', True)),
                'top_k': int(payload.get('top_k', 50)),
                'num_return_sequences': int(payload.get('num_return_sequences', 1)),
            }
            res = gen(payload.get('prompt'), **params)
            return { 'provider': 'local', 'model': model, 'result': res }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    elif provider == 'huggingface':
        hf_key = os.getenv('HUGGINGFACE_API_KEY', '')
        if not hf_key:
            raise HTTPException(status_code=500, detail='HUGGINGFACE_API_KEY not set')
        hf_model = model
        url = f'https://api-inference.huggingface.co/models/{hf_model}'
        headers = {'Authorization': f'Bearer {hf_key}'}
        body = { 'inputs': payload.get('prompt'), 'parameters': payload.get('parameters', {}) }
        resp = requests.post(url, headers=headers, json=body)
        if not resp.ok:
            raise HTTPException(status_code=500, detail=resp.text)
        return resp.json()

    elif provider == 'openai':
        openai_key = os.getenv('OPENAI_API_KEY', '')
        if not openai_key:
            raise HTTPException(status_code=500, detail='OPENAI_API_KEY not set')
        data = { 'model': model, 'prompt': payload.get('prompt'), 'max_tokens': int(payload.get('max_tokens', 150)) }
        headers = { 'Authorization': f'Bearer {openai_key}', 'Content-Type': 'application/json' }
        resp = requests.post('https://api.openai.com/v1/completions', headers=headers, json=data)
        if not resp.ok:
            raise HTTPException(status_code=500, detail=resp.text)
        return resp.json()

    else:
        raise HTTPException(status_code=400, detail='unknown provider')


@app.get('/models/list')
def models_list(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    try:
        items = r.smembers('local_models') or set()
        out = [ (i.decode() if isinstance(i, bytes) else i) for i in items ]
        return { 'models': out }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _install_model_background(model_name: str):
    try:
        from transformers import pipeline
        # instantiate pipeline to trigger model download
        pipeline('text-generation', model=model_name)
        try:
            r.sadd('local_models', model_name)
        except Exception:
            pass
    except Exception:
        # ignore errors in background
        pass


@app.post('/models/install')
def models_install(payload: dict, request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('model'):
        raise HTTPException(status_code=400, detail='model required')
    model_name = payload.get('model')
    # start background thread to download and cache the model
    try:
        t = threading.Thread(target=_install_model_background, args=(model_name,), daemon=True)
        t.start()
        return { 'status': 'installing', 'model': model_name }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/models/run')
def models_run(payload: dict, request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('prompt') or not payload.get('model'):
        raise HTTPException(status_code=400, detail='prompt and model required')
    model = payload.get('model')
    try:
        from transformers import pipeline
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'transformers not installed: {e}')
    try:
        gen = pipeline('text-generation', model=model)
        params = {
            'max_length': int(payload.get('max_length', 128)),
            'do_sample': bool(payload.get('do_sample', True)),
            'top_k': int(payload.get('top_k', 50)),
            'num_return_sequences': int(payload.get('num_return_sequences', 1)),
        }
        res = gen(payload.get('prompt'), **params)
        return { 'provider': 'local', 'model': model, 'result': res }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/auth')
def auth(payload: dict):
    # verify Telegram login widget
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail='BOT_TOKEN not set on server')
    if not payload or not payload.get('hash'):
        raise HTTPException(status_code=400, detail='invalid auth payload')
    parts = [k for k in payload.keys() if k != 'hash']
    parts.sort()
    data_check = '\n'.join([f"{k}={payload[k]}" for k in parts])
    key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    calc = hmac.new(key, data_check.encode(), hashlib.sha256).hexdigest()
    if calc != payload.get('hash'):
        raise HTTPException(status_code=401, detail='invalid signature')
    token = secrets.token_hex(32)
    sess = { 'id': payload.get('id'), 'first_name': payload.get('first_name'), 'last_name': payload.get('last_name'), 'username': payload.get('username') }
    sess_raw = json.dumps(sess)
    enc = encrypt_value(sess_raw)
    r.setex(f'web:session:{token}', 3600, enc)
    return { 'token': token, 'ttl': 3600 }


@app.post('/auth/login')
def auth_login(payload: dict, request: Request):
    """Simple login endpoint for the web UI.
    Accepts either { "api_key": "..." } or { "user": "...", "pass": "..." }.
    If the provided api_key or pass equals `WEB_API_KEY` the request is accepted and
    a session token is returned. The session includes `is_admin` when authenticated
    with the API key.
    """
    if not payload:
        raise HTTPException(status_code=400, detail='invalid payload')
    # api_key path
    if payload.get('api_key'):
        if WEB_API_KEY and payload.get('api_key') == WEB_API_KEY:
            token = secrets.token_hex(32)
            sess = { 'user': 'api_key_user', 'is_admin': True }
            enc = encrypt_value(json.dumps(sess))
            r.setex(f'web:session:{token}', 3600, enc)
            return { 'token': token, 'ttl': 3600 }
        else:
            raise HTTPException(status_code=401, detail='invalid api_key')

    # username/password path — first check stored users in Redis
    user = payload.get('user')
    passwd = payload.get('pass')
    if not user or not passwd:
        raise HTTPException(status_code=400, detail='user and pass required')

    def _verify_password(stored: str, password: str) -> bool:
        try:
            salt_hex, dk_hex = stored.split(':')
            salt = bytes.fromhex(salt_hex)
            dk = bytes.fromhex(dk_hex)
            test = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
            return _hmaclib.compare_digest(test, dk)
        except Exception:
            return False

    user_key = f'web:user:{user}'
    stored = r.get(user_key)
    if stored:
        try:
            obj = json.loads(stored)
            pw = obj.get('pw')
            if pw and _verify_password(pw, passwd):
                token = secrets.token_hex(32)
                sess = { 'user': user, 'is_admin': bool(obj.get('is_admin')) }
                enc = encrypt_value(json.dumps(sess))
                r.setex(f'web:session:{token}', 3600, enc)
                # geolocate login IP
                try:
                    ip = request.client.host if request and request.client else None
                    if ip and not str(ip).startswith('127.'):
                        geo = geolocate_ip(str(ip))
                        if geo:
                            r.hset(f'geo:user:{user}', mapping={
                                'ip': geo.get('ip') or str(ip),
                                'city': geo.get('city') or '',
                                'country': geo.get('country') or '',
                                'lat': geo.get('lat') or '',
                                'lon': geo.get('lon') or '',
                                'org': geo.get('org') or '',
                                'ts': int(time.time())
                            })
                except Exception:
                    pass
                return { 'token': token, 'ttl': 3600 }
            else:
                raise HTTPException(status_code=401, detail='invalid credentials')
        except Exception:
            raise HTTPException(status_code=500, detail='error reading user')

    # fallback: use WEB_API_KEY as password backend if set
    if WEB_API_KEY and passwd == WEB_API_KEY:
        token = secrets.token_hex(32)
        sess = { 'user': user, 'is_admin': False }
        enc = encrypt_value(json.dumps(sess))
        r.setex(f'web:session:{token}', 3600, enc)
        return { 'token': token, 'ttl': 3600 }
    raise HTTPException(status_code=401, detail='invalid credentials')


@app.post('/auth/register')
def auth_register(payload: dict):
    """Register a new user: payload { user, pass, is_admin (opt) }.
    Stores a salted PBKDF2-SHA256 hash in Redis under `web:user:<user>`.
    """
    if not payload or not payload.get('user') or not payload.get('pass'):
        raise HTTPException(status_code=400, detail='user and pass required')
    user = payload.get('user')
    passwd = payload.get('pass')
    user_key = f'web:user:{user}'
    if r.exists(user_key):
        raise HTTPException(status_code=409, detail='user exists')

    hashed = _hash_password(passwd)
    obj = { 'pw': hashed, 'created_at': int(time.time()), 'is_admin': bool(payload.get('is_admin', False)) }
    r.set(user_key, json.dumps(obj))
    return { 'status': 'created', 'user': user }


# --- Admin: user management ---
@app.get('/admin/users')
def admin_list_users(request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    return { 'users': _sanitize_user_records() }


@app.post('/admin/users')
def admin_create_user(payload: dict, request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('user') or not payload.get('pass'):
        raise HTTPException(status_code=400, detail='user and pass required')
    user = payload.get('user')
    passwd = payload.get('pass')
    user_key = f'web:user:{user}'
    if r.exists(user_key):
        raise HTTPException(status_code=409, detail='user exists')
    hashed = _hash_password(passwd)
    obj = { 'pw': hashed, 'created_at': int(time.time()), 'is_admin': bool(payload.get('is_admin', False)) }
    try:
        r.set(user_key, json.dumps(obj))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return { 'status': 'created', 'user': user }


@app.post('/admin/users/reset')
def admin_reset_user(payload: dict, request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not payload.get('user') or not payload.get('pass'):
        raise HTTPException(status_code=400, detail='user and pass required')
    user = payload.get('user')
    passwd = payload.get('pass')
    user_key = f'web:user:{user}'
    stored = r.get(user_key)
    if not stored:
        raise HTTPException(status_code=404, detail='user not found')
    try:
        obj = json.loads(stored.decode() if isinstance(stored, bytes) else stored)
    except Exception:
        obj = {}
    obj['pw'] = _hash_password(passwd)
    if 'is_admin' in payload:
        obj['is_admin'] = bool(payload.get('is_admin'))
    r.set(user_key, json.dumps(obj))
    _delete_user_sessions(user)
    return { 'status': 'reset', 'user': user }


@app.delete('/admin/users/{username}')
def admin_delete_user(username: str, request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    key = f'web:user:{username}'
    if not r.exists(key):
        raise HTTPException(status_code=404, detail='user not found')
    try:
        r.delete(key)
        _delete_user_sessions(username)
        return { 'status': 'deleted', 'user': username }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/admin/overview')
def admin_overview(request: Request):
    if not is_admin_request(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    out = {}
    try:
        out['users'] = _sanitize_user_records()
    except Exception as e:
        out['users_error'] = str(e)
    try:
        out['status'] = status_info(request)
    except Exception as e:
        out['status_error'] = str(e)
    try:
        out['bot_stats'] = bot_stats(request)
    except Exception as e:
        out['bot_stats_error'] = str(e)
    try:
        out['bot_accounts'] = bot_accounts(request)
    except Exception as e:
        out['bot_accounts_error'] = str(e)
    return out


@app.get('/settings/backup')
def settings_backup(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    # fetch stored settings from redis key 'web:settings'
    v = r.get('web:settings')
    if not v:
        return {}
    try:
        return json.loads(v)
    except Exception:
        return {}


@app.post('/settings/restore')
def settings_restore(payload: dict, request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    if not payload or not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail='invalid payload, expect JSON object')
    # store whole settings object in redis
    try:
        r.set('web:settings', json.dumps(payload))
        return { 'status': 'ok' }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/settings/favicon')
def upload_favicon(payload: dict, request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail='unauthorized')
    # payload should include either user_id or use session
    user = get_session_from_request(request)
    user_id = None
    if user and user.get('id'):
        user_id = str(user.get('id'))
    else:
        user_id = str(payload.get('user_id')) if payload.get('user_id') else None
    if not user_id:
        raise HTTPException(status_code=400, detail='user id not provided')
    favicon_b64 = payload.get('favicon')
    if not favicon_b64:
        raise HTTPException(status_code=400, detail='favicon (base64) required')
    try:
        # validate base64
        _ = base64.b64decode(favicon_b64)
        r.set(f'web:settings:favicon:{user_id}', favicon_b64)
        return { 'status': 'ok' }
    except Exception as e:
        raise HTTPException(status_code=400, detail='invalid base64')


@app.get('/settings/favicon/{user_id}')
def get_favicon(user_id: str):
    v = r.get(f'web:settings:favicon:{user_id}')
    if not v:
        raise HTTPException(status_code=404, detail='not found')
    try:
        b = base64.b64decode(v if isinstance(v, bytes) else v)
        return JSONResponse(content=b, media_type='image/png')
    except Exception:
        raise HTTPException(status_code=500, detail='cannot decode favicon')


@app.get('/pages.json')
def pages_list():
    """Return a JSON list of available web pages. If `web/pages.json` exists, return it.
    Otherwise scan the `web/` directory for HTML files and return href/label pairs.
    """
    # locate repository root from this file: ../../
    try:
        repo_root = Path(__file__).resolve().parents[2]
    except Exception:
        repo_root = Path('.')
    web_dir = repo_root / 'web'
    pages_json = web_dir / 'pages.json'
    if pages_json.exists():
        try:
            return json.loads(pages_json.read_text(encoding='utf-8'))
        except Exception:
            pass

    out = []
    try:
        if web_dir.exists() and web_dir.is_dir():
            for p in sorted(web_dir.glob('*.html')):
                href = p.name
                name = p.stem.replace('_', ' ').replace('-', ' ')
                label = name.title()
                if label.lower() == 'index':
                    label = 'Inicio'
                out.append({'href': href, 'label': label})
    except Exception:
        pass
    return out


@app.get('/status')
def status_info(request: Request):
    """Return basic status information: uptime, current time, redis health and pages."""
    now = int(time.time())
    uptime = now - START_TIME
    redis_status = {'ok': False}
    try:
        # ping and some info
        redis_status['ok'] = bool(r.ping())
        info = r.info()
        redis_status['connected_clients'] = info.get('connected_clients')
        redis_status['used_memory_human'] = info.get('used_memory_human')
    except Exception as e:
        redis_status['error'] = str(e)

    pages = []
    try:
        repo_root = Path(__file__).resolve().parents[2]
        p = repo_root / 'web' / 'pages.json'
        if p.exists():
            pages = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        pages = []

    # gather counts (safe: use scan/llen, avoid exposing secret values)
    counts = {}
    try:
        counts['messages'] = r.llen('web:messages')
    except Exception:
        counts['messages'] = None
    try:
        counts['devices'] = r.llen('web:devices')
    except Exception:
        counts['devices'] = None
    try:
        counts['translation_suggestions'] = r.llen('web:translation:suggestions')
    except Exception:
        counts['translation_suggestions'] = None
    # count users and sessions via scan_iter (may be approximate but safe)
    try:
        users = 0
        for _ in r.scan_iter(match='web:user:*'):
            users += 1
        counts['users'] = users
    except Exception:
        counts['users'] = None
    try:
        sessions = 0
        for _ in r.scan_iter(match='web:session:*'):
            sessions += 1
        counts['sessions'] = sessions
    except Exception:
        counts['sessions'] = None

    # count how many sessions were created via API key (if we can decrypt sessions)
    api_key_sessions = None
    try:
        api_key_sessions = 0
        for k in r.scan_iter(match='web:session:*'):
            v = r.get(k)
            if not v:
                continue
            raw = v.decode() if isinstance(v, bytes) else v
            dec = decrypt_value(raw) if FERNET else None
            if not dec:
                continue
            try:
                obj = json.loads(dec)
            except Exception:
                continue
            if obj and obj.get('user') == 'api_key_user':
                api_key_sessions += 1
    except Exception:
        api_key_sessions = None

    # build list of masked session ids created via API key
    api_key_session_ids = None
    try:
        api_key_session_ids = []
        for k in r.scan_iter(match='web:session:*'):
            keyname = k.decode() if isinstance(k, bytes) else k
            token_part = keyname.split(':',2)[2] if ':' in keyname else keyname
            v = r.get(k)
            if not v:
                continue
            raw = v.decode() if isinstance(v, bytes) else v
            dec = decrypt_value(raw) if FERNET else None
            if not dec:
                continue
            try:
                obj = json.loads(dec)
            except Exception:
                continue
            if obj and obj.get('user') == 'api_key_user':
                t = token_part or ''
                if not t:
                    continue
                if len(t) <= 10:
                    masked = t[:2] + '***' + t[-2:]
                else:
                    masked = t[:6] + '***' + t[-4:]
                api_key_session_ids.append(masked)
    except Exception:
        api_key_session_ids = None

    # include devices list (id and name only) without revealing stored tokens
    devices_list = None
    try:
        devices_list = []
        items = r.lrange('web:devices', 0, -1) or []
        for it in items:
            try:
                obj = json.loads(it.decode() if isinstance(it, bytes) else it)
                devices_list.append({'id': obj.get('id'), 'name': obj.get('name')})
            except Exception:
                continue
    except Exception:
        devices_list = None

    # include TTL (seconds remaining) for sessions created via API key (masked ids)
    api_key_sessions_with_ttl = None
    try:
        api_key_sessions_with_ttl = []
        for k in r.scan_iter(match='web:session:*'):
            keyname = k.decode() if isinstance(k, bytes) else k
            token_part = keyname.split(':',2)[2] if ':' in keyname else keyname
            v = r.get(k)
            if not v:
                continue
            raw = v.decode() if isinstance(v, bytes) else v
            dec = decrypt_value(raw) if FERNET else None
            if not dec:
                continue
            try:
                obj = json.loads(dec)
            except Exception:
                continue
            if obj and obj.get('user') == 'api_key_user':
                ttl = None
                try:
                    ttl_val = r.ttl(k)
                    # redis returns -2 if key missing, -1 if no expire
                    if isinstance(ttl_val, int) and ttl_val >= 0:
                        ttl = int(ttl_val)
                except Exception:
                    ttl = None
                t = token_part or ''
                if not t:
                    continue
                if len(t) <= 10:
                    masked = t[:2] + '***' + t[-2:]
                else:
                    masked = t[:6] + '***' + t[-4:]
                api_key_sessions_with_ttl.append({'id': masked, 'ttl_seconds': ttl})
    except Exception:
        api_key_sessions_with_ttl = None

    # applied translations: count suggestion keys with status == 'applied'
    try:
        applied = 0
        per_lang = {}
        for sid in r.scan_iter(match='web:translation:suggestion:*'):
            try:
                data = r.get(sid)
                if not data:
                    continue
                obj = json.loads(data)
                if obj.get('status') == 'applied':
                    applied += 1
                    lang = obj.get('lang') or 'unknown'
                    per_lang[lang] = per_lang.get(lang, 0) + 1
            except Exception:
                continue
        counts['translation_suggestions_applied'] = applied
        counts['translation_suggestions_applied_per_lang'] = per_lang
    except Exception:
        counts['translation_suggestions_applied'] = None

    api_info = {
        'web_api_key_set': bool(WEB_API_KEY),
        'web_api_origin': WEB_API_ORIGIN or None,
        'bot_token_set': bool(BOT_TOKEN),
    }

    # include masked api key info (never reveal full key)
    try:
        if WEB_API_KEY:
            k = str(WEB_API_KEY)
            # show first 2 and last 2 characters with length
            if len(k) <= 6:
                masked = k[0:1] + '***' + k[-1:]
            else:
                masked = k[0:2] + '***' + k[-2:]
            api_info['web_api_key_masked'] = masked
            api_info['web_api_key_length'] = len(k)
        else:
            api_info['web_api_key_masked'] = None
            api_info['web_api_key_length'] = 0
    except Exception:
        api_info['web_api_key_masked'] = None
        api_info['web_api_key_length'] = None

    api_info['sessions_via_api_key'] = api_key_sessions
    api_info['sessions_via_api_key_ids'] = api_key_session_ids


    supported_endpoints = [
        {'path': '/status', 'method': 'GET', 'desc': 'Server status, uptime, redis and pages'},
        {'path': '/auth/register', 'method': 'POST', 'desc': 'Register a new user (user, pass) stored in Redis'},
        {'path': '/auth/login', 'method': 'POST', 'desc': 'Login using api_key or user/pass, returns session token'},
        {'path': '/admin/users', 'method': 'GET/POST/DELETE', 'desc': 'List, create or delete users (admin)'},
        {'path': '/admin/users/reset', 'method': 'POST', 'desc': 'Reset password or role for a user (admin)'},
        {'path': '/admin/overview', 'method': 'GET', 'desc': 'Combined status, bots and users (admin)'},
        {'path': '/translations/suggest', 'method': 'POST', 'desc': 'Submit a translation suggestion'},
        {'path': '/translations/suggestions', 'method': 'GET', 'desc': 'List pending translation suggestions (admin)'},
        {'path': '/translations/apply', 'method': 'POST', 'desc': 'Apply a suggestion to i18n files (admin)'}
    ]

    explanations = {
        'time': 'Current server unix timestamp',
        'uptime': 'Seconds since the server process started',
        'redis.ok': 'Whether Redis responded to a ping',
        'redis.connected_clients': 'Number of clients connected to Redis (if available)',
        'redis.used_memory_human': 'Human-readable Redis memory usage (if available)',
        'counts': 'Counts of items stored in Redis relevant to the web UI',
        'api_info': 'Flags that describe configured API-related settings (do not include secret values)',
        'supported_endpoints': 'Important API endpoints and short descriptions'
    }

    # i18n file stats: file size and number of keys
    i18n_stats = {}
    try:
        repo_root = Path(__file__).resolve().parents[2]
        i18n_dir = repo_root / 'web' / 'i18n'
        if i18n_dir.exists() and i18n_dir.is_dir():
            for p in sorted(i18n_dir.glob('*.json')):
                try:
                    txt = p.read_text(encoding='utf-8')
                    js = json.loads(txt)
                    i18n_stats[p.name] = { 'bytes': p.stat().st_size, 'keys': len(js) }
                except Exception:
                    i18n_stats[p.name] = { 'bytes': None, 'keys': None }
    except Exception:
        i18n_stats = {}

    # try to determine current commit SHA from .git
    git_sha = None
    git_last = None
    try:
        repo_root = Path(__file__).resolve().parents[2]
        head = (repo_root / '.git' / 'HEAD')
        if head.exists():
            htxt = head.read_text(encoding='utf-8').strip()
            if htxt.startswith('ref:'):
                ref = htxt.split(None,1)[1].strip()
                ref_file = repo_root / '.git' / ref
                if ref_file.exists():
                    git_sha = ref_file.read_text(encoding='utf-8').strip()
                else:
                    # try packed-refs
                    packed = repo_root / '.git' / 'packed-refs'
                    if packed.exists():
                        for line in packed.read_text(encoding='utf-8').splitlines():
                            if line.startswith('#') or not line.strip():
                                continue
                            parts = line.split()
                            if len(parts) == 2 and parts[1] == ref:
                                git_sha = parts[0]
                                break
            else:
                # HEAD contains SHA directly
                git_sha = htxt
        # try to get last commit author/message from logs if available
        logs = repo_root / '.git' / 'logs' / 'HEAD'
        if logs.exists():
            try:
                last = logs.read_text(encoding='utf-8').strip().splitlines()[-1]
                # format: <oldsha> <newsha> <author>\t<message>
                parts = last.split('\t')
                msg = parts[1] if len(parts) > 1 else ''
                pre = parts[0].split()
                # pre contains oldsha newsha and author+timestamp
                oldsha = pre[0] if len(pre) > 0 else None
                newsha = pre[1] if len(pre) > 1 else None
                author = ' '.join(pre[2:]) if len(pre) > 2 else None
                git_last = { 'sha': newsha or git_sha, 'author': author, 'message': msg }
            except Exception:
                git_last = None
    except Exception:
        git_sha = None

    # include new fields in explanations
    explanations['counts.translation_suggestions_applied'] = 'Number of translation suggestions that have been applied'
    explanations['i18n_stats'] = 'Per-language i18n JSON file size and number of keys'
    explanations['git_sha'] = 'Current commit SHA read from .git (if available)'

    # TDLib status: attempt to inspect tdlib_router module for client and ws state
    tdlib_status = { 'available': False }
    try:
        import importlib
        tdmod = importlib.import_module('python_api.app.tdlib_router')
        tdlib_status['available'] = True
        _td = getattr(tdmod, '_td_client', None)
        tdlib_status['client_present'] = bool(_td)
        if _td is not None:
            try:
                tdlib_status['client_type'] = type(_td).__name__
            except Exception:
                tdlib_status['client_type'] = None
            try:
                tdlib_status['client_running'] = bool(getattr(_td, '_running', False))
            except Exception:
                tdlib_status['client_running'] = None
        # websocket manager active connections
        try:
            ws_mgr = getattr(tdmod, 'ws_mgr', None)
            tdlib_status['ws_connections'] = len(getattr(ws_mgr, 'active', [])) if ws_mgr is not None else 0
        except Exception:
            tdlib_status['ws_connections'] = None
        # auth flow stored in redis (if present)
        try:
            auth_raw = r.get('tdlib:auth')
            if auth_raw:
                try:
                    auth_obj = json.loads(auth_raw)
                except Exception:
                    auth_obj = None
                if auth_obj:
                    masked = dict(auth_obj)
                    if 'code' in masked:
                        masked['code'] = '*****'
                    tdlib_status['auth'] = masked
                else:
                    tdlib_status['auth'] = None
            else:
                tdlib_status['auth'] = None
        except Exception:
            tdlib_status['auth'] = None
        # recent events count and last item
        try:
            ev_count = r.llen('tdlib:events')
            tdlib_status['events_count'] = ev_count
            last = r.lindex('tdlib:events', 0)
            if last:
                try:
                    if isinstance(last, bytes):
                        s = last.decode()
                    else:
                        s = last
                    tdlib_status['last_event'] = json.loads(s) if s and s[0] in '{["' else s
                except Exception:
                    tdlib_status['last_event'] = str(last)
            else:
                tdlib_status['last_event'] = None
        except Exception:
            tdlib_status['events_count'] = None
            tdlib_status['last_event'] = None
    except Exception:
        tdlib_status = { 'available': False }

    # Tor status: check common local ports (SOCKS5 9050, ControlPort 9051)
    tor_status = { 'socks_ok': False, 'control_ok': False }
    try:
        try:
            s = socket.create_connection(('127.0.0.1', 9050), timeout=1)
            s.close()
            tor_status['socks_ok'] = True
        except Exception:
            tor_status['socks_ok'] = False
        try:
            s2 = socket.create_connection(('127.0.0.1', 9051), timeout=1)
            s2.close()
            tor_status['control_ok'] = True
        except Exception:
            tor_status['control_ok'] = False
    except Exception:
        tor_status = { 'socks_ok': False, 'control_ok': False }

    return {
        'status': 'ok',
        'time': now,
        'uptime': uptime,
        'redis': redis_status,
        'counts': counts,
        'api_info': api_info,
        'supported_endpoints': supported_endpoints,
        'pages': pages,
        'i18n_stats': i18n_stats,
        'git_sha': git_sha,
        'git_last': git_last,
        'processes': [ process_status(n) for n in PROCESS_DEFS.keys() ],
        'tdlib': tdlib_status,
        'explanations': explanations
    }


@app.get('/status/mock')
def status_mock():
    """Development mock for the status page. Returns example components and incidents."""
    now = int(time.time())
    sample = {
        'status': 'ok',
        'time': now,
        'uptime': 3600,
        'redis': { 'ok': True, 'connected_clients': 3, 'used_memory_human': '1.2M' },
        'counts': { 'messages': 123, 'devices': 2, 'users': 5 },
        'api_info': { 'web_api_key_set': bool(WEB_API_KEY), 'bot_token_set': bool(BOT_TOKEN) },
        'supported_endpoints': [ { 'path': '/status', 'method': 'GET', 'desc': 'Server status' } ],
        'pages': [ { 'href': 'index.html', 'label': 'Inicio' }, { 'href': 'chat.html', 'label': 'Chat' } ],
        'components': [
            { 'name': 'web', 'label': 'Web UI', 'status': 'operational' },
            { 'name': 'api', 'label': 'API', 'status': 'operational' },
            { 'name': 'redis', 'label': 'Redis', 'status': 'operational' },
            { 'name': 'tdlib', 'label': 'TDLib', 'status': 'degraded' }
        ],
        'incidents': [
            { 'title': 'TDLib connectivity issues', 'status': 'investigating', 'impact': 'minor', 'updates': [ { 'time': now, 'text': 'Investigando desconexiones intermitentes' } ] }
        ],
        'processes': [ process_status(n) for n in PROCESS_DEFS.keys() ],
        'tdlib': { 'available': TDLIB_AVAILABLE }
    }
    return sample


# Finally, mount the web/ static files so API routes are registered first
try:
    repo_root = Path(__file__).resolve().parents[2]
    web_dir = repo_root / 'web'
    if web_dir.exists():
        app.mount('/', StaticFiles(directory=str(web_dir), html=True), name='web')
except Exception:
    pass
