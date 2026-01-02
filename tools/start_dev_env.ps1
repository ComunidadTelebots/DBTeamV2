#!/usr/bin/env pwsh
<#
Start development environment: launches the streamer backend and the dev proxy in separate processes.

Usage (PowerShell):
  .\tools\start_dev_env.ps1

Requirements:
  - Python 3 on PATH (callable via `py -3`)
  - Install Python deps for dev proxy: `py -3 -m pip install --user flask requests`

This script starts `python_api\stream_server.py` and `tools\dev_proxy.py` and writes PID files to `logs/`.
#>

Set-StrictMode -Version Latest
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$root = Resolve-Path (Join-Path $scriptDir "..")
Push-Location $root

$logsDir = Join-Path $root 'logs'
If (-Not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir | Out-Null }

Write-Output "Starting streamer backend (python_api\stream_server.py)..."
$proc1 = Start-Process -FilePath py -ArgumentList '-3','python_api\stream_server.py' -WorkingDirectory $root -PassThru
Write-Output "Streamer pid: $($proc1.Id)"; Set-Content -Path (Join-Path $logsDir 'dev_streamer.pid') -Value $proc1.Id

Start-Sleep -Seconds 1

Write-Output "Starting dev proxy (tools\dev_proxy.py)..."
$proc2 = Start-Process -FilePath py -ArgumentList '-3','tools\dev_proxy.py' -WorkingDirectory $root -PassThru
Write-Output "Proxy pid: $($proc2.Id)"; Set-Content -Path (Join-Path $logsDir 'dev_proxy.pid') -Value $proc2.Id

Write-Output "Development services started."
Write-Output "- Owner UI: http://127.0.0.1:8000/owner.html"
Write-Output "- Streamer API: http://127.0.0.1:8082"
Write-Output "To stop: use Stop-Process -Id <pid> or remove the pid files under logs/."

Pop-Location
