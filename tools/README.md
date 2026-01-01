Tools — Scanner & Status Page
================================

This folder contains a small local scanner `scan_and_clean_secrets.py` and a static status UI `status.html` to help detect and remediate leaked secrets.

Quick start (Windows, from repo root):

```powershell
# Activate your venv if you have one
.venv\Scripts\Activate.ps1

# Start the scanner service (binds to localhost only)
.venv\Scripts\python.exe tools\scan_and_clean_secrets.py --serve

# Open in your browser:
# http://127.0.0.1:8000/tools/status.html
```

Commands:

- `--scan` : run a scan and print JSON findings.
- `--clean` : backup matching files to `.secrets_backup/` and replace detected secrets with placeholders.
- `--serve` : start a local HTTP server on `127.0.0.1:8000` exposing `/scan`, `/clean` and serving `tools/status.html`.

Security notes:

- The server only listens on `127.0.0.1` to avoid remote access. Do not expose it publicly.
- Always rotate any secret you find and verify backups in `.secrets_backup/` before pushing changes.
DBTeam tools
=============

This folder contains helper scripts for developing and running the DBTeam project on Windows.

bot_control.ps1
---------------
Interactive PowerShell control panel. Usage (from repo root):

```powershell
. .\tools\bot_control.ps1
```

Menu options include:
- Show `/stats` and `/messages`
- Tail `bot.log`
- Restart bot
- Start web server + bot (asks for domain)
- Start web server + bot + Tor hidden service (creates `.onion` and writes `WEBAPP_ONION` to `.env`)
- Create `.onion` only (hidden service)
- Stop Tor (best-effort)
- Clean Tor data (removes `tor_data` and `WEBAPP_ONION` from `.env`)

Notes:
- `Set-WebDomain` writes `WEBAPP_URL` into `.env` so the frontend can read it via `/stats`.
- Tor support expects `tor` available on PATH or `tor\tor.exe` inside the repo.

smoke_test.ps1
--------------
Quick health check script that queries the static web server and the stats API (uses `WEB_API_SECRET` from `.env` if present).

Tor
---
To run Tor on Windows for hidden services, install Tor Expert Bundle or Tor Browser and point `bot_control.ps1` to the `tor.exe` location.

Security
--------
- Hidden services expose your local web server via Tor; review your content before publishing.
- `WEBAPP_ONION` and `WEBAPP_URL` are written to `.env`; keep this file safe.

Git
---
Commit and push changes from your local environment as needed. This environment cannot perform git pushes for you.
