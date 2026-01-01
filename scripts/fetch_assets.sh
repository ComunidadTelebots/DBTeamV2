#!/usr/bin/env bash
set -euo pipefail

echo "This script fetches large assets excluded from git (torrents, media)."
echo "Edit the URL variables below to point to your storage (GitHub Releases, S3, etc)."

# Example placeholders - update to real URLs
TMP_TORRENT_URL="https://example.com/assets/tmp_downloaded.torrent"
DEST_DIR="projects/bot"

mkdir -p "$DEST_DIR"

echo "Downloading tmp_downloaded.torrent to $DEST_DIR"
# curl example
# curl -L -o "$DEST_DIR/tmp_downloaded.torrent" "$TMP_TORRENT_URL"

# wget example
# wget -O "$DEST_DIR/tmp_downloaded.torrent" "$TMP_TORRENT_URL"

# aria2c example (fast, parallel)
# aria2c -x16 -s16 -o "$DEST_DIR/tmp_downloaded.torrent" "$TMP_TORRENT_URL"

echo "No URLs configured. Open this script and set TMP_TORRENT_URL to fetch assets."
