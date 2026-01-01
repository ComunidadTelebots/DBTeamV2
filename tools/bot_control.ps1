# Simple PowerShell control panel for DBTeam bot
# Usage: run .\tools\bot_control.ps1

function Get-BotApiKey {
    if (Test-Path .env) {
        $k = (Get-Content .env | Where-Object { $_ -match '^WEB_API_SECRET=' }) -replace '^[^=]*=' , ''
        return $k.Trim('"')
    }
    return ''
}

function Get-BotStats {
    param([string]$Base = 'http://127.0.0.1:8081')
    $k = Get-BotApiKey
    $h = @{}
    if ($k) { $h['Authorization'] = "Bearer $k" }
    try {
        $r = Invoke-RestMethod -Uri ($Base + '/stats') -Headers $h -TimeoutSec 5
        $r | ConvertTo-Json -Depth 4
    } catch {
        Write-Host "Failed to fetch /stats: $_" -ForegroundColor Red
    }
}

function Get-BotMessages {
    param([string]$Base = 'http://127.0.0.1:8081')
    $k = Get-BotApiKey
    $h = @{}
    if ($k) { $h['Authorization'] = "Bearer $k" }
    try {
        $r = Invoke-RestMethod -Uri ($Base + '/messages') -Headers $h -TimeoutSec 5
        return $r
    } catch {
        Write-Host "Failed to fetch /messages: $_" -ForegroundColor Red
    }
}

function Read-MessagesInteractive {
    param([string]$Base = 'http://127.0.0.1:8081')
    $msgs = Get-BotMessages -Base $Base
    if (-not $msgs) { Write-Host 'No messages retrieved' -ForegroundColor Yellow; return }
    # show last 50 with index
    $arr = @($msgs)
    $count = $arr.Count
    $start = [Math]::Max(0, $count - 50)
    for ($i=$start; $i -lt $count; $i++) {
        $index = $i - $start + 1
        $line = $arr[$i].line -replace "\r?\n", ' '
        Write-Host "[$index] $line"
    }
    $sel = Read-Host 'Selecciona número para ver completo (o Enter para salir)'
    if (-not $sel) { return }
    if ($sel -as [int] -and $sel -ge 1 -and $sel -le ($count - $start)) {
        $idx = $start + ([int]$sel) - 1
        Write-Host "--- Mensaje #$sel ---" -ForegroundColor Cyan
        Write-Host $arr[$idx].line
    } else {
        Write-Host 'Selección inválida' -ForegroundColor Yellow
    }
}

function Tail-BotLog {
    param([int]$Lines = 50)
    if (Test-Path bot.log) {
        Get-Content bot.log -Tail $Lines -Wait
    } else {
        Write-Host 'bot.log not found in repo root' -ForegroundColor Yellow
    }
}

function Restart-Bot {
    param([string]$Token='', [string]$MinInterval='1.0', [string]$MaxConc='1')
    # Stop all python_bot instances
    $ps = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'python_bot\\main.py' }
    foreach ($p in $ps) {
        try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
    }
    Start-Sleep -Seconds 1
    if (-not $Token) { $Token = Read-Host 'BOT token to start' }
    Start-Process -FilePath .\run_bot_alt.bat -ArgumentList $Token, $MinInterval, $MaxConc
    Write-Host 'Restart issued' -ForegroundColor Green
}


function Set-WebDomain {
    param([string]$Domain)
    if (-not $Domain) { $Domain = Read-Host 'Introduce dominio (ej: example.com) o http(s)://...' }
    if (-not $Domain) { Write-Host 'No domain provided' -ForegroundColor Yellow; return }
    # normalize: preserve port if provided. If no scheme provided and a port is present, default to http://
    if ($Domain -notmatch '^[a-zA-Z]+://') {
        if ($Domain -match ':[0-9]+$') {
            $url = "http://$Domain"
        } else {
            $url = "https://$Domain"
        }
    } else {
        $url = $Domain
    }
    # remove trailing slash
    $weburl = $url.TrimEnd('/')
    $envfile = Join-Path (Get-Location) '.env'
    if (Test-Path $envfile) {
        $lines = Get-Content $envfile
        $found = $false
        for ($i=0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match '^WEBAPP_URL=') { $lines[$i] = ('WEBAPP_URL="' + $weburl + '"'); $found = $true; break }
        }
        if (-not $found) { $lines += ('WEBAPP_URL="' + $weburl + '"') }
        $lines | Set-Content $envfile
    } else {
        ('WEBAPP_URL="' + $weburl + '"') | Out-File -FilePath $envfile -Encoding utf8
    }
    Write-Host "Set WEBAPP_URL=$weburl in .env" -ForegroundColor Green
}


