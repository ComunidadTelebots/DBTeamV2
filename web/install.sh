#!/bin/bash
# DBTeamV2 Web Install Script
# Instala dependencias y prepara el entorno para la web

set -e

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

# Instalar dependencias del sistema
if [ "$OS" = "debian" ]; then
    sudo apt-get update
    sudo apt-get install -y nodejs npm ffmpeg aria2 curl wget git
elif [ "$OS" = "arch" ]; then
    sudo pacman -Sy --noconfirm nodejs npm ffmpeg aria2 curl wget git
elif [ "$OS" = "fedora" ]; then
    sudo dnf install -y nodejs npm ffmpeg aria2 curl wget git
fi

# Instalar paquetes globales necesarios
sudo npm install -g webtorrent-hybrid node-pre-gyp

# Instalar dependencias locales si hay package.json
if [ -f package.json ]; then
    npm install
fi

# Mensaje final
cat <<EOF

Instalación de la web completada.
Revisa la documentación para iniciar el servidor web o integrar con el backend.

EOF
