#!/bin/bash
# Verifica la integridad de los bots comparando los SHA256 listados en checksums.txt
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
checksums_file="$repo_root/checksums.txt"
sig_file="$repo_root/checksums.txt.sig"

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

echo "Comprobando existencia de $checksums_file..."
if [ ! -f "$checksums_file" ]; then
    echo "[error] No existe checksums.txt en $repo_root" >&2
    exit 2
fi

# Verificar firma si existe
if [ -f "$sig_file" ]; then
    if ! command -v gpg >/dev/null 2>&1; then
        echo "[error] checksums.txt.sig existe pero gpg no está disponible para verificar firma" >&2
        exit 3
    fi
    echo "Verificando firma GPG de checksums.txt..."
    # importar clave pública si está incluida
    if [ -f "$repo_root/keys/public.key" ]; then
        gpg --import "$repo_root/keys/public.key" >/dev/null 2>&1 || true
    fi
    if ! gpg --verify "$sig_file" "$checksums_file" >/dev/null 2>&1; then
        echo "[error] Firma GPG de checksums.txt inválida" >&2
        exit 4
    fi
    echo "[ok] Firma GPG verificada." 
else
    echo "[warn] No se encontró checksums.txt.sig; la verificación será menos segura." 
    read -p "¿Deseas continuar sin firma GPG? [y/N]: " cont
    case "$cont" in
        y|Y) echo "Continuando sin verificación GPG..." ;;
        *) echo "Abortando."; exit 5 ;;
    esac
fi

fail=0
echo "Leyendo entradas en checksums.txt y verificando..."
while read -r name expected_hash; do
    # Ignorar líneas vacías o comentarios
    case "$name" in
        ""|
        \#*) continue ;;
    esac
    target="$repo_root/$name"
    if [ -f "$target" ]; then
        actual=$(compute_sha256 "$target") || actual=""
        if [ -z "$actual" ]; then
            echo "[warn] No es posible calcular SHA256 para $target (faltan utilidades)" >&2
            fail=1; continue
        fi
        if [ "$actual" != "$expected_hash" ]; then
            echo "[error] HASH mismatch for $name" >&2
            echo "  esperado: $expected_hash" >&2
            echo "  actual:   $actual" >&2
            fail=1
        else
            echo "[ok] $name verified"
        fi
    elif [ -d "$target" ]; then
        # Calcular hash combinado de todos los ficheros en orden
        tmpfile=$(mktemp)
        while IFS= read -r -d $'\0' f; do
            fh=$(compute_sha256 "$f")
            printf "%s  %s\n" "$fh" "${f#$repo_root/}" >> "$tmpfile"
        done < <(find "$target" -type f -print0 | sort -z)
        combined=$(sha256sum "$tmpfile" | awk '{print $1}')
        rm -f "$tmpfile"
        if [ "$combined" != "$expected_hash" ]; then
            echo "[error] HASH mismatch for directory $name" >&2
            echo "  esperado: $expected_hash" >&2
            echo "  actual:   $combined" >&2
            fail=1
        else
            echo "[ok] $name verified (directory)"
        fi
    else
        echo "[warn] $name no existe en el repositorio; omitiendo" >&2
        fail=1
    fi
done < <(grep -E -v '^\s*$|^#' "$checksums_file" | awk '{print $1, $2}')

if [ "$fail" -ne 0 ]; then
    echo "[error] Verificación fallida. Revisa las entradas en checksums.txt o la firma GPG." >&2
    exit 6
fi

echo "Todas las entradas verificadas correctamente." 
exit 0
