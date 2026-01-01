#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# load .env if exists
if [ -f .env ]; then
  # shellcheck disable=SC1091
  source .env
fi

# activate virtualenv
if [ -d .venv ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  echo "Virtualenv .venv not found. Create it: python3 -m venv .venv"
  exit 1
fi

export PYTHONPATH="$ROOT/projects"

mkdir -p logs pids

# start redis if available
if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl start redis-server || true
else
  sudo service redis-server start || true
fi

# start static UI
nohup python3 -m http.server 8080 --bind 127.0.0.1 --directory projects/web/web > logs/static.log 2>&1 &
echo $! > pids/static.pid

# start API
nohup uvicorn projects.python_api.python_api.app.main:app --host 127.0.0.1 --port 8000 --reload > logs/api.log 2>&1 &
echo $! > pids/api.pid

# start bot
nohup python3 projects/bot/python_bot/main.py > logs/bot.log 2>&1 &
echo $! > pids/bot.pid

printf "Started services. Logs: %s, %s, %s\n" "logs/static.log" "logs/api.log" "logs/bot.log"
printf "PIDs saved in pids/*.pid\n"
