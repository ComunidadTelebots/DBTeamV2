Carpeta madre para el backend Python (FastAPI).

Contiene: `python_api/` y utilidades relacionadas.

Arranque rápido (desarrollo):

- Crear entorno virtual e instalar dependencias:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r python_api/requirements.txt
```
- Ejecutar el servidor (desde la raíz del repo):
```bash
uvicorn projects/python_api/python_api.app.main:app --reload --port 5500
```

Revisa `projects/python_api/python_api/README_TDLIB.md` para instrucciones relacionadas con TDLib.
