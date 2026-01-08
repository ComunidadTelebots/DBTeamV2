**Resumen**: Documentación de la funcionalidad de moderación y protección contra abuso integrada en la aplicación.

- **Componentes principales**:
  - **Clasificador de comportamiento**: `projects/bot/python_bot/moderation/classifier.py` — regla-based, acumula puntos por usuario, sugiere acciones (`warn`, `mute`, `ban`) y publica en `moderation:actions` y `web:notifications`.
  - **Protección de abuso (web/API)**: `python_api/abuse_protection.py` — cuenta peticiones por IP, soporta bloqueo por IP/país/región/ciudad/medio, auto-block y escalado a admin.
  - **Servidor web / endpoints**: `python_api/stream_server.py` — expone endpoints para revisar y aplicar sugerencias, y endpoints admin de abuse.
  - **Alertas**: `python_api/alerts.py` — envía notificaciones por Telegram y/o e-mail cuando hay escalaciones o bloqueos automáticos.
  - **Frontend**: `projects/python_api/web/app.js` — burbuja lateral que consume `/web/notifications` y marca notificaciones como leídas.

**Claves Redis y colas**
- `mod:points:<group_id>:<user_id>`: lista JSON de [ts,points] por usuario (ventana deslizante).
- `moderation:actions`: lista FIFO de sugerencias (JSON) para revisión por admins.
- `moderation:applied`: lista de acciones aplicadas (histórico).
- `web:notifications`: lista de notificaciones para UI (bounded list).
- `abuse:blacklist:ip`, `abuse:blacklist:country`, `abuse:blacklist:region`, `abuse:blacklist:city`, `abuse:blacklist:medium`: sets con elementos bloqueados.

**Variables de entorno importantes**
- `REDIS_URL` — URL de Redis (por defecto `redis://127.0.0.1:6379/0`).
- `ADMIN_TOKEN` — token simple HTTP header (`X-ADMIN-TOKEN`) para proteger endpoints admin.
- `ABUSE_IP_THRESHOLD` — número de peticiones en ventana que dispara la acción (default 100). Para pruebas reduzca a 3–10.
- `ABUSE_WINDOW` — ventana en segundos para contar peticiones (default 60).
- `ABUSE_BLOCK_TTL` — TTL por defecto para bloqueo de IPs (default 3600).
- `ABUSE_COUNTRY_THRESHOLD` — número de IPs bloqueadas en un país para considerar bloqueo por país (default 10).
- `ABUSE_AUTO_BLOCK` — `1`/`0` auto bloquear IP/país cuando se alcanza el umbral (default `1`).
- `ABUSE_AUTO_ESCALATE` — `1`/`0` publicar sugerencia y notificación para admin en lugar de bloquear automáticamente (default `1`).
- `GEOIP_DB` — (opcional) ruta local al MaxMind DB para resolución geoip (ej. GeoLite2-City.mmdb).
- Alertas:
  - `BOT_TOKEN` — token del bot de Telegram para enviar alertas.
  - `ADMIN_TELEGRAM_CHAT` — chat id donde enviar alertas Telegram.
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `ADMIN_EMAIL` — si desea notificaciones por e-mail.

**Endpoints (resumen y uso)**
- GET `/web/notifications` — devuelve últimas notificaciones (JSON). Si `ADMIN_TOKEN` está configurado requiere header `X-ADMIN-TOKEN`.
- POST `/web/notifications/mark_read` — body `{ "raws": ["<raw-json-string>"] }` para eliminar notificaciones concretas (requiere token si está configurado).
- GET `/admin/moderation/actions` — listar sugerencias (requires `X-ADMIN-TOKEN`).
- POST `/admin/moderation/apply` — aplicar sugerencia: body `{ "index": <int>, "action": "ban|mute|warn|..." }` (requires `X-ADMIN-TOKEN`).
- GET `/admin/abuse/blocked` — listar IPs/países/regiones/ciudades/medios bloqueados (requires `X-ADMIN-TOKEN`).
- POST `/admin/abuse/block` — body con cualquiera de `{ "ip":"1.2.3.4" }`, `{ "country":"ES" }`, `{ "region":"..." }`, `{ "city":"..." }`, `{ "medium":"telegram" }` para bloquear manualmente (requires `X-ADMIN-TOKEN`).
- POST `/admin/abuse/unblock` — similar a block para deshacer bloqueos (requires `X-ADMIN-TOKEN`).

