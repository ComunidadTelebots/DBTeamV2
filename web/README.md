Prueba de concepto: Interfaz web para llamar a modelos de IA

Instrucciones rápidas:

- Servir los archivos estáticos (por ejemplo, desde la carpeta `web`) con un servidor simple:

```bash
# desde la carpeta del repo
python -m http.server 8001 --directory web
# o con PowerShell (Windows):
# Start-Process -NoNewWindow -FilePath python -ArgumentList '-m http.server 8001 --directory web'
```

- Abrir `http://localhost:8001` en el navegador.

- Por defecto el formulario apunta a `http://127.0.0.1:8000/generate`. Debes tener un servidor que acepte POST JSON y responda con texto o JSON. Si usas `data/ai_config.lua` en modo `local`, ajusta ese servicio para exponer un endpoint compatible.

Notas y recomendaciones:
- El navegador requiere que el endpoint permita CORS para llamadas directas. Si no quieres configurar CORS, corre un pequeño proxy en el mismo origen que la página o usa `curl`/servidor intermedio.
- El PoC no está autenticado; no exponerlo a redes públicas sin protección.
