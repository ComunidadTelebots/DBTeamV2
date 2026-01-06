#!/bin/bash
set -euo pipefail
# Script to build multi-arch images for bot and api using docker buildx
# Usage examples:
#  - Build and push to Docker Hub: DOCKER_NAMESPACE=myuser DOCKER_PUSH=1 ./scripts/buildx_build.sh
#  - Build and load locally for testing (no push): DOCKER_NAMESPACE=myuser ./scripts/buildx_build.sh

DOCKER_NAMESPACE=${DOCKER_NAMESPACE:-dbteamv2}
DOCKER_PUSH=${DOCKER_PUSH:-0}
PLATFORMS=${PLATFORMS:-linux/arm/v7,linux/arm64,linux/amd64}

IMAGES=("${DOCKER_NAMESPACE}/bot:latest" "${DOCKER_NAMESPACE}/api:latest")

# Ensure buildx builder exists and is selected
if ! docker buildx inspect multi-builder >/dev/null 2>&1; then
  docker buildx create --use --name multi-builder
fi
docker buildx use multi-builder

for img in "${IMAGES[@]}"; do
  case "$img" in
    *bot*) DIR="./projects/bot/python_bot" ;;
    *api*) DIR="./python_api" ;;
    *) DIR="." ;;
  esac
  echo "\nBuilding $img from $DIR for $PLATFORMS"

  if [ "$DOCKER_PUSH" -eq 1 ]; then
    echo "Pushing multi-arch image $img to registry"
    docker buildx build --platform $PLATFORMS -t "$img" -f "$DIR/Dockerfile" "$DIR" --push
  else
    echo "Building and loading image $img locally (no push). Note: --load supports single-platform; using buildx to create images for local testing may be slow or limited."
    # Try to build for local arch and load into local docker engine
    docker buildx build --platform $PLATFORMS -t "$img" -f "$DIR/Dockerfile" "$DIR" --load || true
  fi
done

echo "Buildx process completed."
