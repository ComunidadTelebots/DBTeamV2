# Instalación reducida para Raspberry Pi

Este archivo describe cómo desplegar una versión reducida del proyecto en Raspberry Pi, con Portainer para gestión de contenedores.

1) Requisitos
- Raspberry Pi con Docker instalado (preferible Raspberry Pi OS 64-bit para `arm64`).
- Acceso a la terminal con privilegios `sudo`.

2) Uso rápido (desde la raíz del repositorio)

```bash
# Ejecutar el instalador y elegir la opción Raspberry Pi
./install.sh
```

El instalador detectará Docker y levantará Portainer usando `docker-compose.rpi.yml`.

Ahora el instalador ofrece selección interactiva de servicios cuando eliges la opción Raspberry Pi.
Al ejecutarlo te preguntará por cada servicio:
- Portainer (gestión de contenedores)
- Redis (contenedor)
- Bot (instalación local en un entorno virtual Python)
- Web (instalación local con `npm`)
- API Python (instalación local en venv)

Ahora la opción de `Web` es más flexible: podrás elegir entre:
- **Web ligera**: instala dependencias y ejecuta el `build` (o `build:light` si está disponible) para generar artefactos estáticos optimizados.
- **Web completa**: instala todas las dependencias (`npm install`) y deja la aplicación lista para ejecutarse con `npm start` según la configuración del proyecto.

El instalador preguntará `n` (ninguna), `l` (ligera) o `f` (completa) cuando selecciones la instalación para Raspberry Pi.

Dependiendo de tus selecciones el instalador:
- arrancará Portainer con `docker compose -f docker-compose.rpi.yml up -d`
- arrancará Redis como contenedor `redis:alpine`
- instalará el `bot`, `web` o `python_api` localmente si existen las rutas correspondientes


3) Si prefieres hacerlo manualmente

```bash
# Levantar Portainer
sudo docker compose -f docker-compose.rpi.yml up -d

# Accede a Portainer en http://<IP_de_tu_RPi>:9000
```

4) Notas
- El `docker-compose.rpi.yml` contiene sólo Portainer y un volumen para datos. Añade más servicios adaptados a ARM si quieres ejecutar el bot o la API en contenedores.
- Para imágenes no multi-arch, construye imágenes en la Raspberry o utiliza `docker buildx` para crear multiplataforma.

8) Web ligera incluida

Se incluye una versión estática mínima en `web_light/`. Si eliges la opción "Web ligera" en el instalador y no hay un `package.json` con `build` configurado, el instalador copiará automáticamente los archivos de `web_light/` a `web/build/`, que es la ruta usada por `docker-compose.rpi.services.yml` (nginx) para servir la web estática.

Si quieres probar manualmente:

```bash
# Copiar manualmente el contenido ligero a web/build
mkdir -p web/build
cp -r web_light/* web/build/

# Levantar nginx para servir la web ligera (en la Raspberry):
sudo docker compose -f docker-compose.rpi.services.yml up -d --build web
```

9) Selección modular de páginas (web ligera)

En la web ligera puedes seleccionar los módulos (páginas) que quieras incluir para ahorrar espacio. Módulos disponibles:
- `index` — página principal
- `login` — login/registro
- `chat` — interfaz de chat
- `status` — página de estado
- `monitor` — páginas de monitorización
- `translations` — traducciones/traducciones UI
- `links` — enlaces y widgets
- `tutorial` — tutorial/página de ayuda
 - `streaming` / `streamer` — interfaz de streaming (`streamer.html`, `streamer.js`, `streamer.css`)
 - `torrents` — páginas relacionadas con torrents (`torrents_user.html`, `torrents_user.js`, y cualquier archivo con 'torrent' en el nombre)
 - `media` — biblioteca multimedia (`media.html`, `media.js`)

Ejemplo: al ejecutar el instalador y elegir Web ligera, responde la petición de módulos con:

```
index status login
```

El instalador llamará a `./scripts/assemble_web_light.sh index status login` y generará `web/build/` con sólo esos archivos y activos necesarios.

Presets disponibles (más fácil y rápido):
- `minimo`: `index status login`
- `admin`: `index status owner bots bot_control admin_bots` (si existen)
- `full_light`: incluye la mayoría de módulos (`index login chat status monitor translations links tutorial anuncios`)
 - `full_light`: incluye la mayoría de módulos (`index login chat status monitor translations links tutorial anuncios`) y además `owner`, `bots`, `bot_control`, `admin_bots`, `media`, `torrents`, `streaming`.
