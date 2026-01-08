# DBTeamV2 — Consolidated README

This file is an aggregated README combining the root README with key information extracted from the project's sub-READMEs and moderation docs. If you prefer, I can replace `README.md` with this file.

## Project overview

DBTeamV2 is an administration Telegram bot + web UI with a Python backend and several deploy options (Docker, Swarm, Kubernetes). The repository groups active components under `projects/` and includes tools and deployment manifests.

- Bot: `projects/bot/python_bot`
- Backend/API: `projects/python_api`
- Frontend: `projects/web` and `projects/python_api/web`
- Deployment artifacts: `deploy/`, `docker-compose.yml`, `k8s/`

## Quick install (Docker)

```bash
./scripts/build_docker.sh
docker run -it --rm -p 8000:8000 -p 8081:8081 --name dbteamv2 dbteamv2:latest
```

## Quick install (local)

```bash
git clone https://github.com/Josepdal/DBTeamV2.git
cd DBTeamV2
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r projects/python_api/requirements.txt
./start_quick.sh
```

## Backend (python_api) quick start

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r projects/python_api/requirements.txt
uvicorn projects/python_api/python_api.app.main:app --reload --port 5500
```

## Moderation & Abuse (summary)

See `docs/moderation_and_abuse.md` for full documentation. Key points:

- Rule-based classifier suggests actions and pushes them to Redis queues (`moderation:actions`, `web:notifications`).
- `abuse_protection.py` counts requests per IP and supports blocking by IP/country/region/city/medium.
- Admin endpoints exist to list/apply suggestions and block/unblock entities.

## Important files & READMEs

- Root README: `README.md` (this repo). 
- Docker instructions: `README_DOCKER.md`.
- Deployment: `README_DEPLOY.md`.
- Backend notes: `projects/python_api/README.md`.
- Bot notes: `projects/bot/python_bot/README.md`.
- Moderation doc: `docs/moderation_and_abuse.md`.
- Consolidated summary: `docs/README_CONSOLIDATED.md`.

## Env vars (high level)

- `BOT_TOKEN`, `WEB_API_SECRET`, `REDIS_URL`.
- Moderation/abuse: `ADMIN_TOKEN`, `ABUSE_*`, `GEOIP_DB`, `BOT_TOKEN`, `ADMIN_TELEGRAM_CHAT`.
- Alerts (SMTP): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `ADMIN_EMAIL`.

## Tests

Run unit tests for abuse protection and stream server:

```powershell
python -m unittest -v python_api.tests.test_abuse_protection python_api.tests.test_stream_server
```

## Docker/Deployment

See `README_DOCKER.md` and `README_DEPLOY.md` for building images, Swarm and Kubernetes manifests, and production considerations.

---

If you'd like, I can now replace `README.md` with this consolidated file (keeping the original as `README.md.bak`). Approve and I'll perform the replacement.