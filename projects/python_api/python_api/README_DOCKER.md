Docker build & publish

This document explains how to build and publish the API and Bot Docker images locally or via GitHub Actions.

Local build (Docker installed):

# Build API image
```bash
cd python_api
docker build -f Dockerfile -t myrepo/dbteamv2-api:alfa .

# Build Bot image (same Dockerfile, different tag)
docker build -f Dockerfile -t myrepo/dbteamv2-bot:alfa .
```

# Push to Docker Hub (login required)
```bash
docker tag myrepo/dbteamv2-api:alfa mydockerhubuser/dbteamv2-api:alfa
docker tag myrepo/dbteamv2-bot:alfa mydockerhubuser/dbteamv2-bot:alfa
docker push mydockerhubuser/dbteamv2-api:alfa
docker push mydockerhubuser/dbteamv2-bot:alfa
```

Publish via GitHub Actions

A workflow is included at `.github/workflows/docker-publish.yml` that builds and pushes images to GitHub Container Registry `ghcr.io/<owner>/...` on push to the `alfa` branch.

Notes
- Ensure secrets and permissions are set for registry when using external registries.
- The same image can be used for `api` and `bot` (entrypoint differs). Use appropriate `docker run --entrypoint` or override `CMD`.
