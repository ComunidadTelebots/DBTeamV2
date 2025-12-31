<#
windows-ssh-tunnel.ps1

Inicia un túnel SSH inverso desde Windows hacia una Raspberry Pi (o servidor
con Nginx Proxy Manager) para exponer tu `localhost:5500` en la Pi.

Uso recomendado (PowerShell):
  .\windows-ssh-tunnel.ps1 -PiUser pi -PiHost 203.0.113.10 -RemotePort 5500 -LocalPort 5500

Requisitos:
- Tener `ssh` disponible (Windows 10/11: cliente OpenSSH incluido) o usar WSL.
- Clave pública añadida en `~/.ssh/authorized_keys` del usuario Pi.

El script reiniciará el túnel automáticamente si se cae.
#>

param(
  [string]$PiUser = 'pi',
  [string]$PiHost = 'PI_IP_OR_HOST',
  [int]$RemotePort = 5500,
  [int]$LocalPort = 5500,
  [string]$KeyPath = "$env:USERPROFILE\.ssh\id_rsa",
  [int]$RestartDelaySeconds = 5
)

if ($PiHost -eq 'PI_IP_OR_HOST'){
  Write-Host "ERROR: Please set -PiHost to your Raspberry Pi public IP or hostname." -ForegroundColor Red
  exit 1
}

$sshCmd = "-o ServerAliveInterval=60 -o ExitOnForwardFailure=yes -R 0.0.0.0:$RemotePort:localhost:$LocalPort -i `"$KeyPath`" $PiUser@$PiHost -N"

Write-Host "Starting reverse SSH tunnel: remote $PiHost:$RemotePort -> local localhost:$LocalPort"

while ($true) {
  try {
    Write-Host "Launching ssh $PiUser@$PiHost (press Ctrl+C to stop)" -ForegroundColor Green
    & ssh $sshCmd
    $exit = $LASTEXITCODE
    Write-Host "ssh exited with code $exit. Restarting in $RestartDelaySeconds seconds..." -ForegroundColor Yellow
  }
  catch {
    Write-Host "ssh failed: $_" -ForegroundColor Red
  }
  Start-Sleep -Seconds $RestartDelaySeconds
}
