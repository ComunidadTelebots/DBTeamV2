#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/service_monitor.log"

CMDS=(
  "python3 -m http.server 8000 --directory $REPO_ROOT/web"
  "python3 $REPO_ROOT/python_api/ai_server.py --host 127.0.0.1 --port 8081"
)

for i in "${!CMDS[@]}"; do
  cmd="${CMDS[$i]}"
  nohup bash -lc "$cmd" >> "$LOGFILE" 2>&1 &
  pid=$!
  echo "$pid" > "$LOG_DIR/service_$i.pid"
  echo "$(date -Iseconds) Started: $cmd (pid $pid)" >> "$LOGFILE"
done

while true; do
  for i in "${!CMDS[@]}"; do
    pid_file="$LOG_DIR/service_$i.pid"
    if [[ -f "$pid_file" ]]; then
      pid=$(cat "$pid_file")
      if ! kill -0 "$pid" 2>/dev/null; then
        echo "$(date -Iseconds) Process $pid not running. Restarting..." >> "$LOGFILE"
        cmd="${CMDS[$i]}"
        nohup bash -lc "$cmd" >> "$LOGFILE" 2>&1 &
        newpid=$!
        echo "$newpid" > "$pid_file"
        echo "$(date -Iseconds) Restarted: $cmd (pid $newpid)" >> "$LOGFILE"
      fi
    fi
  done
  sleep 5
done
