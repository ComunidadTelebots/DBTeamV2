
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
import json, os, time, random, glob
import requests

router = APIRouter()

# Endpoint para obtener anuncios pendientes
@router.get('/api/anuncios_pendientes')
def anuncios_pendientes():
    anuncios = []
    anuncios_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'anuncios'))
    if not os.path.exists(anuncios_dir):
        return JSONResponse({"ok": True, "anuncios": []})
    for f in glob.glob(os.path.join(anuncios_dir, '*.json')):
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                anuncio = json.load(fh)
            if anuncio.get('estado', 'pendiente') == 'pendiente':
                anuncios.append(anuncio)
        except Exception:
            continue
    return JSONResponse({"ok": True, "anuncios": anuncios})

# Página para que el receptor acepte/rechace el anuncio
@router.get('/anuncio_review/{anuncio_id}')
def review_anuncio(anuncio_id: str, r=None):
    raw = r.get(f'anuncio:{anuncio_id}')
    if not raw:
        return HTMLResponse('<h2>Anuncio no encontrado</h2>', status_code=404)
    anuncio = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    estado = anuncio.get('estado', 'pendiente')
    if estado != 'pendiente':
        return HTMLResponse('<h2>Anuncio ya revisado</h2>', status_code=400)
    html = f"""
    <html><head><title>Revisar anuncio</title></head><body style='font-family:sans-serif;background:#181f2a;color:#fff;text-align:center;padding:40px'>
    <h2>Revisión de anuncio</h2>
    <h3>{anuncio['titulo']}</h3>
    <p>{anuncio['contenido']}</p>
    <form method='post' action='/api/anuncio_review_action'>
      <input type='hidden' name='anuncio_id' value='{anuncio_id}' />
      <button name='accion' value='aceptar' style='background:#22c55e;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-size:1.1em;margin:10px 18px'>Aceptar</button>
      <button name='accion' value='rechazar' style='background:#ef4444;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-size:1.1em;margin:10px 18px'>Rechazar</button>
    </form>
    </body></html>
    """
    return HTMLResponse(html)

# Acción de aceptar/rechazar por receptor
@router.post('/api/anuncio_review_action')
def anuncio_review_action(anuncio_id: str = Form(...), accion: str = Form(...), r=None):
    raw = r.get(f'anuncio:{anuncio_id}')
    if not raw:
        return HTMLResponse('<h2>Anuncio no encontrado</h2>', status_code=404)
    anuncio = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    estado_actual = anuncio.get('estado', 'pendiente')
    if estado_actual not in ['pendiente', 'aceptado_receptor']:
        return HTMLResponse('<h2>Anuncio ya revisado</h2>', status_code=400)
    if accion == 'aceptar':
        anuncio['estado'] = 'aceptado_receptor'
        r.set(f'anuncio:{anuncio_id}', json.dumps(anuncio))
        return HTMLResponse('<h2>Anuncio aceptado</h2>')
    elif accion == 'rechazar':
        anuncio['estado'] = 'rechazado_receptor'
        r.set(f'anuncio:{anuncio_id}', json.dumps(anuncio))
        return HTMLResponse('<h2>Anuncio rechazado</h2>')
    else:
        return HTMLResponse('<h2>Acción no válida</h2>', status_code=400)


# Endpoint para enviar un nuevo anuncio (desde web)
@router.post('/api/anuncios')
def crear_anuncio(payload: dict, request: Request, r=None):
    titulo = (payload.get('titulo') or '').strip()
    contenido = (payload.get('contenido') or '').strip()
    usuario = payload.get('usuario') or {}
    if not titulo or not contenido:
        raise HTTPException(status_code=400, detail='Título y contenido requeridos')
    anuncios_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'anuncios'))
    os.makedirs(anuncios_dir, exist_ok=True)
    aid = str(int(time.time()*1000)) + str(random.randint(100, 999))
    anuncio = {
        'id': aid,
        'titulo': titulo,
        'contenido': contenido,
        'usuario': usuario,
        'estado': 'pendiente',
        'created_at': int(time.time())
    }
    fpath = os.path.join(anuncios_dir, f'{aid}.json')
    try:
        with open(fpath, 'w', encoding='utf-8') as fh:
            json.dump(anuncio, fh, ensure_ascii=False, indent=2)
        if r is not None:
            try:
                r.set(f'anuncio:{aid}', json.dumps(anuncio))
            except Exception:
                pass
    except Exception as e:
        raise HTTPException(status_code=500, detail='No se pudo guardar el anuncio')
    return JSONResponse({'ok': True, 'id': aid, 'msg': 'Anuncio enviado para revisión'})


