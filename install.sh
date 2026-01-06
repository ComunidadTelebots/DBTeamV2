#!/bin/bash
# DBTeamV2 General Install Script
# Instala y configura todos los componentes: bot, web, API, dependencias extra

set -e

# Utilidades de verificación de hash
compute_sha256() {
    local file="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$file" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$file" | awk '{print $1}'
    else
        echo ""
    fi
}

verify_file_hash() {
    local file="$1" expected="$2"
    if [ -z "$expected" ]; then
        return 1
    fi
    local actual
    actual=$(compute_sha256 "$file")
    if [ -z "$actual" ]; then
        echo "[warn] No se dispone de sha256sum/shasum para verificar $file"
        return 2
    fi
    if [ "$actual" != "$expected" ]; then
        echo "[error] Hash SHA256 no coincide para $file"
        echo "  esperado: $expected"
        echo "  obtenido: $actual"
        return 1
    fi
    echo "[ok] Hash SHA256 verificado para $file"
    return 0
}

# Verificar firma GPG del archivo checksums.txt (checksums.txt.sig)
verify_checksums_signature() {
    # devuelve: 0 = ok, 1 = firma inválida / no verificada, 2 = gpg no disponible
    if ! command -v gpg >/dev/null 2>&1; then
        echo "[warn] gpg no está instalado; no se puede verificar la firma GPG de checksums.txt"
        return 2
    fi
    local checksums_file="$(pwd)/checksums.txt"
    local sig_file="$(pwd)/checksums.txt.sig"
    if [ ! -f "$checksums_file" ] || [ ! -f "$sig_file" ]; then
        echo "[warn] Falta checksums.txt o checksums.txt.sig; no se puede verificar firma"
        return 1
    fi
    # Importar clave pública local si existe
    if [ -f "$(pwd)/keys/public.key" ]; then
        gpg --import "$(pwd)/keys/public.key" >/dev/null 2>&1 || true
    fi
    # Si el usuario proporciona URL de clave pública, descargarla e importarla
    if [ -n "$GPG_PUBKEY_URL" ]; then
        tmpk="/tmp/repo_public_key.gpg"
        curl -fsSL "$GPG_PUBKEY_URL" -o "$tmpk" || true
        if [ -f "$tmpk" ]; then
            gpg --import "$tmpk" >/dev/null 2>&1 || true
        fi
    fi
    if gpg --verify "$sig_file" "$checksums_file" >/dev/null 2>&1; then
        echo "[ok] Firma GPG verificada para checksums.txt"
        return 0
    else
        echo "[error] Firma GPG inválida o no verificada para checksums.txt"
        return 1
    fi
}

