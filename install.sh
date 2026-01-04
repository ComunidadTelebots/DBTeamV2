#!/bin/bash
# DBTeamV2 General Install Script
# Instala y configura todos los componentes: bot, web, API, dependencias extra

set -e
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
