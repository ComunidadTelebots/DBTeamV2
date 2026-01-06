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

env = os.environ.get('ENV')
if env:
    # Use ENV as the project base directory. Expect ENV to be a full path.
    # If ENV is not an absolute path, treat it as a path relative to current working dir.
    if os.path.isabs(env):
        base_dir = os.path.abspath(env)
    else:
        base_dir = os.path.abspath(os.path.join(os.getcwd(), env))
else:
    # No ENV provided: prefer the executing user's environment (home directory)
    user_home = os.path.expanduser('~')
    # Common development locations to check under user's home
    cand1 = os.path.join(user_home, 'Documents', 'GitHub', 'DBTeamV2')
    cand2 = os.path.join(user_home, 'GitHub', 'DBTeamV2')
    cand3 = os.path.join(user_home, 'DBTeamV2')
    if os.path.exists(cand1):
        base_dir = os.path.abspath(cand1)
    elif os.path.exists(cand2):
        base_dir = os.path.abspath(cand2)
    elif os.path.exists(cand3):
        base_dir = os.path.abspath(cand3)
    else:
        # Fallback to repository-relative path (where the package lives)
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
