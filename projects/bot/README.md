Carpeta madre para el proyecto `bot`.

Contiene: código del bot Python en `python_bot/`, compat layers en `python_bot/legacy/` y plugins en `python_bot/plugins/`.

Arranque rápido:

- Crear entorno virtual e instalar dependencias:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r python_bot/requirements.txt
```
- Ejecutar bot (modo porting/scaffold):
```bash
py -c "from python_bot.bot import Bot; b=Bot(); b.start()"
```

Notas:
- Este repo contiene herramientas de migración; muchas funcionalidades siguen en desarrollo.