# Descargar un archivo y verificar SHA256 (si se proporciona en checksums.txt o como argumento)
download_and_verify() {
    local url="$1" dest="$2" name="$3"
    if [ -z "$dest" ]; then dest="$(basename "$url")"; fi
    if [ -z "$name" ]; then name="$(basename "$dest")"; fi
    echo "Descargando $name desde $url..."
    curl -fsSL "$url" -o "$dest"
    # buscar hash esperado en checksums.txt (si existe y su firma GPG valida)
    local expected=""
    if [ -f "$(pwd)/checksums.txt" ]; then
        verify_checksums_signature >/dev/null 2>&1
        sig_ok=$?
        if [ "$sig_ok" -eq 0 ]; then
            expected=$(grep -E "^${name}[[:space:]]+" "$(pwd)/checksums.txt" | awk '{print $2}' || true)
        else
            echo "Aviso: checksums.txt no está firmada o la firma no se pudo verificar. No usaremos su contenido a menos que lo confirmes." 
            read -p "¿Deseas confiar en checksums.txt sin verificación GPG y usar su hash para $name? [y/N]: " trustc
            case "$trustc" in
                y|Y) expected=$(grep -E "^${name}[[:space:]]+" "$(pwd)/checksums.txt" | awk '{print $2}' || true) ;;
                *) expected="" ;;
            esac
        fi
    fi
    # si no está en checksums, noitamos al usuario para pedirlo opcionalmente
    if [ -z "$expected" ]; then
        read -p "No se encontró SHA256 para $name en checksums.txt. ¿Deseas introducirlo ahora para verificar? [y/N]: " vch
        case "$vch" in
            y|Y) read -p "Introduce SHA256 esperado para $name: " expected ;;
            *) expected="" ;;
        esac
    fi
    if [ -n "$expected" ]; then
        if ! verify_file_hash "$dest" "$expected"; then
            echo "Verificación fallida para $name"; return 1
        fi
    else
        echo "Aviso: no se verificó SHA256 para $name";
    fi
    return 0
}
# =====================================================
#
# RECOMENDACIONES DE BACKUP
#
# BUENAS PRÁCTICAS DE BACKUP Y RESTAURACIÓN
#
# AUTOMATIZACIÓN DE BACKUPS
#
# EJEMPLOS DE RESTAURACIÓN DE BACKUPS
#
# CIFRADO Y ALMACENAMIENTO EN LA NUBE
# - Protege tus backups cifrándolos antes de almacenarlos:
#     openssl enc -aes-256-cbc -salt -in backup_config_YYYY-MM-DD.tar.gz -out backup_config_YYYY-MM-DD.tar.gz.enc
# - Para descifrar:
#     openssl enc -d -aes-256-cbc -in backup_config_YYYY-MM-DD.tar.gz.enc -out backup_config_YYYY-MM-DD.tar.gz
# - Puedes subir los backups cifrados a servicios en la nube como Google Drive, Dropbox, S3, etc. usando rclone, aws-cli o herramientas similares.
# - Ejemplo con rclone:
#     rclone copy backup_config_YYYY-MM-DD.tar.gz.enc remote:DBTeamV2Backups
# - Mantén las claves de cifrado y acceso en un lugar seguro y separado de los backups.
# - Para restaurar archivos de configuración y .env:
#     tar xzf backup_config_YYYY-MM-DD.tar.gz -C /ruta/del/proyecto
# - Para restaurar un volumen Docker:
#     docker run --rm -v volumen:/data -v $(pwd):/backup busybox tar xzf /backup/volumen_backup_YYYY-MM-DD.tar.gz -C /
# - Para restaurar Redis:
#     Detén el servicio Redis, reemplaza dump.rdb y vuelve a iniciar Redis.
# - Para restaurar modelos o logs:
#     tar xzf models_backup_YYYY-MM-DD.tar.gz -C ./models
#     tar xzf logs_backup_YYYY-MM-DD.tar.gz -C ./logs
# - Revisa la documentación de cada servicio para restauraciones avanzadas o en producción.
# - Usa el script tools/backup.sh para realizar copias de seguridad automáticas de archivos clave, volúmenes Docker, modelos y logs.
# - Ejecútalo manualmente o programa su ejecución con cron:
#     0 3 * * * /ruta/a/tools/backup.sh /ruta/a/backups
# - Revisa el contenido de la carpeta de backups y verifica que los archivos se hayan creado correctamente.
# - Para restaurar, descomprime los archivos .tar.gz en sus ubicaciones originales y sigue la documentación específica de cada servicio.
# - Realiza copias de seguridad automáticas y manuales de:
#   - .env y archivos de configuración
#   - Bases de datos (ej: Redis, SQLite, PostgreSQL, etc.)
#   - Volúmenes y carpetas persistentes de Docker
#   - Archivos importantes en data/, models/, logs/ si contienen información relevante
# - Usa herramientas como rsync, tar, pg_dump, redis-cli save, o scripts personalizados para los backups.
# - Ejemplo para backup de .env y configuraciones:
#     tar czf backup_config_$(date +%F).tar.gz .env config/ deploy/ data/
# - Ejemplo para backup de Redis:
#     redis-cli save && cp /var/lib/redis/dump.rdb /ruta/backup/
# - Ejemplo para backup de volúmenes Docker:
#     docker run --rm -v volumen:/data -v $(pwd):/backup busybox tar czf /backup/volumen_backup.tar.gz /data
# - Almacena los backups en ubicaciones externas y seguras (otro servidor, nube, disco externo).
# - Verifica periódicamente que los backups se pueden restaurar correctamente.
# - Documenta el proceso de restauración y prueba la recuperación en entorno de pruebas.
# - Protege los backups con cifrado si contienen datos sensibles.
# - Elimina backups antiguos de forma segura y controlada.
# - Realiza copias de seguridad periódicas de los archivos .env, configuraciones y bases de datos.
# - Guarda los backups en ubicaciones seguras y fuera del servidor principal.
# - Si usas Docker, considera respaldar los volúmenes y datos persistentes.
# - Automatiza los backups si es posible y verifica que puedas restaurar correctamente.
# - Documenta el proceso de restauración para tu equipo o para ti mismo.
# - Mantén tu sistema y dependencias actualizadas para evitar vulnerabilidades.
# - Realiza copias de seguridad periódicas de tus datos y archivos de configuración.
# - Si usas el bot, web o API en producción, utiliza HTTPS y firewalls para proteger los servicios.
# - Revisa los logs y monitorea accesos sospechosos regularmente.
# ADVERTENCIAS DE SEGURIDAD
# =====================================================
# - Nunca compartas tu BOT_TOKEN ni WEB_API_SECRET con terceros.
# - Usa un WEB_API_SECRET largo y aleatorio para evitar accesos no autorizados.
# - Los IDs de usuario deben ser correctos; no pongas IDs de desconocidos como admin/owner.
# - El archivo .env contiene credenciales sensibles, protégelo y no lo subas a repositorios públicos.
# - Si usas Redis en producción, configura contraseña y acceso seguro.
# =====================================================
# Solicitar tokens y usuarios iniciales con explicaciones
echo "\n=== Configuración inicial de credenciales ==="
echo "Se crearán las variables necesarias en el archivo .env para el funcionamiento de todos los servicios."

