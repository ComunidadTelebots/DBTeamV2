# API pública para gestión de bots importados

## Autenticación
- Todas las rutas requieren sesión de usuario (login web o token de sesión).

## Endpoints principales

### 1. Importar/registrar bot externo
- `POST /bot/import`
  - Parámetros: `token`, `name`, `info` (opcional), `avatar` (opcional)
  - Respuesta: `{ ok, msg, bot }`

### 2. Listar bots del usuario
- `GET /bot/mybots`
  - Respuesta: `{ bots: [...] }`

### 3. Ver y gestionar grupos/chats del bot
- `GET /bot/stats?token=...`
  - Respuesta: `{ chats: [...] }`

### 4. Enviar mensaje a grupo/chat
- `POST /bot/send_message`
  - Parámetros: `token`, `group_id`, `text`
  - Respuesta: `{ ok, msg }`

### 5. Limitar recursos del bot
- `POST /bot/set_limits`
  - Parámetros: `token`, `limits` (ej: `{ max_chats, max_members, max_messages, rate_limit }`)
  - Respuesta: `{ ok, msg, limits }`

### 6. Consultar límites del bot
- `GET /bot/get_limits?token=...`
  - Respuesta: `{ limits }`

### 7. Limitar lectura de mensajes por grupo
- `POST /group/set_read_limit`
  - Parámetros: `group_id`, `read_limit`
  - Respuesta: `{ ok, msg, group_id, read_limit }`

### 8. Consultar límite de lectura de grupo
- `GET /group/get_read_limit?group_id=...`
  - Respuesta: `{ group_id, read_limit }`

### 9. Ver alertas de saturación en tiempo real
- `GET /group/rate_limit_alerts`
  - Respuesta: `{ alerts: [...] }`

### 10. Banear grupo/canal
- `POST /group/ban`
  - Parámetros: `group_id`
  - Respuesta: `{ ok, msg, group_id }`

### 11. Banear bot
- `POST /bot/ban`
  - Parámetros: `token`
  - Respuesta: `{ ok, msg }`

## Notas
- Los usuarios solo pueden gestionar sus propios bots.
- Los admins/owner pueden gestionar todos los bots y grupos.
- La API está pensada para integración web, paneles y automatización.

---
¿Quieres agregar ejemplos de uso, OpenAPI/Swagger, o instrucciones de despliegue?