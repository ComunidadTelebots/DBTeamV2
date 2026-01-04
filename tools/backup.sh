#!/bin/bash
# DBTeamV2 Automated Backup Script
# Realiza copias de seguridad automáticas de archivos clave y volúmenes Docker

set -e

# Carpeta destino de backups
BACKUP_DIR="${1:-./backups}"
mkdir -p "$BACKUP_DIR"

# Fecha actual
DATE=$(date +%F_%H-%M-%S)

# Backup de archivos de configuración y .env
CONFIG_FILES=(.env config/ deploy/ data/)
echo "Creando backup de configuración y datos..."
tar czf "$BACKUP_DIR/config_backup_$DATE.tar.gz" ${CONFIG_FILES[@]} 2>/dev/null || echo "Algunos archivos no existen, se omiten."

# Backup de Redis (si existe)
if pgrep redis-server &>/dev/null; then
    echo "Realizando backup de Redis..."
    redis-cli save
    cp /var/lib/redis/dump.rdb "$BACKUP_DIR/redis_backup_$DATE.rdb" 2>/dev/null || echo "No se encontró dump.rdb, omitiendo Redis."
fi

# Backup de volúmenes Docker (ejemplo: data_volume)
if command -v docker &>/dev/null; then
    VOLUMES=(data_volume)
    for VOL in "${VOLUMES[@]}"; do
        echo "Respaldando volumen Docker: $VOL"
        docker run --rm -v $VOL:/data -v "$BACKUP_DIR":/backup busybox tar czf /backup/${VOL}_backup_$DATE.tar.gz /data || echo "No se pudo respaldar el volumen $VOL."
    done
fi

# Backup de modelos y logs
if [ -d models ]; then
    echo "Respaldando modelos..."
    tar czf "$BACKUP_DIR/models_backup_$DATE.tar.gz" models/
fi
if [ -d logs ]; then
    echo "Respaldando logs..."
    tar czf "$BACKUP_DIR/logs_backup_$DATE.tar.gz" logs/
fi

# Mensaje final
cat <<EOF

Backup completado en $BACKUP_DIR
Puedes automatizar este script con cron o tareas programadas:
  0 3 * * * /ruta/a/tools/backup.sh /ruta/a/backups
EOF