**Cómo funciona la IA/autonomía**
- `abuse_protection.record_request(ip, meta)` se invoca desde `stream_server` en cada petición web. Si `ABUSE_AUTO_BLOCK=1` la IP puede bloquearse automáticamente cuando supere `ABUSE_IP_THRESHOLD`. Si `ABUSE_AUTO_BLOCK=0` y `ABUSE_AUTO_ESCALATE=1` la IA sólo publicará una sugerencia en `moderation:actions` y una notificación en `web:notifications` para que un admin/aplicación la revise.
- Cuando se bloquea automáticamente o se escala, se publican notificaciones y entradas en `moderation:actions`; `python_api/alerts.py` intentará notificar al admin vía Telegram y/o e-mail.

**Frontend**
- Archivo: `projects/python_api/web/app.js` — la burbuja lateral ya contiene `renderNotifications()` que consulta `/web/notifications`. Para que el frontend use `ADMIN_TOKEN` (si establecido) agregue en la plantilla HTML:
  ```html
  <script>window.ADMIN_TOKEN = 'mi-token-secreto';</script>
  <script src="/static/app.js"></script>
  ```
  La UI marcará las notificaciones mostradas como leídas llamando a `/web/notifications/mark_read`.

**Pruebas**
- Unit tests existentes:
  - `python_api/tests/test_abuse_protection.py` — tests para conteo y auto-block con `FakeRedis`.
  - `python_api/tests/test_stream_server.py` — tests para endpoints admin con `FakeRedis` y `Flask` test client.
- Ejecutar tests:
  ```powershell
  python -m unittest -v python_api.tests.test_abuse_protection python_api.tests.test_stream_server
  ```

**Despliegue y pruebas manuales rápidas**
1. Levantar Redis en local o usar la URL en `REDIS_URL`.
2. Exportar variables (ejemplo PowerShell):
   ```powershell
   $env:REDIS_URL = 'redis://127.0.0.1:6379/0'
   $env:ADMIN_TOKEN = 'mi-token'
   $env:ABUSE_IP_THRESHOLD = '10'
   $env:ABUSE_WINDOW = '60'
   $env:ABUSE_AUTO_BLOCK = '1'
   $env:BOT_TOKEN = '<telegram-bot-token>'
   $env:ADMIN_TELEGRAM_CHAT = '<chat-id>'
   ```
3. Ejecutar servidor:
   ```powershell
   python python_api/stream_server.py
   ```
4. Simular ataques (curl con `X-Forwarded-For`):
   ```bash
   for i in {1..12}; do curl -s -H "X-Forwarded-For: 1.2.3.4" http://localhost:5000/ >/dev/null; done
   ```
5. Verificar colas y bloqueos via endpoints admin (usar header `X-ADMIN-TOKEN: mi-token`).

**Seguridad y recomendaciones**
- Proteja `ADMIN_TOKEN` y considérelo sólo para entornos internos; preferible integrar autenticación de sesión o OAuth en producción.
- Ejecute `stream_server` detrás de un reverse-proxy (nginx) que establezca `X-Forwarded-For` correctamente.
- Mantenga un TTL razonable para bloqueos temporales y revise los logs antes de bloquear países completos.
- Use `GEOIP_DB` (MaxMind) actualizado para resolución de ciudad/región.

Si quieres, genero un README corto en la raíz del `python_api` o agrego ejemplos de `docker-compose` para desplegar el executor y el servicio web con estas variables.
