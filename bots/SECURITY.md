Best practices para proteger bots contra ejecución de spam/malware

- Nunca ejecutar código recibido en mensajes. Evitar `eval`, `exec` o `subprocess` con entrada directa del usuario.
- Comandos del bot: implementar whitelist con permisos por rol (owner/admin) y token-scoped commands.
- Validar y sanitizar todos los campos de usuario antes de procesarlos.
- Adjuntos/archivos: no ejecutar nunca binarios directamente. Escanear con un antivirus (p.ej. `clamav`) antes de procesar.
- Si necesitas permitir ejecución de scripts, exige firma digital (GPG) o checksums pre-aprobados; verifica antes de ejecutar.
- Rate-limit y throttling: impedir envío masivo de comandos o adjuntos desde un mismo usuario/ip.
- Logs y alertas: registrar intentos sospechosos y bloquear/banear automáticamente en caso de patrones repetidos.
- Ejecutar bots como usuarios no-privilegiados y preferiblemente dentro de contenedores aislados (Docker) con capacidades limitadas.
- Escapar y validar rutas de archivos; nunca usar rutas construidas directamente desde mensajes.
- Para funcionalidades de autoplay/streaming: validar metadatos y usar procesos dedicados que no ejecuten código arbitrario.
- Mantener dependencias actualizadas y revisar con herramientas SCA (dependabot, safety, etc.).

Checklist de implementación mínima:
1. Eliminar `eval`/`exec` en el código del bot.
2. Añadir `scripts/verify_bots.sh` para comprobar integridad antes de arrancar.
3. Configurar `install.sh` o systemd service para ejecutar verificación antes del arranque.
4. Instalar `clamav` en servidores que reciban archivos enviados por usuarios y escanear antes de aceptar.