function Start-WebServer {
    param([int]$Port = 8000)
    $webdir = Join-Path (Get-Location) 'projects\web\web'
    if (-not (Test-Path $webdir)) { Write-Host "Web dir not found: $webdir" -ForegroundColor Red; return }
    Write-Host "Starting static server from $webdir on port $Port..."
    Start-Process -FilePath powershell -ArgumentList "-NoProfile","-Command","Set-Location -Path '$webdir'; python -m http.server $Port" -WindowStyle Minimized
    Write-Host "Static server started (background)." -ForegroundColor Green
}


function Wait-ForHttp {
    param([string]$Url = 'http://127.0.0.1:8000/', [int]$TimeoutSec = 30)
    $start = Get-Date
    while ( ((Get-Date) - $start).TotalSeconds -lt $TimeoutSec ) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { return $true }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}


function Start-Bot {
    param([string]$Token='')
    $repo = Get-Location
    if (-not (Test-Path (Join-Path $repo 'run_bot_env.bat'))) {
        Write-Host 'run_bot_env.bat not found in repo root' -ForegroundColor Yellow
        if (Test-Path (Join-Path $repo 'run_bot_alt.bat')) { $script = 'run_bot_alt.bat' } else { return }
    } else { $script = 'run_bot_env.bat' }
    Write-Host "Starting bot using $script..."
    if ($Token) {
        Start-Process -FilePath .\$script -ArgumentList $Token -WorkingDirectory $repo
    } else {
        Start-Process -FilePath .\$script -WorkingDirectory $repo
    }
    Write-Host 'Bot start issued' -ForegroundColor Green
}


function Start-WebAndBot {
    param([int]$Port = 8000)
    $domain = Read-Host 'Dominio para la web (ej: example.com o https://example.com)'
    if ($domain) { Set-WebDomain -Domain $domain }
    Start-WebServer -Port $Port
    $token = Read-Host 'Introduce BOT token para iniciar el bot (Enter para usar .env)'
    if ($token -eq '') { $token = $null }
    Start-Bot -Token $token
    Write-Host 'Web + Bot start sequence issued.' -ForegroundColor Cyan
}


