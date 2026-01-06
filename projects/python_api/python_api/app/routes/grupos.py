from fastapi import APIRouter, Request, HTTPException
import json

router = APIRouter()

# Listar grupos anunciantes
@router.get('/api/grupos_anunciantes')
def listar_grupos_anunciantes(request: Request, r=None, is_owner_request=None, is_admin_request=None):
    if not (is_owner_request(request) or is_admin_request(request)):
        raise HTTPException(status_code=403, detail='No autorizado')
    grupos = []
    for raw in r.lrange('grupos_anunciantes', 0, -1) or []:
        try:
            grupos.append(json.loads(raw.decode() if isinstance(raw, bytes) else raw))
        except Exception:
            continue
    return {'ok': True, 'grupos': grupos}

# Agregar grupo anunciante
@router.post('/api/grupos_anunciantes')
def agregar_grupo_anunciante(payload: dict, request: Request, r=None, is_owner_request=None, is_admin_request=None):
    if not (is_owner_request(request) or is_admin_request(request)):
        raise HTTPException(status_code=403, detail='No autorizado')
    gid = (payload.get('id') or '').strip()
    nombre = (payload.get('nombre') or '').strip()
    if not gid:
        raise HTTPException(status_code=400, detail='ID requerido')
    grupo = {'id': gid, 'nombre': nombre}
    grupos = r.lrange('grupos_anunciantes', 0, -1) or []
    for raw in grupos:
        try:
            g = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
            if g.get('id') == gid:
                raise HTTPException(status_code=400, detail='Grupo ya existe')
        except Exception:
            continue
    r.rpush('grupos_anunciantes', json.dumps(grupo))
    return {'ok': True, 'msg': 'Grupo añadido'}

# Eliminar grupo anunciante
@router.delete('/api/grupos_anunciantes')
def eliminar_grupo_anunciante(payload: dict, request: Request, r=None, is_owner_request=None, is_admin_request=None):
    if not (is_owner_request(request) or is_admin_request(request)):
        raise HTTPException(status_code=403, detail='No autorizado')
    idx = payload.get('idx')
    grupos = r.lrange('grupos_anunciantes', 0, -1) or []
    if idx is None or idx < 0 or idx >= len(grupos):
        raise HTTPException(status_code=400, detail='Índice inválido')
    r.lset('grupos_anunciantes', idx, '__DELETED__')
    r.lrem('grupos_anunciantes', 0, '__DELETED__')
    return {'ok': True, 'msg': 'Grupo eliminado'}