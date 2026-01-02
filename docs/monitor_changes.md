# Monitor changes and references

Resumen breve
- Se añadieron collectors para Docker y Kubernetes y se extendió el endpoint `/monitor/service/status` para devolver información adicional (`docker`, `k8s`).
- Se actualizó la UI Owner para mostrar esas secciones: `web/owner.js`.

Principales ubicaciones de código
- Backend:
  - `python_api/ai_server.py` — funciones añadidas/movidas:
    - `_collect_docker_info()`  (módulo)
    - `_collect_k8s_info()`    (módulo)
    - `/monitor/service/status` ahora devuelve: `{'services': ..., 'docker': <lista|error>, 'k8s': <lista|error>}`

- Frontend:
  - `web/owner.js` — en la función `loadServiceControls()` ahora se renderizan bloques para "Containers Docker" y "Kubernetes Pods" usando los campos devueltos por el endpoint.

Notas sobre integridad del código
- No debería haberse eliminado lógica funcional: las implementaciones fueron reubicadas a nivel de módulo para evitar duplicados y errores de sintaxis (definiciones dentro de un `return` causaban `SyntaxError`).
- Si prefieres que las versiones antiguas del código permanezcan intactas, puedo:
  1) Restaurar o conservar copias en `python_api/ai_server.py.orig` con los fragmentos anteriores; o
  2) Insertar los bloques originales como comentarios referenciados cerca de las nuevas funciones (sin ejecutar).

Pruebas recomendadas
1. Instalar dependencias opcionales (recomendado):
```powershell
py -3 -m pip install psutil docker kubernetes
```
2. Reiniciar la API y comprobar el endpoint:
```powershell
py -3 python_api\ai_server.py --host 127.0.0.1 --port 8081
curl http://127.0.0.1:8081/monitor/service/status
```

Siguiente paso
- Dime si prefieres que añada copias de las versiones anteriores del código (opción 1 ó 2 arriba). No eliminaré ni sobrescribiré código sin tu confirmación; en su lugar crearé referencias o copias según prefieras.
