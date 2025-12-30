#!/usr/bin/env bash
set -e

# Start redis (if installed in container)
if command -v service >/dev/null 2>&1; then
  service redis-server start || true
fi

# If redis-server binary exists, try to start it as fallback
if command -v redis-server >/dev/null 2>&1; then
  if ! pgrep -x redis-server >/dev/null 2>&1; then
    redis-server --bind 127.0.0.1 &
  fi
fi

echo "Starting Web API (bot/web_api.lua)"
lua bot/web_api.lua &
WEB_API_PID=$!

if [ -n "$BOT_TOKEN" ]; then
  echo "BOT_TOKEN detected — starting Bot API adapter (bot/bot_api_adapter.lua)"
  lua bot/bot_api_adapter.lua &
  BOT_API_PID=$!
else
  echo "BOT_TOKEN not set — skipping Bot API adapter. Set BOT_TOKEN env to enable." 
fi

echo "Container setup complete. Web API PID=${WEB_API_PID}"

# Wait (keep container running)
wait -n || true
tail -f /dev/null
