# Python API scaffold for DBTeam

This folder contains a FastAPI-based scaffold implementing the web API endpoints from the Lua version:

- GET /messages
- GET /devices
- POST /devices/add
- POST /send
- POST /send_user
- POST /auth

Requirements: see `requirements.txt`.

Run locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN='your_bot_token'
export WEB_API_SECRET='a_long_secret'
# optional: WEB_API_KEY, WEB_API_ORIGIN, WEB_API_PORT
uvicorn app.main:app --host 0.0.0.0 --port 8081
```

Notes:
- Uses `cryptography` Fernet with key derived from `WEB_API_SECRET` to encrypt device tokens and sessions in Redis.
- Uses Redis keys compatible with the Lua version: `web:devices` (list), `web:outbox` (list), `web:messages` (list), `web:session:<token>`.
