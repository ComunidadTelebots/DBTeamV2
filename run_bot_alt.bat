@echo off
REM Run the bot with alternate token and optional flood parameters
if "%1"=="" (
  echo Usage: run_bot_alt.bat <BOT_TOKEN> [MIN_INTERVAL_SECONDS] [MAX_CONCURRENT]
  exit /b 1
)
set BOT_TOKEN=%1
if not "%2"=="" set TELEGRAM_MIN_INTERVAL=%2
if not "%3"=="" set TELEGRAM_MAX_CONCURRENT=%3
set PYTHONPATH=projects\bot
echo Starting bot with token %BOT_TOKEN: interval=%TELEGRAM_MIN_INTERVAL% concurrent=%TELEGRAM_MAX_CONCURRENT%
start "DBTeamBotAlt" ".\.venv\Scripts\python.exe" -u projects\bot\python_bot\main.py >> bot_alt.log 2>> bot_alt.err
exit /b 0
