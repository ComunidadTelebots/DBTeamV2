#!/bin/bash
# DBTeamV2 Bot Install Script (Python Bot)
# Instala dependencias modernas y prepara el entorno

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
    sudo apt-get install -y python3 python3-pip python3-venv ffmpeg aria2 curl wget git
elif [ "$OS" = "arch" ]; then
    sudo pacman -Sy --noconfirm python python-pip ffmpeg aria2 curl wget git
elif [ "$OS" = "fedora" ]; then
    sudo dnf install -y python3 python3-pip ffmpeg aria2 curl wget git
fi

# Instalar Node.js y paquetes globales
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo bash -
    sudo apt-get install -y nodejs
fi
sudo npm install -g webtorrent-hybrid node-pre-gyp

# Crear y activar entorno virtual Python
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel

# Instalar dependencias Python del bot
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi

# Mensaje final
cat <<EOF

Instalación completada.
Para iniciar el bot ejecuta:

source .venv/bin/activate
python3 main.py

EOF