# Aprobar (publicar) anuncio por índice según lista de pendientes
@router.post('/api/anuncios_aprobar')
def aprobar_anuncio(payload: dict, request: Request, r=None, is_owner_request=None, is_admin_request=None):
    if not (is_owner_request(request) or is_admin_request(request)):
        raise HTTPException(status_code=403, detail='No autorizado')
    idx = payload.get('idx')
    if idx is None:
        raise HTTPException(status_code=400, detail='Índice requerido')
    anuncios_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'anuncios'))
    files = glob.glob(os.path.join(anuncios_dir, '*.json'))
    pendientes = []
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                a = json.load(fh)
            if a.get('estado', 'pendiente') == 'pendiente':
                pendientes.append((f, a))
        except Exception:
            continue
    if idx < 0 or idx >= len(pendientes):
        raise HTTPException(status_code=400, detail='Índice fuera de rango')
    fpath, anuncio = pendientes[idx]
    anuncio['estado'] = 'publicado'
    anuncio['published_at'] = int(time.time())
    try:
        with open(fpath, 'w', encoding='utf-8') as fh:
            json.dump(anuncio, fh, ensure_ascii=False, indent=2)
        if r is not None:
            try:
                aid = anuncio.get('id')
                if aid:
                    r.set(f'anuncio:{aid}', json.dumps(anuncio))
            except Exception:
                pass
    except Exception:
        raise HTTPException(status_code=500, detail='No se pudo publicar el anuncio')
    return {'ok': True, 'msg': 'Anuncio publicado'}


# Rechazar anuncio por índice
@router.post('/api/anuncios_rechazar')
def rechazar_anuncio(payload: dict, request: Request, r=None, is_owner_request=None, is_admin_request=None):
    if not (is_owner_request(request) or is_admin_request(request)):
        raise HTTPException(status_code=403, detail='No autorizado')
    idx = payload.get('idx')
    if idx is None:
        raise HTTPException(status_code=400, detail='Índice requerido')
    anuncios_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'anuncios'))
    files = glob.glob(os.path.join(anuncios_dir, '*.json'))
    pendientes = []
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                a = json.load(fh)
            if a.get('estado', 'pendiente') == 'pendiente':
                pendientes.append((f, a))
        except Exception:
            continue
    if idx < 0 or idx >= len(pendientes):
        raise HTTPException(status_code=400, detail='Índice fuera de rango')
    fpath, anuncio = pendientes[idx]
    anuncio['estado'] = 'rechazado_moderador'
    anuncio['rejected_at'] = int(time.time())
    try:
        with open(fpath, 'w', encoding='utf-8') as fh:
            json.dump(anuncio, fh, ensure_ascii=False, indent=2)
        if r is not None:
            try:
                aid = anuncio.get('id')
                if aid:
                    r.set(f'anuncio:{aid}', json.dumps(anuncio))
            except Exception:
                pass
    except Exception:
        raise HTTPException(status_code=500, detail='No se pudo rechazar el anuncio')
    return {'ok': True, 'msg': 'Anuncio rechazado'}


# Listar anuncios publicados
@router.get('/api/anuncios_publicados')
def anuncios_publicados():
    anuncios = []
    anuncios_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'anuncios'))
    if not os.path.exists(anuncios_dir):
        return JSONResponse({"ok": True, "anuncios": []})
    for f in glob.glob(os.path.join(anuncios_dir, '*.json')):
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                anuncio = json.load(fh)
            if anuncio.get('estado') == 'publicado':
                anuncios.append(anuncio)
        except Exception:
            continue
    return JSONResponse({"ok": True, "anuncios": anuncios})


# Endpoint para generar anuncio vía IA (proxy al AI server local)
@router.post('/api/ia_anuncio')
def ia_anuncio(payload: dict):
    prompt = (payload.get('prompt') or '').strip()
    if not prompt:
        raise HTTPException(status_code=400, detail='Prompt requerido')
    try:
        resp = requests.post('http://127.0.0.1:8081/ai/gpt2', json={'prompt': prompt}, timeout=15)
        if resp.status_code != 200:
            return JSONResponse({'ok': False, 'error': 'AI server error'}, status_code=502)
        data = resp.json()
        text = data.get('text') or data.get('result') or ''
        return JSONResponse({'ok': True, 'anuncio': text})
    except Exception:
        return JSONResponse({'ok': False, 'error': 'No se pudo contactar al servidor IA'}, status_code=502)