- `traductores`: sólo módulos de traducciones
- `anuncios`: incluye páginas de anuncios (`anuncios.html`, `moderar_anuncios.html`)
 - `media`: sólo los módulos de multimedia (`media`, `media.js`, etc.)
 - `torrents`: módulos relacionados con torrents (`torrents_user.html`, `torrents_user.js`, etc.)

Nota: el módulo `links` ahora incluye automáticamente todos los archivos del sitio que contengan "link" o "links" en su nombre (HTML, JS, CSS), por lo que no es necesario listarlos manualmente.

En el instalador puedes elegir `preset` o `manual` cuando configures la Web ligera.

9) Gestión posterior — añadir/eliminar módulos y servicios

Después de la instalación, puedes añadir o eliminar módulos de la `web ligera` con:

```bash
# Listar módulos actuales
./scripts/manage_web_light.sh list

# Añadir módulos
./scripts/manage_web_light.sh add chat links

# Eliminar módulos
./scripts/manage_web_light.sh remove chat
```

Para gestionar servicios Docker (iniciar, parar, eliminar contenedores individuales) usa:

```bash
# Listar servicios definidos
./scripts/manage_services_rpi.sh list

# Iniciar servicios concretos
./scripts/manage_services_rpi.sh start redis web

# Parar servicios
./scripts/manage_services_rpi.sh stop redis

# Eliminar contenedores de servicios
./scripts/manage_services_rpi.sh remove redis
```

Estos scripts permiten ajustar qué módulos/servicios se descargan o se mantienen sin volver a ejecutar todo el instalador.


5) Despliegue con servicios completos (compose)

Si quieres desplegar Portainer + web estática + Redis + bot + API en la Raspberry Pi usando `docker-compose.rpi.services.yml`:

```bash
# Construir localmente (en la Raspberry) y arrancar:
sudo docker compose -f docker-compose.rpi.services.yml up -d --build

# O, si has publicado las imágenes en Docker Hub, simplemente arrancar:
sudo docker compose -f docker-compose.rpi.services.yml up -d
```

6) Construir y publicar imágenes multi-arch (Docker Hub)

Pre-requisitos:
- Tener `docker` y `docker buildx` instalados y configurados.
- Autenticarse en Docker Hub: `docker login`.

Usa el script `scripts/buildx_build.sh`. Ejemplos:

- Para construir y publicar a Docker Hub (reemplaza `myuser` por tu namespace):

```bash
DOCKER_NAMESPACE=myuser DOCKER_PUSH=1 ./scripts/buildx_build.sh
```

- Para construir y cargar localmente (no publicar):

```bash
DOCKER_NAMESPACE=myuser ./scripts/buildx_build.sh
```

Notas:
- El script genera las imágenes `DOCKER_NAMESPACE/bot:latest` y `DOCKER_NAMESPACE/api:latest`.
- Después de publicar, actualiza `image:` en `docker-compose.rpi.services.yml` para apuntar a tus imágenes si es necesario.

7) Recomendaciones y consideraciones

- Si tu Raspberry Pi es `arm64`, prefieres usar `linux/arm64` en `PLATFORMS` y ejecutar las imágenes `arm64` para mejor rendimiento.
- Construir multi-arch y publicar requiere acceso a una máquina con capacidad para `buildx` (puede hacerse en CI). Construir directamente en la Raspberry está bien para pruebas, pero puede ser lento.
- Revisa y ajusta variables de entorno, puertos y volúmenes en `docker-compose.rpi.services.yml` según tu entorno.

8) Presets globales de instalación (RPi)

El instalador ofrece presets que configuran combinaciones de servicios para facilitar despliegues en Raspberry Pi:

- `minimal`: sólo `Portainer` y `Web (ligera)` — ideal para gestión mínima y servir contenidos estáticos.
- `server`: `Portainer`, `Redis`, `Web (completa)` — orientado a servidor de producción ligero.
- `full`: `Portainer`, `Redis`, `Bot` (local), `Web (completa)`, `API` — instala todo lo disponible.
- `dev`: `Redis`, `Bot` (local), `Web (completa)`, `API` — entorno para desarrollo en la Raspberry.
- `headless`: `Redis`, `API` — para entornos sin frontend.

Al ejecutar la sección Raspberry Pi del instalador puedes elegir un preset y el instalador aplicará automáticamente la configuración correspondiente. Si no eliges preset, se solicitará la selección manual de cada servicio.