function Start-Tor {
    param([int]$Port = 8000)
    $repo = Get-Location
    $torExe = ''
    # look for tor in PATH or repo\tor\tor.exe
    try {
        $which = Get-Command tor -ErrorAction SilentlyContinue
        if ($which) { $torExe = $which.Path }
    } catch {}
    if (-not $torExe) {
        $localTor = Join-Path $repo 'tor\tor.exe'
        if (Test-Path $localTor) { $torExe = $localTor }
    }
    if (-not $torExe) {
        Write-Host 'Tor executable not found (install Tor or place tor.exe in ./tor/)' -ForegroundColor Red
        return $null
    }

    $hsDir = Join-Path $repo 'tor_data'
    if (-not (Test-Path $hsDir)) { New-Item -ItemType Directory -Path $hsDir | Out-Null }
    $torrc = @()
    $torrc += "DataDirectory $hsDir"
    $torrc += "HiddenServiceDir $hsDir\hidden_service"
    $torrc += "HiddenServicePort 80 127.0.0.1:$Port"
    $torrcPath = Join-Path $hsDir 'torrc'
    $torrc | Set-Content -Path $torrcPath -Encoding UTF8

    Write-Host "Starting Tor with config $torrcPath..." -ForegroundColor Cyan
    Start-Process -FilePath $torExe -ArgumentList "-f `"$torrcPath`"" -WorkingDirectory $hsDir -WindowStyle Hidden

    # wait for hostname
    $hostnameFile = Join-Path $hsDir 'hidden_service\hostname'
    $tries = 0
    while ($tries -lt 30) {
        if (Test-Path $hostnameFile) { break }
        Start-Sleep -Seconds 1
        $tries++
    }
    if (-not (Test-Path $hostnameFile)) {
        Write-Host 'Tor did not create hidden service hostname in time.' -ForegroundColor Red
        return $null
    }
    $onion = Get-Content $hostnameFile -Raw
    $onion = $onion.Trim()
    if ($onion) {
        $envfile = Join-Path $repo '.env'
        if (Test-Path $envfile) {
            $lines = Get-Content $envfile
            $found = $false
            for ($i=0; $i -lt $lines.Count; $i++) {
                if ($lines[$i] -match '^WEBAPP_ONION=') { $lines[$i] = ('WEBAPP_ONION="' + $onion + '"'); $found = $true; break }
            }
            if (-not $found) { $lines += ('WEBAPP_ONION="' + $onion + '"') }
            $lines | Set-Content $envfile
        } else {
            ('WEBAPP_ONION="' + $onion + '"') | Out-File -FilePath $envfile -Encoding utf8
        }
        Write-Host "Hidden service created: $onion" -ForegroundColor Green
        return $onion
    }
    return $null
}


function Create-Onion {
    param([int]$Port = 8000)
    $p = Read-Host "Puerto para hidden service (por defecto $Port)"
    if ($p) {
        try { $Port = [int]$p } catch { Write-Host 'Puerto inválido' -ForegroundColor Yellow; return }
    }
    $onion = Start-Tor -Port $Port
    if ($onion) {
        Write-Host "Hidden service creado: $onion" -ForegroundColor Green
        Write-Host "Puedes encontrarlo en .env como WEBAPP_ONION" -ForegroundColor Cyan
    } else {
        Write-Host 'Fallo al crear hidden service' -ForegroundColor Red
    }
}


function Stop-Tor {
    param()
    # try stopping tor processes by name or commandline
    try {
        $ps = Get-Process -Name tor -ErrorAction SilentlyContinue
        if ($ps) { $ps | Stop-Process -Force -ErrorAction SilentlyContinue }
    } catch {}
    try {
        $procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'tor.exe' }
        foreach ($p in $procs) { try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }
    } catch {}
    Write-Host 'Requested Tor stop (best-effort).' -ForegroundColor Yellow
}


function Clean-TorData {
    param()
    $repo = Get-Location
    $hsDir = Join-Path $repo 'tor_data'
    if (-not (Test-Path $hsDir)) { Write-Host 'No tor_data directory present.' -ForegroundColor Yellow; return }
    $ok = Read-Host "Confirm delete $hsDir and contents? (y/N)"
    if ($ok -notmatch '^[yY]') { Write-Host 'Aborted.'; return }
    try {
        Stop-Tor
        Remove-Item -Recurse -Force -Path $hsDir
        # remove WEBAPP_ONION from .env if present
        $envfile = Join-Path $repo '.env'
        if (Test-Path $envfile) {
            $lines = Get-Content $envfile | Where-Object { $_ -notmatch '^WEBAPP_ONION=' }
            $lines | Set-Content $envfile
        }
        Write-Host 'tor_data removed and .env cleaned.' -ForegroundColor Green
    } catch {
        Write-Host "Failed to clean tor_data: $_" -ForegroundColor Red
    }
}


function Start-WebBotAndTor {
    param([int]$Port = 8000)
    $domain = Read-Host 'Dominio para la web (ej: example.com o https://example.com) (Enter para usar Tor only)'
    if ($domain) { Set-WebDomain -Domain $domain }
    Start-WebServer -Port $Port
    # wait for http server to be available before creating onion
    $url = "http://127.0.0.1:$Port/"
    $ok = Wait-ForHttp -Url $url -TimeoutSec 30
    if (-not $ok) { Write-Host 'Web server did not respond in time; you can still create Tor hidden service.' -ForegroundColor Yellow }
    $onion = Start-Tor -Port $Port
    if ($onion) { Write-Host "Onion URL saved to .env: $onion" -ForegroundColor Cyan }
    $token = Read-Host 'Introduce BOT token para iniciar el bot (Enter para usar .env)'
    if ($token -eq '') { $token = $null }
    # ensure web server available before starting bot
    if (-not $ok) {
        $cont = Read-Host 'Web server not responding. Start bot anyway? (y/n)'
        if ($cont -notmatch '^[yY]') { Write-Host 'Aborted starting bot.' -ForegroundColor Yellow; return }
    }
    Start-Bot -Token $token
    Write-Host 'Web + Tor + Bot sequence issued.' -ForegroundColor Cyan
}

function Show-Menu {
    Clear-Host
    Write-Host 'DBTeam Bot Control' -ForegroundColor Cyan
    Write-Host '1) Mostrar /stats'
    Write-Host '2) Leer /messages (interactivo)'
    Write-Host '3) Tail bot.log'
    Write-Host '4) Reiniciar bot'
    Write-Host '5) Iniciar web + bot (pregunta dominio)'
    Write-Host '6) Iniciar web + bot + Tor (crear hidden service)'
    Write-Host '7) Crear .onion (solo hidden service)'
    Write-Host '8) Detener Tor'
    Write-Host '9) Limpiar datos Tor (tor_data)'
    Write-Host '10) Salir'
    $sel = Read-Host 'Selecciona una opción (1-10)'
    switch ($sel) {
        '1' { Get-BotStats }
        '2' { Read-MessagesInteractive }
        '3' { Tail-BotLog }
        '4' { Restart-Bot }
        '5' { Start-WebAndBot }
        '6' { Start-WebBotAndTor }
        '7' { Create-Onion }
        '8' { Stop-Tor }
        '9' { Clean-TorData }
        default { Write-Host 'Bye' }
    }
}

# If called directly, show menu in a loop
if ($MyInvocation.InvocationName -eq '.') {
    while ($true) {
        Show-Menu
        Start-Sleep -Seconds 1
        if ((Read-Host 'Continuar? (s/n)') -match '^[nN]') { break }
    }
}
