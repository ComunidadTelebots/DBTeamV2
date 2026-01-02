Resumen de funciones del cliente web `web/telegram.js`

- `el(tag, cls)`
  - Crea y devuelve un elemento DOM; `tag` etiqueta HTML, `cls` clase opcional.

- `connect()`
  - Llama a `POST /tdlib/connect` (usa dummy por defecto) y arranca WebSocket + carga chats.

- `disconnect()`
  - Llama a `POST /tdlib/disconnect` y cierra la conexión WebSocket.

- `startWS()`
  - Abre WebSocket a `/tdlib/ws`, configura handlers `onopen`, `onmessage`, `onclose`.

- `loadChats()`
  - `GET /tdlib/chats`, renderiza la lista de chats en el panel izquierdo.

- `loadMessages()`
  - `GET /tdlib/messages`, carga e inserta el historial en el área de mensajes.

- `selectChat(c)`
  - Selecciona un chat, actualiza título y carga mensajes para ese chat.

- `sendMessage()`
  - Envía mensaje usando `/tdlib/send` o `/bot/send` dependiendo del selector `sendVia`.
  - Incluye `attachment_url` si hay un archivo subido en `window._lastUploadedUrl`.

- `uploadFile(file)`
  - Subida multipart a `POST /tdlib/upload`, retorna la URL devuelta por el servidor.

- `appendEvent(ev)`
  - Inserta un evento/mensaje en el DOM; renderiza imágenes inline si el adjunto parece imagen; añade botones Editar/Borrar.

- `onEditClick(node)`
  - Prompt para nuevo texto y llama a `POST /tdlib/message/edit` con `{id,text}`.

- `onDeleteClick(node)`
  - Confirma y llama a `POST /tdlib/message/delete` con `{id}`.

- `getAuthHeaders()`
  - Lee `td_api_key` de `localStorage` y devuelve headers con `Authorization: Bearer <key>` si existe.

- `showAttachmentPreview(file)`
  - Muestra preview local (imagen o nombre) y estado "Subiendo..." en el composer.

- `updateAttachmentPreviewWithUrl(url)`
  - Actualiza preview tras la subida, guarda `window._lastUploadedUrl` y añade enlace "Ver archivo".

- `clearAttachmentPreview()`
  - Limpia el preview y resetea `window._lastUploadedUrl`.

Event listeners y almacenamiento cliente:
- Guarda `td_api_key` en `localStorage` con el botón `saveKey`.
- Guarda token de Bot en `sessionStorage` o `localStorage` según `rememberBot`.
- `saveBotServer` envía `POST /devices/add` con `{id,token,name}` para guardar token en servidor.
- `attachFile` → al seleccionar archivo llama `showAttachmentPreview` → `uploadFile` → `updateAttachmentPreviewWithUrl`.

Notas:
- El cliente usa un cliente dummy por defecto (`/tdlib/connect` con `{dummy:true}`) para desarrollo.
- El archivo guarda la URL del último adjunto en `window._lastUploadedUrl` para incluirla en envíos.

Archivo generado: `web/telegram_functions.md`
