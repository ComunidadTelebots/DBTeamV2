<#
quick_setup_windows.ps1
One-shot script to prepare and run DBTeamV2 on Windows.
Usage: run PowerShell as Administrator or normal user, in the repo root:
  .\quick_setup_windows.ps1
The script will:
 - check for Python and create .venv if missing
 - install required Python packages
 - prompt for BOT_TOKEN and write .env
 - start the static UI, API (uvicorn) and bot in background and save PIDs to pids\

Notes:
 - Redis is NOT started by this script. Use Docker or WSL to run Redis, or install Redis for Windows.
 - External native tools (aria2c, ffmpeg, libtorrent) must be installed separately if needed.
#>

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root

Write-Host "Working directory: $root"

# ensure logs and pids directories
if (-not (Test-Path logs)) { New-Item -ItemType Directory logs | Out-Null }
if (-not (Test-Path pids)) { New-Item -ItemType Directory pids | Out-Null }

# find python
$py = $null
$venvPy = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path $venvPy) { $py = $venvPy }
else {
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pyCmd) { $py = $pyCmd.Source }
}

if (-not $py) {
    Write-Error "Python not found. Install Python 3.9+ and re-run the script."
    Pop-Location; exit 1
}

Write-Host "Using Python: $py"

# create venv if missing
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtualenv .venv..."
    & $py -m venv .venv
}

$venvPy = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path $venvPy) { $py = $venvPy }

# upgrade pip and install deps
Write-Host "Upgrading pip and installing dependencies (this may take a few minutes)..."
& $py -m pip install --upgrade pip
try {
    & $py -m pip install -r projects\bot\python_bot\requirements.txt
} catch {
    Write-Warning "Failed to install bot requirements file; attempting pip install minimal packages"
    & $py -m pip install python-telegram-bot requests redis
}
try {
    if (Test-Path projects\python_api\python_api\requirements.txt) {
        & $py -m pip install -r projects\python_api\python_api\requirements.txt
    } else {
        & $py -m pip install fastapi uvicorn[standard] python-multipart cryptography requests redis
    }
} catch {
    Write-Warning "Failed to install API requirements exactly; ensure required packages are installed later."
}

# prompt for BOT_TOKEN
$token = Read-Host -Prompt "Enter your Telegram BOT_TOKEN (will be saved to .env)"
if (-not $token) { Write-Error "BOT_TOKEN required."; Pop-Location; exit 1 }

# generate WEB_API_SECRET
$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$secret = [Convert]::ToBase64String($bytes)

# write .env
$envContent = @"
BOT_TOKEN="$token"
WEB_API_SECRET="$secret"
REDIS_HOST="127.0.0.1"
REDIS_PORT="6379"
# AUTO_REGISTER_BOT_TOKEN=1
# API_BASE="https://cas.chat/api"
"@

$envContent | Out-File -Encoding UTF8 -FilePath .env -Force
Write-Host ".env created"

# start static UI
Write-Host "Starting static UI on http://127.0.0.1:8080 ..."
$staticProc = Start-Process -FilePath $py -ArgumentList '-m','http.server','8080','--bind','127.0.0.1','--directory','projects/web/web' -PassThru
$staticProc.Id | Out-File -FilePath pids\static.pid -Encoding ascii
Write-Host "Static UI PID: $($staticProc.Id)"

# start API (uvicorn)
Write-Host "Starting API (uvicorn) on http://127.0.0.1:8000 ..."
$apiProc = Start-Process -FilePath $py -ArgumentList '-m','uvicorn','projects.python_api.python_api.app.main:app','--host','127.0.0.1','--port','8000','--reload' -PassThru
$apiProc.Id | Out-File -FilePath pids\api.pid -Encoding ascii
Write-Host "API PID: $($apiProc.Id)"

# start bot
Write-Host "Starting bot (long-polling)..."
$botProc = Start-Process -FilePath $py -ArgumentList 'projects\bot\python_bot\main.py' -PassThru
$botProc.Id | Out-File -FilePath pids\bot.pid -Encoding ascii
Write-Host "Bot PID: $($botProc.Id)"

Write-Host "All processes started. Logs may be visible in the consoles of each process."
Write-Host "To stop the services run: .\stop_quick.ps1 (not provided) or use Task Manager to end the PIDs in pids\"

Pop-Location
