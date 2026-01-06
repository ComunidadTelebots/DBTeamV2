import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Importar routers
from .routes import anuncios, grupos, blog, auth, admin

app.include_router(anuncios.router)
app.include_router(grupos.router)
app.include_router(blog.router)
app.include_router(auth.router)
app.include_router(admin.router)

# Montar la carpeta web actual en la raíz


# Servir archivos estáticos desde /static y HTML desde la raíz
from fastapi.responses import FileResponse

emv = os.environ.get('EMV')
if emv:
    base_dir = os.path.abspath(os.path.join('C:\Users', emv, 'Documents', 'GitHub', 'DBTeamV2'))
else:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
web_dir = os.path.join(base_dir, 'web')
if os.path.exists(web_dir):
    static_dir = web_dir
    app.mount('/static', StaticFiles(directory=static_dir), name='static')

    @app.get("/{file_path}", response_class=FileResponse)
    async def serve_html(file_path: str):
        # Solo permitir archivos .html
        if not file_path.endswith('.html'):
            return FileResponse(os.path.join(web_dir, 'index.html'))
        full_path = os.path.join(web_dir, file_path)
        if os.path.exists(full_path):
            return FileResponse(full_path)
        return FileResponse(os.path.join(web_dir, 'index.html'))

    @app.get("/", response_class=FileResponse)
    async def root_html():
        return FileResponse(os.path.join(web_dir, 'index.html'))
