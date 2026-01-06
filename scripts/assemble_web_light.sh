#!/bin/bash
set -euo pipefail
# Assemble a lightweight web build from selected modules or presets
# Usage:
#  ./scripts/assemble_web_light.sh index status login
#  ./scripts/assemble_web_light.sh minimo

ROOT_DIR="$(pwd)"
SRC_DIR="$ROOT_DIR/web"
LIGHT_DIR="$ROOT_DIR/web_light"
OUT_DIR="$ROOT_DIR/web/build"

if [ ! -d "$OUT_DIR" ]; then
  mkdir -p "$OUT_DIR"
fi

echo "Assembling lightweight web into $OUT_DIR"

# Helper: copy common assets
cp_common_assets() {
  cp -f "$LIGHT_DIR/index.html" "$OUT_DIR/index.html" 2>/dev/null || true
  cp -f "$LIGHT_DIR/status.html" "$OUT_DIR/status.html" 2>/dev/null || true
  cp -f "$LIGHT_DIR/light-style.css" "$OUT_DIR/light-style.css" 2>/dev/null || true
  [ -f "$SRC_DIR/logo.svg" ] && cp -f "$SRC_DIR/logo.svg" "$OUT_DIR/logo.svg"
  [ -f "$SRC_DIR/favicon.svg" ] && cp -f "$SRC_DIR/favicon.svg" "$OUT_DIR/favicon.svg"
}

copy_module_files() {
  local module="$1"
  echo "Adding module: $module"
  case "$module" in
    index)
      [ -f "$SRC_DIR/index.html" ] && cp -f "$SRC_DIR/index.html" "$OUT_DIR/index.html"
      ;;
    login)
      for f in login.html login.js register.html register.js; do [ -f "$SRC_DIR/$f" ] && cp -f "$SRC_DIR/$f" "$OUT_DIR/"; done
      ;;
    chat)
      for f in chat.html chat.js; do [ -f "$SRC_DIR/$f" ] && cp -f "$SRC_DIR/$f" "$OUT_DIR/"; done
      ;;
    streaming|streamer|stream)
      # include streamer UI and related assets
      shopt -s nullglob
      for f in "$SRC_DIR"/*stream*.html "$SRC_DIR"/*stream*.js "$SRC_DIR"/*stream*.css; do [ -f "$f" ] && cp -f "$f" "$OUT_DIR/"; done
      shopt -u nullglob
      ;;
    torrents|torrent)
      shopt -s nullglob
      for f in "$SRC_DIR"/*torrent*.html "$SRC_DIR"/*torrent*.js "$SRC_DIR"/*torrent*.css; do [ -f "$f" ] && cp -f "$f" "$OUT_DIR/"; done
      shopt -u nullglob
      ;;
    media)
      for f in media.html media.js media.css; do [ -f "$SRC_DIR/$f" ] && cp -f "$SRC_DIR/$f" "$OUT_DIR/"; done
      ;;
    status)
      [ -f "$SRC_DIR/status.html" ] && cp -f "$SRC_DIR/status.html" "$OUT_DIR/"; [ -f "$SRC_DIR/status.js" ] && cp -f "$SRC_DIR/status.js" "$OUT_DIR/";
      ;;
    monitor)
      for f in monitor.html monitor.js; do [ -f "$SRC_DIR/$f" ] && cp -f "$SRC_DIR/$f" "$OUT_DIR/"; done
      ;;
    translations|traductores)
      for f in traducciones.html traducciones.js; do
        [ -f "$SRC_DIR/$f" ] && cp -f "$SRC_DIR/$f" "$OUT_DIR/"
      done
      if [ -d "$SRC_DIR/i18n/web" ]; then mkdir -p "$OUT_DIR/i18n/web" && cp -r "$SRC_DIR/i18n/web"/* "$OUT_DIR/i18n/web/"; fi
      ;;
    links)
      # Copy any files with 'link' or 'links' in the name (html, js, css)
      shopt -s nullglob
      for f in "$SRC_DIR"/*link*.html "$SRC_DIR"/*links*.html "$SRC_DIR"/*link*.js "$SRC_DIR"/*link*.css; do
        [ -f "$f" ] && cp -f "$f" "$OUT_DIR/"
      done
      shopt -u nullglob
      ;;
    tutorial)
      [ -f "$SRC_DIR/tutorial.html" ] && cp -f "$SRC_DIR/tutorial.html" "$OUT_DIR/";
      ;;
    help)
      [ -f "$SRC_DIR/help.html" ] && cp -f "$SRC_DIR/help.html" "$OUT_DIR/" || true
      ;;
    anuncios)
      for f in anuncios.html moderar_anuncios.html; do [ -f "$SRC_DIR/$f" ] && cp -f "$SRC_DIR/$f" "$OUT_DIR/"; done
      ;;
    owner|admin)
      for f in owner.html owner.js admin_bots.html bots.html bot_control.html; do [ -f "$SRC_DIR/$f" ] && cp -f "$SRC_DIR/$f" "$OUT_DIR/"; done
      ;;
    bots)
      for f in bots.html bots_resources_usage.html; do [ -f "$SRC_DIR/$f" ] && cp -f "$SRC_DIR/$f" "$OUT_DIR/"; done
      ;;
    *)
      echo "Módulo desconocido: $module (omitido)"
      ;;
  esac
}

# Presets
PRESET_MODULES=()
if [ "$#" -eq 1 ]; then
  case "$1" in
    minimo)
      PRESET_MODULES=(index status login)
      ;;
    admin)
      PRESET_MODULES=(index status owner bots bot_control admin_bots)
      ;;
    full_light)
      PRESET_MODULES=(index login chat status monitor translations links tutorial help anuncios owner bots bot_control admin_bots media torrents streaming)
      ;;
    media)
      PRESET_MODULES=(media)
      ;;
    torrents|torrent)
      PRESET_MODULES=(torrents)
      ;;
    traductores|translations)
      PRESET_MODULES=(translations)
      ;;
    anuncios)
      PRESET_MODULES=(anuncios)
      ;;
    *)
      PRESET_MODULES=()
      ;;
  esac
fi

# Start by copying common assets
cp_common_assets

if [ ${#PRESET_MODULES[@]} -gt 0 ]; then
  for m in "${PRESET_MODULES[@]}"; do copy_module_files "$m"; done
  SELECTED_MODULES=("${PRESET_MODULES[@]}")
else
  if [ "$#" -eq 0 ]; then
    echo "No modules specified and no preset matched. Nothing to add beyond base assets."
    SELECTED_MODULES=()
  else
    for module in "$@"; do copy_module_files "$module"; done
    SELECTED_MODULES=("$@")
  fi
fi

# Save selected modules for future management
if [ ${#SELECTED_MODULES[@]} -gt 0 ]; then
  echo "${SELECTED_MODULES[@]}" > "$OUT_DIR/modules.txt"
else
  rm -f "$OUT_DIR/modules.txt" 2>/dev/null || true
fi

echo "Assembly complete. Files in $OUT_DIR:"
ls -la "$OUT_DIR"
