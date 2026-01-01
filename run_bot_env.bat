@echo off
REM Temporary helper to start the bot with env vars set
set BOT_TOKEN=5724481351:AAHbKYPAHgYjGZK4XB3cOrkGXBbBxQHhjl0
set WEB_API_SECRET=yZc4OLfdUny6q/I/AGs7RqAJ4orRLAckndG1fEFnuXw=
set PYTHONPATH=projects\bot
start "DBTeamBot" ".\.venv\Scripts\python.exe" -u projects\bot\python_bot\main.py >> bot2.log 2>> bot2.err
exit /b 0
