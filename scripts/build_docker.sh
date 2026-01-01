#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="dbteamv2:latest"
docker build -t ${IMAGE_NAME} .
echo "Built ${IMAGE_NAME}"
