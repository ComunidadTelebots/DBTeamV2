@echo off
REM Temporary helper to start the bot with env vars set
REM This file is intentionally a placeholder. Do NOT commit real secrets here.
REM The bot will load secrets from a `.env` file in the repository root or from
REM the OS environment. Keep your secret `.env` outside version control (see secrets/LOCAL_SECRETS.md).

REM Example .env contents (DO NOT STORE REAL SECRETS IN THE REPO):
REM BOT_TOKEN="<your_bot_token>"
REM WEB_API_SECRET="change_me"

echo Loading environment variables from .env (if present)...
if exist .env (
	for /f "usebackq tokens=* delims=" %%L in (.env) do (
		set "line=%%L"
		echo %%L | findstr /b "#" >nul && (
			REM skip comments
		) || (
			for /f "tokens=1* delims==" %%A in ("%%L") do set "%%A=%%B"
		)
	)
) else (
	echo ".env not found; ensure BOT_TOKEN and WEB_API_SECRET are set in environment or secrets/"
)

echo Done. Use the real secrets from environment variables.
set PYTHONPATH=projects\bot
start "DBTeamBot" ".\.venv\Scripts\python.exe" -u projects\bot\python_bot\main.py >> bot2.log 2>> bot2.err
exit /b 0
