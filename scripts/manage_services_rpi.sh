#!/bin/bash
set -euo pipefail
# Manage docker services defined in docker-compose.rpi.services.yml
# Usage:
#  ./scripts/manage_services_rpi.sh list
#  ./scripts/manage_services_rpi.sh start service1 service2
#  ./scripts/manage_services_rpi.sh stop service1 service2
#  ./scripts/manage_services_rpi.sh remove service1 service2

COMPOSE_FILE="docker-compose.rpi.services.yml"
if [ ! -f "$COMPOSE_FILE" ]; then echo "Compose file not found: $COMPOSE_FILE"; exit 1; fi

usage(){ echo "Usage: $0 list|start|stop|remove [services...]"; exit 1; }
if [ $# -lt 1 ]; then usage; fi
CMD="$1"; shift || true

case "$CMD" in
  list)
    echo "Defined services in $COMPOSE_FILE:"; docker compose -f "$COMPOSE_FILE" config --services
    ;;
  start)
    if [ $# -lt 1 ]; then echo "Specify services to start"; exit 1; fi
    docker compose -f "$COMPOSE_FILE" up -d "$@"
    ;;
  stop)
    if [ $# -lt 1 ]; then echo "Specify services to stop"; exit 1; fi
    docker compose -f "$COMPOSE_FILE" stop "$@"
    ;;
  remove)
    if [ $# -lt 1 ]; then echo "Specify services to remove"; exit 1; fi
    docker compose -f "$COMPOSE_FILE" rm -s -f "$@"
    ;;
  *) usage ;;
esac