echo "\nBOT_TOKEN: Token del bot de Telegram. Puedes obtenerlo desde @BotFather."
read -p "Introduce el BOT_TOKEN: " BOT_TOKEN

echo "\nWEB_API_SECRET: Secreto para proteger el acceso a la API web. Usa una cadena segura y privada."
read -p "Introduce el WEB_API_SECRET: " WEB_API_SECRET

echo "\nADMIN_USER: ID de usuario de Telegram que será el administrador inicial del sistema. Puedes obtener tu ID con @userinfobot."
read -p "Introduce el usuario administrador inicial (Telegram user ID): " ADMIN_USER

echo "\nOWNER_USER: ID de usuario de Telegram que será el propietario inicial del sistema. Suele ser el creador o responsable principal."
read -p "Introduce el usuario propietario inicial (Telegram user ID): " OWNER_USER

echo "\nREDIS_URL: URL de conexión a Redis para almacenamiento y caché. Si no sabes cuál poner, deja el valor por defecto."
read -p "Introduce la URL de Redis (por defecto: redis://127.0.0.1:6379/0): " REDIS_URL
REDIS_URL=${REDIS_URL:-redis://127.0.0.1:6379/0}

echo "\nGuardando credenciales en .env..."
cat > .env <<EOF
BOT_TOKEN=${BOT_TOKEN}
WEB_API_SECRET=${WEB_API_SECRET}
ADMIN_USER=${ADMIN_USER}
OWNER_USER=${OWNER_USER}
REDIS_URL=${REDIS_URL}
EOF
echo "\nArchivo .env creado correctamente. Puedes editarlo manualmente si necesitas cambiar algún dato."

# Función para preguntar al usuario
ask() {
    read -p "$1 [y/n]: " ans
    case $ans in
        y|Y) return 0 ;;
        *) return 1 ;;
    esac
}

# Detectar sistema operativo
if [ -f /etc/debian_version ]; then
    OS="debian"
