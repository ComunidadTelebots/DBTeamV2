<#
run_bot_with_check.ps1
- Prompts for an admin (chat id or @username), writes SUDO_USERS to .env
- Sends a test message to the admin via Bot API
- Starts the python bot in foreground with DEBUG logging so you can see incoming updates
Usage: run from repo root in PowerShell:
  .\run_bot_with_check.ps1
#>

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root

function Read-EnvValue($file, $key) {
    if (-not (Test-Path $file)) { return $null }
    $lines = Get-Content $file -ErrorAction SilentlyContinue
    # build regex dynamically to avoid quoting issues
    $escapedKey = [regex]::Escape($key)
    $regex = '^\\s*' + $escapedKey + '\\s*=\\s*"?(.+?)"?\\s*$'
    foreach ($l in $lines) {
        if ($l -match $regex) {
            return $Matches[1]
        }
    }
    return $null
}

$envFile = Join-Path $root '.env'
$token = Read-EnvValue $envFile 'BOT_TOKEN'
if (-not $token) {
    $token = Read-Host -Prompt 'BOT_TOKEN not found in .env. Enter your Bot token (will be saved)'
    if (-not $token) { Write-Error 'BOT_TOKEN required'; Pop-Location; exit 1 }
    # create minimal .env if missing
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $secret = [Convert]::ToBase64String($bytes)
    $envContent = @"
BOT_TOKEN="$token"
WEB_API_SECRET="$secret"
REDIS_HOST="127.0.0.1"
REDIS_PORT="6379"
"@
    $envContent | Out-File -Encoding UTF8 -FilePath $envFile -Force
    Write-Host '.env created with provided BOT_TOKEN'
}

# admin (chat id or @username)
$admin = Read-Host -Prompt 'Enter admin chat id (numeric) or @username to receive test message'
if (-not $admin) { Write-Error 'Admin required'; Pop-Location; exit 1 }

# Update or add SUDO_USERS in .env
$envLines = @()
if (Test-Path $envFile) { $envLines = Get-Content $envFile }
$found = $false
for ($i=0; $i -lt $envLines.Count; $i++) {
    if ($envLines[$i] -match '^\s*SUDO_USERS\s*=') {
        $envLines[$i] = "SUDO_USERS=""$admin"""
        $found = $true
        break
    }
}
if (-not $found) {
    $envLines += "SUDO_USERS=""$admin"""
}
$envLines | Out-File -Encoding UTF8 -FilePath $envFile -Force
Write-Host "SUDO_USERS set to: $admin in $envFile"

# Send test message via Bot API
$sendTarget = $admin
# if username given with @, Telegram accepts it
$body = @{ chat_id = $sendTarget; text = "[DBTeamV2] Test message: bot token configured and script running." } | ConvertTo-Json
try {
    $resp = Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/sendMessage" -Method Post -ContentType 'application/json' -Body $body -ErrorAction Stop
    if ($resp.ok) { Write-Host "Test message sent to $sendTarget (message_id=$($resp.result.message_id))" }
    else { Write-Warning "Telegram API returned not-ok: $($resp | ConvertTo-Json -Depth 3)" }
} catch {
    Write-Warning "Failed to send test message: $_"
}

# Start bot in foreground with DEBUG logging
# Prefer .venv python
$venvPy = Join-Path $root '.venv\Scripts\python.exe'
if (Test-Path $venvPy) { $python = $venvPy } else { $python = 'python' }

Write-Host "Starting bot in foreground using: $python"
Write-Host "Press Ctrl+C to stop."

& $python -u -c "import os,sys,logging,runpy; logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(name)s %(levelname)s: %(message)s'); logging.getLogger('telegram').setLevel(logging.DEBUG); logging.getLogger('telegram.ext').setLevel(logging.DEBUG); sys.path.insert(0, os.path.join(r'$root','projects','bot')); runpy.run_path(os.path.join(r'$root','projects','bot','python_bot','main.py'), run_name='__main__')"

Pop-Location
