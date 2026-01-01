# DBTeamV2 — Docker usage

Build the image on Docker Desktop / Linux:

```bash
./scripts/build_docker.sh
```

Run the image (exposes 8000 and 8081):

```bash
docker run -it --rm -p 8000:8000 -p 8081:8081 --name dbteamv2 dbteamv2:latest
```

Notes:
- The container runs the bot entrypoint `python projects/bot/python_bot/main.py`.
- Large assets (torrents, media) are excluded from the image; use `scripts/fetch_assets.sh` to download them into the workspace before building, or host them in Releases/S3 and fetch at runtime.
