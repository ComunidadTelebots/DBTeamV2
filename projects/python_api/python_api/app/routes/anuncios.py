
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
import json, os, time, random, glob

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
