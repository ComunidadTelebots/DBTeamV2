#!/usr/bin/env bash
set -euo pipefail

echo "Building backend image dbteamv2:alfa"
docker build -t dbteamv2:alfa .

echo "Building nginx image dbteamv2-nginx:alfa"
docker build -t dbteamv2-nginx:alfa -f deploy/Dockerfile.nginx .

echo "Done. You can push images to your registry if deploying to remote clusters."
