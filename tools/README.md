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
