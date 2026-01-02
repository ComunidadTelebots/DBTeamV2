Plex Media Server — Docker Compose

This folder provides a simple Docker Compose file to run Plex (LinuxServer image) for local testing.

Defaults:
- Plex web UI: http://localhost:32400/web
- Config stored at `data/plex/config`
- Media root mapped to `data/media`

Quick start:
```powershell
cd deploy\plex
docker compose up -d
```

Notes:
- Adjust `PUID`/`PGID` and `TZ` in `docker-compose.yml` to match your host user.
- Populate `data/media` with your movies/series/music and add them in the Plex web UI.
- If you prefer the official Plex image (`plexinc/pms-docker`), replace the image in the compose file and read its docs regarding claim tokens.
