#!/bin/bash
# Script para seedear todos los .torrent de data/torrents con webtorrent-hybrid
# Requiere Node.js y webtorrent-hybrid instalado globalmente (npm install -g webtorrent-hybrid)

TORRENT_DIR="data/torrents"

for torrent in "$TORRENT_DIR"/*.torrent; do
  echo "Seedeando: $torrent"
  nohup webtorrent-hybrid "$torrent" --keep-seeding &
done

echo "Todos los torrents están siendo seedeados por webtorrent-hybrid."
