# CVE / Secret Remediation

Este documento describe cómo usar la herramienta local `tools/scan_and_clean_secrets.py` para detectar y limpiar secretos filtrados en el repositorio.

Resumen rápido:

- `python tools/scan_and_clean_secrets.py --scan` — detecta patrones comunes (Telegram tokens, AWS keys, GH PATs, PEM headers).
- `python tools/scan_and_clean_secrets.py --clean` — crea copias de seguridad en `.secrets_backup/` y reemplaza coincidencias con placeholders.
- `python tools/scan_and_clean_secrets.py --serve` — inicia un pequeño servidor en `http://127.0.0.1:8000` con endpoints:
  - `/scan` — devuelve JSON con hallazgos.
  - `/clean` — ejecuta la limpieza y devuelve un resumen JSON.

Pasos recomendados tras detectar un secreto:

1. Rotar la clave/credencial en el proveedor (por ejemplo, BotFather para `BOT_TOKEN`).
2. Ejecutar `--clean` localmente para reemplazar valores y hacer backup.
3. Reemplazar los archivos comprometidos por placeholders o moverlos fuera del repo (`secrets/`), luego commitear.
4. Opcional: purgar historial con `git-filter-repo` o BFG (coordinar con equipo).

Notas de seguridad

- El servidor HTTP está limitado a `127.0.0.1` para que sólo sea accesible localmente.
- La limpieza es conservadora: reemplaza coincidencias exactas por placeholders e incluye backup.
