<#
Start all web services for the project (Windows PowerShell).

Usage: run from repo root or double-click in Explorer.
  .\scripts\start_web_all.ps1

What it does:
 - Uses `.venv\Scripts\python.exe` if available, otherwise `python` on PATH.
 - Starts `python_api/ai_server.py` on 127.0.0.1:8081 (background process)
 - Serves `web/` on port 8000 and `web_light/` on port 8001 via `python -m http.server` (background processes)
 - Writes simple PID files to `logs/` and stores stdout/stderr into `logs/*.log`

This is a lightweight convenience script for local dev on Windows.
#>

Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Push-Location $scriptDir

if (-not (Test-Path -Path .venv\Scripts\python.exe)) {
    Write-Host "Warning: .venv python not found, falling back to 'python' on PATH" -ForegroundColor Yellow
    $py = "python"
} else {
    $py = Join-Path $scriptDir ".venv\Scripts\python.exe"
}

function Start-ServiceProcess($name, $workingDir, $args, $port, $logFile, $pidFile) {
    $absLog = Join-Path $scriptDir $logFile
    $absPid = Join-Path $scriptDir $pidFile
    New-Item -Path (Split-Path $absLog) -ItemType Directory -Force | Out-Null
    $startInfo = @{ 
        FilePath = $py; 
        ArgumentList = $args; 
        WorkingDirectory = $workingDir; 
        RedirectStandardOutput = $absLog; 
        RedirectStandardError = $absLog; 
        UseNewWindow = $false; 
    }
    try {
        $proc = Start-Process @startInfo -PassThru
        $proc.Id | Out-File -FilePath $absPid -Encoding ascii -Force
        Write-Host "Started $name (pid=$($proc.Id)); log=$absLog"
        return $proc
    } catch {
        Write-Host "Failed to start $name: $_" -ForegroundColor Red
        return $null
    }
}

# Ensure logs directory
New-Item -Path (Join-Path $scriptDir 'logs') -ItemType Directory -Force | Out-Null

# 1) AI server
if (Test-Path (Join-Path $scriptDir 'python_api\ai_server.py')) {
    $aiArgs = @('python_api\ai_server.py','--host','127.0.0.1','--port','8081')
    Start-ServiceProcess 'AIServer' $scriptDir $aiArgs 8081 'logs/ai_server.log' 'logs/ai_server.pid' | Out-Null
} else {
    Write-Host "AI server script not found; skipping AIServer" -ForegroundColor Yellow
}

# 2) Static web (web/)
if (Test-Path (Join-Path $scriptDir 'web')) {
    $webDir = Join-Path $scriptDir 'web'
    $webArgs = @('-m','http.server','8000')
    Start-ServiceProcess 'StaticWeb:web' $webDir $webArgs 8000 'logs/web_static.log' 'logs/web_static.pid' | Out-Null
} else {
    Write-Host "web/ directory not found; skipping static web" -ForegroundColor Yellow
}

# 3) web_light (optional)
if (Test-Path (Join-Path $scriptDir 'web_light')) {
    $wlDir = Join-Path $scriptDir 'web_light'
    $wlArgs = @('-m','http.server','8001')
    Start-ServiceProcess 'StaticWeb:web_light' $wlDir $wlArgs 8001 'logs/web_light.log' 'logs/web_light.pid' | Out-Null
} else {
    Write-Host "web_light/ directory not found; skipping web_light" -ForegroundColor Yellow
}

# 4) MTProxy probe server (optional)
# Set environment variable START_MTPROXY=1 to enable starting the probe server
if ($env:START_MTPROXY -eq '1' -and (Test-Path (Join-Path $scriptDir 'python_api\mtproxy_server.py'))) {
    $mpArgs = @('python_api\mtproxy_server.py')
    Start-ServiceProcess 'MTProxyStats' $scriptDir $mpArgs 8082 'logs/mtproxy_server.log' 'logs/mtproxy_server.pid' | Out-Null
} elseif ($env:START_MTPROXY -eq '1') {
    Write-Host "MTProxy server script not found; skipping MTProxyStats" -ForegroundColor Yellow
}

Write-Host "All requested services started. Check logs/ for outputs and *.pid for PIDs." -ForegroundColor Green

Pop-Location
