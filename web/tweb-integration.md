Integración de tweb con el diseño DBTeam

Pasos recomendados:

1) Clonar tweb en el directorio `web/vendor/tweb`:

   cd web
   git clone --depth 1 https://github.com/morethanwords/tweb vendor/tweb

2) Incluir los assets de tweb (HTML/CSS/JS) en tu server estático o copiar los archivos que necesites a `web/`.

3) Para aplicar el tema DBTeam, carga `tweb-theme.css` después del CSS principal de tweb en las páginas relevantes, por ejemplo:

   <link rel="stylesheet" href="/vendor/tweb/dist/tweb.css">
   <link rel="stylesheet" href="/tweb-theme.css">

4) Mapeo y overrides comunes:
   - Variables: sobrescribe colores, tipografía y radios en `tweb-theme.css`.
   - Componentes: si tweb usa clases específicas, añade reglas en `tweb-theme.css` para adaptarlas.

5) Integración JS:
   - Si quieres reusar el frontend tweb, adapta sus llamadas de red a los endpoints del servidor (`/tdlib/*`, `/bot/send`, `/tdlib/upload`).
   - Usa `web/telegram.js` como referencia para la API y WebSocket.

6) Pruebas:
   - Arranca uvicorn y Redis, abre `http://localhost:5500/vendor/tweb/...` o la ruta que uses.
   - Ajusta variables en `tweb-theme.css` hasta que la apariencia encaje con `shared.css`.

Si me autorizas a clonar y adaptar los archivos aquí (no puedo descargar desde Internet directamente), puedo:
- crear la estructura `web/vendor/tweb` vacía y añadir scripts de integración,
- generar ejemplos de overrides para componentes concretos que me indiques (bubbles, lista de chats, composer),
- o guiarte paso a paso para que ejecutes el `git clone` en tu máquina y luego me indiques los archivos para ajustar.
