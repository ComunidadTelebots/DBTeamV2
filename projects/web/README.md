Carpeta madre para la interfaz web y recursos estáticos.

Contiene: `web/` con HTML/CSS/JS e i18n.

Arranque rápido:

- Servir estáticos (por ejemplo con `python -m http.server` desde `projects/web/web`):
```bash
cd projects/web/web
python -m http.server 8000
```

El frontend incluye la integración con el Telegram Login Widget y un scaffold de UI en `telegram.html`.
