# DBTeamV2 — Consolidated Documentation

This document consolidates key information from the project README files and the moderation documentation.

## Components

- `projects/bot/python_bot` — bot, plugins, moderation classifier (`projects/bot/python_bot/moderation/classifier.py`).
- `projects/python_api` — backend/stream server, `abuse_protection.py`, `alerts.py`, admin endpoints and middleware.
- `projects/web` — frontend static files; `projects/python_api/web/app.js` contains the notifications bubble.
- `deploy/`, `docker-compose.yml`, `k8s/` — deployment artifacts for Docker/Swarm/Kubernetes.

## Moderation & Abuse Protection (summary)

See `docs/moderation_and_abuse.md` for full details; highlights:

- Rule-based classifier accumulates per-user points and posts suggestions to `moderation:actions` and `web:notifications`.
- `abuse_protection.py` counts requests per IP and supports blocking by IP/country/region/city/medium.
- Auto-block and escalate behavior controlled by `ABUSE_AUTO_BLOCK` and `ABUSE_AUTO_ESCALATE` env vars.
- Alerts are sent via `python_api/alerts.py` (Telegram and/or SMTP).

## Important Redis keys

- `mod:points:<group_id>:<user_id>` — per-user sliding window points.
- `moderation:actions` — FIFO queue of suggestions for admin review.
- `moderation:applied` — history of applied moderation actions.
- `web:notifications` — UI notifications queue.
- `abuse:blacklist:*` sets for IP/country/region/city/medium.

## Env vars and examples

- `REDIS_URL` — Redis connection string (e.g. `redis://127.0.0.1:6379/0`).
- `ADMIN_TOKEN` — simple admin token passed via `X-ADMIN-TOKEN` header.
- `ABUSE_IP_THRESHOLD`, `ABUSE_WINDOW`, `ABUSE_BLOCK_TTL`, `ABUSE_COUNTRY_THRESHOLD` — abuse thresholds.
- `ABUSE_AUTO_BLOCK`, `ABUSE_AUTO_ESCALATE` — enable auto-blocking or escalation flows.
- `GEOIP_DB` — optional MaxMind DB for geo resolution.
- Alerting: `BOT_TOKEN`, `ADMIN_TELEGRAM_CHAT`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `ADMIN_EMAIL`.

## Quick start (backend)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r projects/python_api/requirements.txt
uvicorn projects/python_api/python_api.app.main:app --reload --port 5500
```

## Docker & Deployment

- See `README_DOCKER.md` and `README_DEPLOY.md` for full Docker, Swarm, and Kubernetes instructions.

## Tests

- Unit tests exist at `python_api/tests/test_abuse_protection.py` and `python_api/tests/test_stream_server.py`.
- Run them with:

```powershell
python -m unittest -v python_api.tests.test_abuse_protection python_api.tests.test_stream_server
```

## Next steps and recommendations

- Secure admin endpoints beyond `ADMIN_TOKEN` (OAuth/session-based auth recommended).
- Use updated `GEOIP_DB` for region/city blocking accuracy.
- Configure alerting (Telegram or SMTP) with the appropriate env vars.
- Consider systemd/service/Windows Service wrappers to run `projects/tools/moderation_executor.py` and the web server.

---

File created programmatically by the consolidation step.
