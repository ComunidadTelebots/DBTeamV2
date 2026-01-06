#!/bin/bash
# Script para firmar checksums.txt con GPG (detached, ASCII-armored)
# Uso: ./scripts/sign_checksums.sh <key-id>

set -e

if [ ! -f checksums.txt ]; then
    echo "No se encontró checksums.txt en el directorio actual. Ejecuta desde la raíz del repo."
    exit 1
fi

if ! command -v gpg >/dev/null 2>&1; then
    echo "gpg no está instalado. Instálalo para firmar: sudo apt-get install -y gnupg"
    exit 1
fi

KEYID="$1"
if [ -z "$KEYID" ]; then
    echo "Uso: $0 <key-id>
Ejemplo: $0 youremail@example.com"
    exit 1
fi

echo "Firmando checksums.txt con la clave $KEYID..."
gpg --batch --yes --armor --detach-sign -u "$KEYID" -o checksums.txt.sig checksums.txt
echo "Firma creada: checksums.txt.sig"
echo "Exporta tu clave pública para distribuirla (p.ej. keys/public.key):"
echo "  gpg --armor --export $KEYID > keys/public.key"
