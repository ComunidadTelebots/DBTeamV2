# Nginx Proxy Manager: configurar Proxy Host para túnel SSH inverso

Resumen: si ya tienes Nginx Proxy Manager (NPM) en una Raspberry Pi y quieres que NPM
redirija `https://app.tudominio.com` a tu servidor local `localhost:5500`, crea
un túnel SSH inverso desde tu máquina Windows hacia la Pi y configura un Proxy Host
en NPM apuntando a `127.0.0.1:REMOTE_PORT` (REMOTE_PORT es el puerto remoto
expuesto por el túnel, normalmente 5500).

Pasos rápidos:

1. Asegúrate de que tu dominio `app.tudominio.com` apunta al IP público de la Pi.

2. En la Pi, habilita `GatewayPorts` en `/etc/ssh/sshd_config`:

   sudo sed -i 's/#GatewayPorts no/GatewayPorts yes/' /etc/ssh/sshd_config
   sudo systemctl restart ssh

3. En Windows, usa el script `scripts\windows-ssh-tunnel.ps1` (modifica `-PiHost`):

   powershell -ExecutionPolicy Bypass -File .\scripts\windows-ssh-tunnel.ps1 -PiUser pi -PiHost 203.0.113.10 -RemotePort 5500 -LocalPort 5500

   Esto hará que la Pi escuche en `0.0.0.0:5500` y reenvíe conexiones a tu
   `localhost:5500` en Windows.

4. En Nginx Proxy Manager admin (http://PI_IP:81):

   - Proxy Hosts → Add Proxy Host
     - Domain Names: `app.tudominio.com`
     - Scheme: `http`
     - Forward Hostname / IP: `127.0.0.1`
     - Forward Port: `5500` (o el `REMOTE_PORT` que hayas elegido)
     - Enable Websockets: ON
     - Block Common Exploits: ON

   - SSL tab → Request a new SSL Certificate (Let's Encrypt) — solo si `app.tudominio.com`
     apunta al IP público de la Pi y puertos 80/443 están abiertos.

5. Verifica abriendo `https://app.tudominio.com/login.html`.

Notas y troubleshooting:
- Si Let's Encrypt falla porque ISP bloquea 80/443, usa DNS-01 (ACME) o Cloudflare.
- Si `ssh` no puede enlazar `0.0.0.0:5500`, prueba otro `RemotePort` (p.ej. 15500)
  y usa ese puerto en NPM.
- Para mantener el túnel activo en Windows, crea una tarea programada que ejecute
  el script al iniciar sesión o usa `nssm` para correrlo como servicio.
