#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

pdir="$ROOT/pids"
if [ ! -d "$pdir" ]; then
  echo "No pid directory found. Nothing to stop."
  exit 0
fi

for f in "$pdir"/*.pid; do
  [ -e "$f" ] || continue
  pid=$(cat "$f" 2>/dev/null || true)
  if [ -n "$pid" ]; then
    if kill -0 "$pid" >/dev/null 2>&1; then
      echo "Stopping PID $pid (from $f)"
      kill "$pid" || true
      sleep 1
      if kill -0 "$pid" >/dev/null 2>&1; then
        echo "PID $pid still running, sending SIGKILL"
        kill -9 "$pid" || true
      fi
    else
      echo "PID $pid not running"
    fi
  fi
  rm -f "$f"
done

echo "Stopped services and removed pid files. Check logs/ for details."