elif [ -f /etc/arch-release ]; then
    OS="arch"
elif [ -f /etc/fedora-release ]; then
    OS="fedora"
else
    echo "Sistema operativo no soportado automáticamente. Instala dependencias manualmente."
    exit 1
fi

# Instalar dependencias base
echo "\n=== Instalación de dependencias base ==="
echo "Se instalarán Python, Node.js, ffmpeg, aria2, curl, wget y git según tu sistema operativo."
echo "Ejemplo para Debian/Ubuntu: sudo apt-get install -y python3 python3-pip python3-venv nodejs npm ffmpeg aria2 curl wget git"
echo "Ejemplo para Arch: sudo pacman -Sy --noconfirm python python-pip nodejs npm ffmpeg aria2 curl wget git"
echo "Ejemplo para Fedora: sudo dnf install -y python3 python3-pip nodejs npm ffmpeg aria2 curl wget git"
if [ "$OS" = "debian" ]; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv nodejs npm ffmpeg aria2 curl wget git
elif [ "$OS" = "arch" ]; then
    sudo pacman -Sy --noconfirm python python-pip nodejs npm ffmpeg aria2 curl wget git
elif [ "$OS" = "fedora" ]; then
    sudo dnf install -y python3 python3-pip nodejs npm ffmpeg aria2 curl wget git
fi

# Instalar paquetes globales Node.js
echo "\nInstalando paquetes globales de Node.js: webtorrent-hybrid y node-pre-gyp"
echo "Ejemplo: sudo npm install -g webtorrent-hybrid node-pre-gyp"
sudo npm install -g webtorrent-hybrid node-pre-gyp

# Opción: instalación reducida para Raspberry Pi con selección de servicios
if ask "¿Quieres instalar la versión reducida para Raspberry Pi (seleccionar servicios)?"; then
    echo "\n=== Instalación reducida para Raspberry Pi (selección de servicios) ==="
    # Comprobar docker
    if ! command -v docker >/dev/null 2>&1; then
        echo "Docker no está instalado. Instalando Docker..."
        if [ "$OS" = "debian" ]; then
            # Descargar y verificar usando download_and_verify (comprueba checksums.txt y su firma si está presente)
            if ! download_and_verify "https://get.docker.com" "get-docker.sh" "get-docker.sh"; then
                echo "Error al descargar/verificar get-docker.sh. Abortando."; rm -f get-docker.sh; exit 1
            fi
            sudo sh get-docker.sh
            rm -f get-docker.sh
        else
            echo "Instala Docker manualmente para continuar.";
            exit 1
        fi
    fi

    # Preguntar si usar un preset global o seleccionar manualmente servicios
    INSTALL_PORTAINER=false
    INSTALL_REDIS=false
    INSTALL_BOT_LOCAL=false
    INSTALL_WEB_LOCAL=false
    INSTALL_WEB_LIGHT=false
    INSTALL_WEB_FULL=false
    INSTALL_API_LOCAL=false

    if ask "¿Usar un preset de instalación para Raspberry Pi?"; then
        echo "Presets disponibles: minimal, server, full, dev, headless"
        read -p "Elige preset (minimal/server/full/dev/headless): " RPI_PRESET
        case "$RPI_PRESET" in
            minimal)
                INSTALL_PORTAINER=true
                INSTALL_REDIS=false
                INSTALL_BOT_LOCAL=false
                INSTALL_WEB_LIGHT=true
                INSTALL_WEB_FULL=false
                INSTALL_API_LOCAL=false
                ;;
            server)
                INSTALL_PORTAINER=true
                INSTALL_REDIS=true
                INSTALL_BOT_LOCAL=false
                INSTALL_WEB_LIGHT=false
                INSTALL_WEB_FULL=true
                INSTALL_API_LOCAL=false
                ;;
            full)
                INSTALL_PORTAINER=true
                INSTALL_REDIS=true
                INSTALL_BOT_LOCAL=true
                INSTALL_WEB_LIGHT=false
                INSTALL_WEB_FULL=true
                INSTALL_API_LOCAL=true
                ;;
            dev)
                INSTALL_PORTAINER=false
                INSTALL_REDIS=true
                INSTALL_BOT_LOCAL=true
                INSTALL_WEB_LIGHT=false
                INSTALL_WEB_FULL=true
                INSTALL_API_LOCAL=true
                ;;
            headless)
                INSTALL_PORTAINER=false
                INSTALL_REDIS=true
                INSTALL_BOT_LOCAL=false
                INSTALL_WEB_LIGHT=false
                INSTALL_WEB_FULL=false
                INSTALL_API_LOCAL=true
                ;;
            *)
                echo "Preset desconocido; continuando con selección manual."
                ;;
        esac
    fi

    # Si no se estableció preset que incluya servicios, permitir selección manual (por si nadie tocó preset)
    if ! $INSTALL_PORTAINER && ! $INSTALL_REDIS && ! $INSTALL_BOT_LOCAL && ! $INSTALL_WEB_LIGHT && ! $INSTALL_WEB_FULL && ! $INSTALL_API_LOCAL; then
        if ask "Instalar Portainer (gestión Docker)?"; then INSTALL_PORTAINER=true; fi
        if ask "Instalar Redis en Docker?"; then INSTALL_REDIS=true; fi
        if ask "Instalar Bot (local, en venv)?"; then INSTALL_BOT_LOCAL=true; fi
        # Selección de versión de la web: ninguna / ligera / completa
        echo "¿Qué versión de la web quieres instalar?"
        echo "  (n) Ninguna  (l) Ligera  (f) Completa"
        read -p "Opción [n/l/f] (por defecto n): " WEB_OPT
        case "$WEB_OPT" in
            l|L) INSTALL_WEB_LIGHT=true ;;
            f|F) INSTALL_WEB_FULL=true ;;
            *) INSTALL_WEB_LOCAL=false ;;
        esac
        if ask "Instalar API Python (local, en venv)?"; then INSTALL_API_LOCAL=true; fi
    fi

    # Detectar arquitectura para información
    ARCH=$(uname -m)
    echo "Arquitectura detectada: $ARCH"

    COMPOSE_FILE="$(pwd)/docker-compose.rpi.yml"
    if $INSTALL_PORTAINER ; then
        if [ ! -f "$COMPOSE_FILE" ]; then
            echo "No se encontró $COMPOSE_FILE. Asegúrate de ejecutar este instalador desde la raíz del repositorio."
            exit 1
        fi
        echo "Iniciando Portainer..."
        if command -v docker-compose >/dev/null 2>&1; then
            sudo docker-compose -f "$COMPOSE_FILE" up -d
        else
            sudo docker compose -f "$COMPOSE_FILE" up -d
        fi
        echo "Portainer iniciado en http://<tu_raspberry_pi>:9000"
    fi

    if $INSTALL_REDIS ; then
        echo "Iniciando Redis en Docker..."
        if sudo docker ps -a --format '{{.Names}}' | grep -q '^redis$'; then
            echo "Contenedor 'redis' ya existe. Arrancándolo..."
            sudo docker start redis || true
        else
            sudo docker run -d --name redis --restart always -p 6379:6379 redis:alpine
        fi
        echo "Redis accesible en el puerto 6379"
    fi

    if $INSTALL_BOT_LOCAL ; then
        echo "Instalando Bot localmente (venv)..."
        if [ -d "projects/bot/python_bot" ]; then
            cd projects/bot/python_bot
            python3 -m venv .venv
            source .venv/bin/activate
            pip install --upgrade pip setuptools wheel
            if [ -f requirements.txt ]; then
                pip install -r requirements.txt
            fi
            cd ../../../..
            # Ejecutar verificación de integridad de bots antes de declarar instalado/ejecutable
            if [ -f "$(pwd)/scripts/verify_bots.sh" ]; then
                echo "Verificando integridad de los bots..."
                bash "$(pwd)/scripts/verify_bots.sh" || { echo "Verificación de integridad fallida. No continúes hasta resolver inconsistencias."; exit 1; }
            else
                echo "Aviso: scripts/verify_bots.sh no encontrado; omitiendo verificación de bots." 
            fi
            echo "Bot instalado. Para ejecutarlo: cd projects/bot/python_bot && source .venv/bin/activate && python3 main.py"
        else
            echo "No se encontró la ruta projects/bot/python_bot; omitiendo instalación del bot local."
        fi
    fi

    if $INSTALL_WEB_LIGHT ; then
        echo "Instalando Web ligera (build optimizado si existe)..."
        if [ -d "web" ]; then
            cd web
            if [ -f package.json ]; then
                npm install
                if grep -q '"build:light"' package.json 2>/dev/null; then
                    npm run build:light || true
                    echo "Build ligera ejecutada (build:light)."
                elif grep -q '"build"' package.json 2>/dev/null; then
                    npm run build || true
                    echo "Build ejecutada (build)."
                else
                    echo "No hay script de build en package.json; usaremos la versión estática ligera incluida en /web_light o copiaremos módulos seleccionados."
                    # Si existe web_light, copiar su contenido a web/build para servir con nginx
                    if [ -d "$(pwd)/../web_light" ] || [ -d "$(pwd)/web_light" ]; then
                        mkdir -p ../web/build
                        if [ -d "$(pwd)/../web_light" ]; then
                            cp -r ../web_light/* ../web/build/
                        else
                            cp -r web_light/* ../web/build/
                        fi
                        echo "Contenido de web_light copiado a web/build."
                    else
                        echo "No se encontró web_light; la web ligera requiere build o web_light disponible."
                    fi
                fi
            else
                echo "No hay package.json en web; intentaremos montar una web ligera desde módulos disponibles."
            fi
            cd ..

            # Preguntar al usuario si quiere un preset o selección manual
            echo "¿Quieres usar un preset para la web ligera o seleccionar módulos manualmente?"
            echo "Presets disponibles: minimo, admin, full_light, traductores, anuncios"
            read -p "Escribe 'preset' o 'manual' (por defecto 'preset'): " PRESET_OR_MANUAL
            PRESET_OR_MANUAL=${PRESET_OR_MANUAL:-preset}
            if [ "$PRESET_OR_MANUAL" = "preset" ]; then
                read -p "Elige preset (minimo/admin/full_light/traductores/anuncios): " CHOSEN_PRESET
                CHOSEN_PRESET=${CHOSEN_PRESET:-minimo}
                echo "Usando preset: $CHOSEN_PRESET"
                sudo bash ./scripts/assemble_web_light.sh "$CHOSEN_PRESET"
            else
                echo "Selecciona los módulos para la web ligera (separados por espacios). Opciones válidas: index login chat status monitor translations links tutorial anuncios owner bots"
                read -p "Módulos (ej: index status login): " SELECTED_MODULES
                if [ -n "$SELECTED_MODULES" ]; then
                    echo "Montando módulos: $SELECTED_MODULES"
                    sudo bash ./scripts/assemble_web_light.sh $SELECTED_MODULES
                else
                    echo "No se seleccionaron módulos; se usará el contenido de web/build si existe."
                fi
                # After assembling, ask if user wants to further manage modules
                if [ -f "web/build/modules.txt" ]; then
                    echo "¿Deseas añadir o eliminar módulos de la web ligera ahora? (s/n)"
                    if ask "Editar modulos web ahora?"; then
                        echo "Usa: ./scripts/manage_web_light.sh list|add|remove"
                        echo "Ejemplo: ./scripts/manage_web_light.sh add chat"
                    fi
                fi
            fi
        else
            echo "No se encontró la carpeta 'web'; omitiendo instalación de la web ligera."
        fi
    fi

    if $INSTALL_WEB_FULL ; then
        echo "Instalando Web completa (dependencias npm)..."
        if [ -d "web" ]; then
            cd web
            if [ -f package.json ]; then
                npm install
                echo "Dependencias instaladas. Inicia la web completa con 'npm start' o según la documentación del proyecto."
            else
                echo "No hay package.json en web; omitiendo instalación de la web completa."
            fi
            cd ..
        else
            echo "No se encontró la carpeta 'web'; omitiendo instalación de la web completa."
        fi
    fi

    if $INSTALL_API_LOCAL ; then
        echo "Instalando API Python localmente (venv)..."
        if [ -d "python_api" ]; then
            cd python_api
            python3 -m venv .venv
            source .venv/bin/activate
            if [ -f requirements_ai.txt ]; then
                pip install -r requirements_ai.txt
            fi
            if [ -f requirements.txt ]; then
                pip install -r requirements.txt
            fi
            cd ..
            echo "API instalada. Para ejecutarla: cd python_api && source .venv/bin/activate && python3 ai_server.py"
        else
            echo "No se encontró la carpeta 'python_api'; omitiendo instalación de la API."
        fi
    fi

    # After services are set up, offer to manage docker services interactively
    echo "¿Quieres gestionar servicios Docker ahora (iniciar/parar/eliminar servicios individuales)?"
    if ask "Gestionar servicios Docker?"; then
        echo "Listado de servicios disponibles:"; docker compose -f docker-compose.rpi.services.yml config --services || true
        echo "Para gestionar usa: ./scripts/manage_services_rpi.sh list|start|stop|remove <servicio>"
    fi

    echo "Instalación reducida para Raspberry Pi completada."
    exit 0
fi

# Instalar y configurar BOT
if ask "¿Quieres instalar y configurar el bot?"; then
if ask "¿Quieres instalar y configurar el bot?"; then
    echo "\n=== Instalación y configuración del bot ==="
    echo "Se creará un entorno virtual Python y se instalarán las dependencias del bot."
    echo "Ejemplo: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    cd projects/bot/python_bot
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip setuptools wheel
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt
    fi
    cd ../../../..
    echo "Bot instalado. Para ejecutarlo: cd projects/bot/python_bot && source .venv/bin/activate && python3 main.py"
fi

# Instalar y configurar WEB
if ask "¿Quieres instalar y configurar la web?"; then
if ask "¿Quieres instalar y configurar la web?"; then
    echo "\n=== Instalación y configuración de la web ==="
    echo "Se instalarán las dependencias locales de Node.js si existe package.json."
    echo "Ejemplo: npm install"
    cd web
    if [ -f package.json ]; then
        npm install
    fi
    cd ..
    echo "Web instalada. Revisa la documentación para iniciar el servidor web."
fi

# Instalar y configurar API Python
if ask "¿Quieres instalar y configurar la API Python?"; then
if ask "¿Quieres instalar y configurar la API Python?"; then
    echo "\n=== Instalación y configuración de la API Python ==="
    echo "Se creará un entorno virtual Python y se instalarán las dependencias de la API."
    echo "Ejemplo: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements_ai.txt && pip install -r requirements.txt"
    cd python_api
    python3 -m venv .venv
    source .venv/bin/activate
    if [ -f requirements_ai.txt ]; then
        pip install -r requirements_ai.txt
    fi
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt
    fi
    cd ..
    echo "API Python instalada. Para ejecutarla: cd python_api && source .venv/bin/activate && python3 ai_server.py"
fi

# Instalar dependencias extra (opcional)
if ask "¿Quieres instalar dependencias extra para scripts y herramientas?"; then
if ask "¿Quieres instalar dependencias extra para scripts y herramientas?"; then
    echo "\n=== Instalación de dependencias extra para scripts y herramientas ==="
    echo "Se instalarán las dependencias Python de tools si existe requirements.txt."
    echo "Ejemplo: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    cd tools
    if [ -f requirements.txt ]; then
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
    fi
    cd ..
    echo "Herramientas instaladas. Revisa tools/README.md para más información."
fi

cat <<EOF

Instalación general completada.
Revisa cada sección para iniciar los servicios que necesites.
EOF
